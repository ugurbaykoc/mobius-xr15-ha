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

from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import RX_DATA_UUID, RX_FINAL_UUID, TX_FINAL_UUID
from .protocol import build_intensity_sequence, build_write_sequence

_LOGGER = logging.getLogger(__name__)

WRITE_DELAY = 0.35
SERVICE_RESOLUTION_DELAY = 1.5
ATTEMPTS = 4


class MobiusXR15Client:
    """Serializes BLE writes to one Mobius XR15 light."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        self.last_error: str | None = None

    async def async_write_schedule(self, slots: list[bytes], intensity: int) -> None:
        await self._send(build_write_sequence(slots, intensity), "schedule")

    async def async_set_intensity(self, intensity: int) -> None:
        await self._send(build_intensity_sequence(intensity), f"intensity {intensity}")

    @property
    def rssi(self) -> int | None:
        info = bluetooth.async_last_service_info(self._hass, self._address, connectable=True)
        return info.rssi if info is not None else None

    def _on_disconnected(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("%s: disconnected", self._address)

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

    async def _write(self, client: BleakClientWithServiceCache, packets: list[bytes]) -> None:
        tx = client.services.get_characteristic(TX_FINAL_UUID)
        if tx is None:
            raise HomeAssistantError(
                f"write characteristic {TX_FINAL_UUID} missing on {self._address}"
            )

        def _noop(_char, _data) -> None:
            return None

        for uuid in (RX_DATA_UUID, RX_FINAL_UUID):
            try:
                await client.start_notify(uuid, _noop)
            except Exception as err:  # notifications are not required to control
                _LOGGER.debug("%s: start_notify(%s) failed: %s", self._address, uuid, err)

        # Acknowledged writes when the characteristic offers them: they
        # pace the sequence to whatever the link can carry and surface
        # failures instead of dropping packets silently.
        response = "write" in tx.properties
        for packet in packets:
            await client.write_gatt_char(tx, packet, response=response)
            await asyncio.sleep(WRITE_DELAY)

    async def _send(self, packets: list[bytes], label: str) -> None:
        async with self._lock:
            last: Exception | None = None
            for attempt in range(1, ATTEMPTS + 1):
                client = None
                try:
                    client = await self._connect(fresh=attempt > 1)
                    await self._write(client, packets)
                    self.last_error = None
                    _LOGGER.debug("%s: %s written (attempt %s)", self._address, label, attempt)
                    return
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
