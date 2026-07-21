"""BLE transport for the Mobius XR15 integration."""
from __future__ import annotations

import asyncio
import logging

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import RX_DATA_UUID, RX_FINAL_UUID, TX_FINAL_UUID
from .protocol import build_intensity_sequence, build_write_sequence

_LOGGER = logging.getLogger(__name__)

WRITE_DELAY = 0.3


class MobiusXR15Client:
    """Serializes BLE writes to a single Mobius XR15 device."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()

    async def async_write_schedule(self, slots: list[bytes], intensity: int) -> None:
        """Install a 25-slot schedule and resume playback."""
        await self._send(build_write_sequence(slots, intensity))

    async def async_set_intensity(self, intensity: int) -> None:
        """Retarget overall intensity without rewriting the schedule."""
        await self._send(build_intensity_sequence(intensity))

    async def _connect(self, force_fresh: bool = False) -> BleakClientWithServiceCache:
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(
                f"{self._address} is not visible to Home Assistant's bluetooth integration"
            )
        return await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._address,
            use_services_cache=not force_fresh,
        )

    async def _connect_verified(self) -> BleakClientWithServiceCache:
        """Connect and confirm the write characteristic is actually present.

        A stale cached service list (e.g. from a flaky discovery on a weak
        BLE signal) can leave establish_connection "succeeding" without the
        characteristic we need. Detect that and force one fresh reconnect.
        """
        client = await self._connect()
        if client.services.get_characteristic(TX_FINAL_UUID) is not None:
            return client

        _LOGGER.warning(
            "%s: TX characteristic missing from cached services, reconnecting fresh",
            self._address,
        )
        await client.clear_cache()
        await client.disconnect()
        client = await self._connect(force_fresh=True)
        if client.services.get_characteristic(TX_FINAL_UUID) is None:
            await client.disconnect()
            raise RuntimeError(f"TX characteristic {TX_FINAL_UUID} not found on {self._address}")
        return client

    async def _send(self, packets: list[bytes]) -> None:
        async with self._lock:
            client = await self._connect_verified()
            try:
                def _noop(_char, _data) -> None:
                    return None

                try:
                    await client.start_notify(RX_DATA_UUID, _noop)
                    await client.start_notify(RX_FINAL_UUID, _noop)
                except Exception as err:  # notifications aren't required for control
                    _LOGGER.debug("Could not start notify: %s", err)

                for packet in packets:
                    await client.write_gatt_char(TX_FINAL_UUID, packet, response=False)
                    await asyncio.sleep(WRITE_DELAY)
            finally:
                await client.disconnect()
