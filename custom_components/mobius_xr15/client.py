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

# An acknowledged write already waits for the light to answer, so the
# gap after it only needs to let the firmware act on the packet. Without
# acknowledgement there is no flow control at all and the gap is the
# only thing keeping the controller's buffer from overflowing.
WRITE_DELAY_ACK = 0.05
WRITE_DELAY_UNACKED = 0.35
READ_WAIT = 1.5
SERVICE_RESOLUTION_TIMEOUT = 3.0
ATTEMPTS = 4

# How long a connection is kept open after the last command. Reconnecting
# costs several seconds, which is most of what "the light is slow to
# react" means in practice; holding the link makes the second command and
# every one after it immediate. It is not held indefinitely, because the
# light accepts one connection at a time and the phone app needs a turn.
IDLE_DISCONNECT = 120.0


class MobiusXR15Client:
    """Serializes BLE exchanges with one Mobius XR15 light."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        self._rx: list[bytes] = []
        self._client: BleakClientWithServiceCache | None = None
        self._tx = None
        self._idle_handle: asyncio.TimerHandle | None = None
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
        self._client = None
        self._tx = None

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
        return await establish_connection(
            BleakClientWithServiceCache,
            device,
            self._address,
            disconnected_callback=self._on_disconnected,
            use_services_cache=not fresh,
        )

    async def _wait_for_tx(self, client: BleakClientWithServiceCache):
        """Wait for GATT to resolve, but only as long as it actually takes.

        This used to be a flat 1.5 second sleep on every connection. It
        was there because services resolve asynchronously and asking too
        early finds nothing - but over a Bluetooth proxy they are usually
        there on the first look, and the sleep was pure latency.
        """
        deadline = self._hass.loop.time() + SERVICE_RESOLUTION_TIMEOUT
        while True:
            tx = client.services.get_characteristic(TX_FINAL_UUID)
            if tx is not None:
                return tx
            if self._hass.loop.time() >= deadline:
                raise HomeAssistantError(
                    f"write characteristic {TX_FINAL_UUID} missing on {self._address}"
                )
            await asyncio.sleep(0.1)

    async def _subscribe(self, client: BleakClientWithServiceCache) -> None:
        for uuid in (RX_DATA_UUID, RX_FINAL_UUID):
            try:
                await client.start_notify(uuid, self._collect)
            except Exception as err:  # notifications are not required to control
                _LOGGER.debug("%s: start_notify(%s) failed: %s", self._address, uuid, err)

    # ------------------------------------------------------------------
    # Keeping the link open
    # ------------------------------------------------------------------

    def _cancel_idle(self) -> None:
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None

    def _arm_idle(self) -> None:
        self._cancel_idle()
        self._idle_handle = self._hass.loop.call_later(IDLE_DISCONNECT, self._idle_expired)

    def _idle_expired(self) -> None:
        self._idle_handle = None
        self._hass.async_create_task(self._async_idle_release())

    async def _async_idle_release(self) -> None:
        async with self._lock:
            await self._release()

    async def _release(self) -> None:
        client, self._client, self._tx = self._client, None, None
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception as err:  # noqa: BLE001 - nothing useful to do about it
            _LOGGER.debug("%s: disconnect failed: %s", self._address, err)

    async def async_shutdown(self) -> None:
        """Hand the light back when the integration goes away."""
        self._cancel_idle()
        async with self._lock:
            await self._release()

    # ------------------------------------------------------------------
    # Exchanges
    # ------------------------------------------------------------------

    async def _send_packet(self, client, tx, packet: bytes) -> None:
        # Acknowledged writes when the characteristic offers them: they
        # pace the sequence to whatever the link can carry and surface
        # failures instead of dropping packets silently.
        acked = "write" in tx.properties
        await client.write_gatt_char(tx, packet, response=acked)
        await asyncio.sleep(WRITE_DELAY_ACK if acked else WRITE_DELAY_UNACKED)

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
        """Run one job on the link, reconnecting and retrying as needed.

        The first attempt reuses an open connection if there is one - that
        is where the speed comes from. Every retry after a failure drops
        the link and builds a new one, because a connection that has just
        failed mid-job is exactly the one not to trust.
        """
        async with self._lock:
            self._cancel_idle()
            last: Exception | None = None
            try:
                for attempt in range(1, ATTEMPTS + 1):
                    try:
                        if self._client is None or not self._client.is_connected:
                            client = await self._connect(fresh=attempt > 1)
                            tx = await self._wait_for_tx(client)
                            await self._subscribe(client)
                            self._client, self._tx = client, tx
                        result = await work(self._client, self._tx)
                        self.last_error = None
                        _LOGGER.debug(
                            "%s: %s done (attempt %s)", self._address, label, attempt
                        )
                        return result
                    except Exception as err:  # noqa: BLE001 - retried as a whole below
                        last = err
                        _LOGGER.warning(
                            "%s: %s attempt %s/%s failed: %s: %s",
                            self._address, label, attempt, ATTEMPTS,
                            type(err).__name__, err,
                        )
                        await self._release()
                self.last_error = f"{type(last).__name__}: {last}"
                raise HomeAssistantError(
                    f"{label} failed after {ATTEMPTS} attempts: {last}"
                )
            finally:
                if self._client is not None:
                    self._arm_idle()
