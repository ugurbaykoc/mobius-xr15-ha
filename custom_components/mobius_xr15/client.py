"""BLE transport for the Mobius XR15 integration.

Connections go through Home Assistant's Bluetooth integration, which
means they are routed over an ESPHome Bluetooth proxy automatically when
one is in range of the light. That is the point of this design: the
proxy sits next to the tank, so the radio link is short and strong,
while Home Assistant stays wherever it already runs.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import RX_DATA_UUID, RX_FINAL_UUID, TX_FINAL_UUID
from .protocol import (
    build_get_packet,
    build_intensity_sequence,
    build_set_packet,
    build_write_sequence,
    parse_response,
)

_LOGGER = logging.getLogger(__name__)

WRITE_DELAY = 0.35
READ_WAIT = 1.5
SERVICE_RESOLUTION_DELAY = 1.5
ATTEMPTS = 4


class MobiusXR15Client:
    """Serializes BLE exchanges with one Mobius XR15 light."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        self._rx: list[bytes] = []
        self.last_error: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def async_write_schedule(self, slots: list[bytes], intensity: int) -> None:
        packets = build_write_sequence(slots, intensity)
        await self._run(lambda c, tx: self._send_all(c, tx, packets), "schedule")

    async def async_set_intensity(self, intensity: int) -> None:
        packets = build_intensity_sequence(intensity)
        await self._run(
            lambda c, tx: self._send_all(c, tx, packets), f"intensity {intensity}"
        )

    async def async_read_attributes(
        self, specs: list[tuple[int, int, int]]
    ) -> dict[int, dict[str, Any] | None]:
        """Read several attributes over one connection.

        `specs` is a list of (attribute, sub, count). Reads are batched
        deliberately: each connection costs a few seconds on this link,
        so asking for six things at once is six times cheaper than six
        separate polls.
        """

        async def work(client, tx) -> dict[int, dict[str, Any] | None]:
            results: dict[int, dict[str, Any] | None] = {}
            for msg_id, (attr, sub, count) in enumerate(specs, 1):
                results[attr] = await self._query(client, tx, attr, msg_id, sub, count)
            return results

        return await self._run(work, f"read {[spec[0] for spec in specs]}")

    async def async_write_attribute(self, attr: int, value: int, sub: int = 0) -> int:
        """Write one attribute, using the length the device itself reports.

        The element width is read back from the light before every write
        and never assumed. Guessing it once already put this light off
        the air until it was power-cycled: a two-byte write to a
        one-byte attribute is not a rejected command, it is a corrupted
        one. If the light will not say how wide the value is, nothing is
        written.
        """

        async def work(client, tx) -> int:
            probe = await self._query(client, tx, attr, 1, sub, 1)
            if probe is None or not probe["elem_len"]:
                raise HomeAssistantError(
                    f"attribute {attr}: the light did not report a value size, "
                    "so there is nothing to write safely"
                )
            width = probe["elem_len"]
            try:
                data = int(value).to_bytes(width, "little")
            except (OverflowError, ValueError) as err:
                raise HomeAssistantError(
                    f"attribute {attr}: {value} does not fit the {width}-byte "
                    f"value the light reports"
                ) from err
            await self._send_packet(client, tx, build_set_packet(attr, data, 2, sub))
            return width

        return await self._run(work, f"write {attr}={value}")

    @property
    def rssi(self) -> int | None:
        info = bluetooth.async_last_service_info(self._hass, self._address, connectable=True)
        return info.rssi if info is not None else None

    @property
    def signal_sources(self) -> dict[str, int]:
        """RSSI per radio that can currently see the light.

        Home Assistant connects through whichever connectable scanner
        hears the light loudest, so a single number cannot tell you
        whether the proxy is earning its keep. This can: if the proxy
        reads no better than the host adapter, it is not where it needs
        to be.
        """
        try:
            devices = bluetooth.async_scanner_devices_by_address(
                self._hass, self._address, connectable=True
            )
        except Exception as err:  # helper availability varies across HA versions
            _LOGGER.debug("%s: scanner listing unavailable: %s", self._address, err)
            return {}

        sources: dict[str, int] = {}
        for device in devices:
            scanner = device.scanner
            name = getattr(scanner, "name", None) or getattr(scanner, "source", None)
            rssi = getattr(device.advertisement, "rssi", None)
            if name is not None and rssi is not None:
                sources[str(name)] = int(rssi)
        return sources

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    def _on_disconnected(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("%s: disconnected", self._address)

    def _collect(self, _char, data: bytearray) -> None:
        self._rx.append(bytes(data))

    async def _connect(self, fresh: bool) -> BleakClientWithServiceCache:
        device = bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if device is None:
            raise HomeAssistantError(
                f"{self._address} is not visible to Home Assistant. Check that the "
                "Bluetooth proxy is online and in range of the light."
            )
        # A previous attempt may have left a connection open at the
        # controller without handing us back a usable client; clear it
        # before asking for a new one.
        await close_stale_connections_by_address(self._address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            self._address,
            disconnected_callback=self._on_disconnected,
            use_services_cache=not fresh,
        )
        # GATT services resolve asynchronously; give them a moment before
        # looking for the write characteristic.
        await asyncio.sleep(SERVICE_RESOLUTION_DELAY)
        return client

    async def _subscribe(self, client: BleakClientWithServiceCache) -> None:
        for uuid in (RX_DATA_UUID, RX_FINAL_UUID):
            try:
                await client.start_notify(uuid, self._collect)
            except Exception as err:  # notifications are not required to control
                _LOGGER.debug("%s: start_notify(%s) failed: %s", self._address, uuid, err)

    # ------------------------------------------------------------------
    # Exchanges
    # ------------------------------------------------------------------

    async def _send_packet(self, client, tx, packet: bytes) -> None:
        # Acknowledged writes when the characteristic offers them: they
        # pace the sequence to whatever the link can carry and surface
        # failures instead of dropping packets silently.
        await client.write_gatt_char(tx, packet, response="write" in tx.properties)
        await asyncio.sleep(WRITE_DELAY)

    async def _send_all(self, client, tx, packets: list[bytes]) -> None:
        for packet in packets:
            await self._send_packet(client, tx, packet)

    async def _query(
        self, client, tx, attr: int, msg_id: int, sub: int, count: int
    ) -> dict[str, Any] | None:
        self._rx.clear()
        await client.write_gatt_char(
            tx, build_get_packet(attr, msg_id, sub, count), response="write" in tx.properties
        )
        await asyncio.sleep(READ_WAIT)
        reply = parse_response(list(self._rx))
        if reply is not None and reply["attr"] != attr:
            # A late reply to the previous question in the batch.
            _LOGGER.debug(
                "%s: asked for attribute %s, got %s", self._address, attr, reply["attr"]
            )
            return None
        return reply

    async def _run(
        self,
        work: Callable[[Any, Any], Awaitable[Any]],
        label: str,
    ) -> Any:
        """Connect, do one job, disconnect - retrying the job as a whole."""
        async with self._lock:
            last: Exception | None = None
            for attempt in range(1, ATTEMPTS + 1):
                client = None
                try:
                    client = await self._connect(fresh=attempt > 1)
                    tx = client.services.get_characteristic(TX_FINAL_UUID)
                    if tx is None:
                        raise HomeAssistantError(
                            f"write characteristic {TX_FINAL_UUID} missing on {self._address}"
                        )
                    await self._subscribe(client)
                    result = await work(client, tx)
                    self.last_error = None
                    _LOGGER.debug("%s: %s done (attempt %s)", self._address, label, attempt)
                    return result
                except Exception as err:  # noqa: BLE001 - retried as a whole below
                    last = err
                    _LOGGER.warning(
                        "%s: %s attempt %s/%s failed: %s: %s",
                        self._address, label, attempt, ATTEMPTS, type(err).__name__, err,
                    )
                finally:
                    if client is not None:
                        try:
                            await client.disconnect()
                        except Exception as err:
                            _LOGGER.debug("%s: disconnect failed: %s", self._address, err)
            self.last_error = f"{type(last).__name__}: {last}"
            raise HomeAssistantError(f"{label} failed after {ATTEMPTS} attempts: {last}")
