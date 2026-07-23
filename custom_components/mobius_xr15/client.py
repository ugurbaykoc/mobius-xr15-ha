"""BLE transport for the Mobius XR15 integration."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import RX_DATA_UUID, RX_FINAL_UUID, TX_FINAL_UUID
from .protocol import build_intensity_sequence, build_write_sequence

_LOGGER = logging.getLogger(__name__)

WRITE_DELAY = 0.3
SERVICE_RESOLUTION_DELAY = 2.0
CONNECT_ATTEMPTS = 6


class MobiusXR15Client:
    """Serializes BLE writes to a single Mobius XR15 device.

    Every operation (connect, verify the write characteristic is actually
    present, write all packets) is retried together as one unit, up to
    CONNECT_ATTEMPTS times. Earlier versions only retried the connect step,
    so a write that failed partway through the packet sequence - a real
    possibility on a marginal signal - would just fail outright with
    nothing to catch it. Retrying the whole cycle means a mid-write drop
    gets a genuine fresh attempt instead.
    """

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self._address = address
        self._lock = asyncio.Lock()
        # Outcome of the most recent command, surfaced by the "Last
        # Command" diagnostic sensor so failures are visible in the UI
        # instead of only in debug logs.
        self.last_command: dict[str, Any] | None = None
        self._used_ack_writes: bool | None = None
        self._listeners: list[Callable[[], None]] = []

    def register_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to last_command updates; returns an unsubscribe callable."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _record(self, label: str, success: bool, attempts: int, error: Exception | None) -> None:
        self.last_command = {
            "action": label,
            "success": success,
            "attempts": attempts,
            "max_attempts": CONNECT_ATTEMPTS,
            "acknowledged_writes": self._used_ack_writes,
            "error": str(error) if error is not None else None,
            "when": datetime.now(timezone.utc),
        }
        for listener in list(self._listeners):
            listener()

    async def async_write_schedule(self, slots: list[bytes], intensity: int) -> None:
        """Install a 25-slot schedule and resume playback."""
        await self._send(
            build_write_sequence(slots, intensity), f"write schedule + intensity {intensity}"
        )

    async def async_set_intensity(self, intensity: int) -> None:
        """Retarget overall intensity without rewriting the schedule."""
        await self._send(build_intensity_sequence(intensity), f"set intensity {intensity}")

    def _on_disconnected(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("%s: BLE disconnected", self._address)

    async def _connect(self, force_fresh: bool) -> BleakClientWithServiceCache:
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(
                f"{self._address} is not visible to Home Assistant's bluetooth integration"
            )
        # If a previous attempt connected at the BlueZ level but raised
        # before handing us back a usable client (e.g. an error during
        # establish_connection's own internal retry/service-resolution
        # logic), that connection has no Python-side reference anywhere
        # and would otherwise sit there indefinitely, occupying one of
        # the adapter's limited connection slots and potentially leaving
        # every subsequent attempt fighting a zombie connection instead
        # of a fresh one. Force-clear anything like that first.
        await close_stale_connections_by_address(self._address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._address,
            disconnected_callback=self._on_disconnected,
            use_services_cache=not force_fresh,
        )
        # BlueZ resolves GATT services asynchronously after the connection
        # itself is up - on a marginal signal it can report "connected"
        # before that resolution has actually finished, leaving the
        # service list empty/incomplete for a moment. Give it a beat.
        await asyncio.sleep(SERVICE_RESOLUTION_DELAY)
        return client

    async def _write_packets(
        self, client: BleakClientWithServiceCache, packets: list[bytes]
    ) -> None:
        tx_char = client.services.get_characteristic(TX_FINAL_UUID)
        if tx_char is None:
            raise RuntimeError(f"TX characteristic {TX_FINAL_UUID} not found on {self._address}")

        def _noop(_char, _data) -> None:
            return None

        try:
            await client.start_notify(RX_DATA_UUID, _noop)
            await client.start_notify(RX_FINAL_UUID, _noop)
        except Exception as err:  # notifications aren't required for control
            _LOGGER.debug("%s: could not start notify: %s", self._address, err)

        # Prefer an acknowledged write (waits for the peripheral's GATT
        # response) when the characteristic supports it - on a weak link,
        # write-without-response can silently drop a packet with no error
        # at all, since there's nothing to confirm delivery.
        use_response = "write" in tx_char.properties
        self._used_ack_writes = use_response
        _LOGGER.debug(
            "%s: TX characteristic properties=%s, write-with-response=%s",
            self._address,
            tx_char.properties,
            use_response,
        )

        for packet in packets:
            await client.write_gatt_char(TX_FINAL_UUID, packet, response=use_response)
            await asyncio.sleep(WRITE_DELAY)

    async def _send(self, packets: list[bytes], label: str) -> None:
        async with self._lock:
            last_error: Exception = RuntimeError(f"could not reach {self._address}")
            for attempt in range(1, CONNECT_ATTEMPTS + 1):
                client: BleakClientWithServiceCache | None = None
                try:
                    client = await self._connect(force_fresh=attempt > 1)
                    await self._write_packets(client, packets)
                    self._record(label, True, attempt, None)
                    return
                except Exception as err:  # noqa: BLE001 - deliberately broad, see retry loop
                    last_error = err
                    _LOGGER.warning(
                        "%s: attempt %s/%s failed: %s",
                        self._address,
                        attempt,
                        CONNECT_ATTEMPTS,
                        err,
                    )
                    if client is not None:
                        try:
                            await client.clear_cache()
                        except Exception as cache_err:
                            _LOGGER.debug("%s: clear_cache failed: %s", self._address, cache_err)
                finally:
                    if client is not None:
                        try:
                            await client.disconnect()
                        except Exception as disconnect_err:
                            _LOGGER.debug(
                                "%s: disconnect after attempt failed: %s",
                                self._address,
                                disconnect_err,
                            )

            self._record(label, False, CONNECT_ATTEMPTS, last_error)
            raise last_error
