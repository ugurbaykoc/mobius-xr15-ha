"""Signal strength diagnostic sensor for the Mobius XR15 integration."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.bluetooth import async_last_service_info
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the diagnostic sensors."""
    mac = entry.data[CONF_MAC]
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MobiusXR15SignalSensor(hass, mac),
            MobiusXR15LastCommandSensor(store["client"], mac),
        ]
    )


class MobiusXR15SignalSensor(SensorEntity):
    """Last-seen BLE advertisement RSSI for the light.

    Reflects Home Assistant's own passive Bluetooth scanning, independent
    of whether a GATT connection is currently open - useful for judging
    whether "the light isn't responding" is a signal-strength problem
    without needing to SSH in and run bluetoothctl by hand.
    """

    _attr_has_entity_name = True
    _attr_name = "Signal Strength"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, mac: str) -> None:
        self._hass = hass
        self._address = mac
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_rssi"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})
        self._unsub: callable | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._async_update(None)
        self._unsub = async_track_time_interval(self._hass, self._async_update, UPDATE_INTERVAL)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _async_update(self, _now: datetime | None) -> None:
        info = async_last_service_info(self._hass, self._address, connectable=True)
        self._attr_native_value = info.rssi if info is not None else None
        self.async_write_ha_state()


class MobiusXR15LastCommandSensor(SensorEntity):
    """Outcome of the most recent BLE command, visible right in the UI.

    Answers "did that toggle actually reach the light?" without needing
    docker logs: the state is e.g. "OK: set intensity 0" or
    "FAILED: set intensity 0", with attempt count, whether acknowledged
    GATT writes were used, the full error text, and a timestamp as
    attributes.
    """

    _attr_has_entity_name = True
    _attr_name = "Last Command"
    _attr_icon = "mdi:bluetooth-transfer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, client, mac: str) -> None:
        self._client = client
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_last_command"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})
        self._unsub: callable | None = None
        self._refresh()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = self._client.register_listener(self._handle_update)
        self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        cmd = self._client.last_command
        if cmd is None:
            self._attr_native_value = "no commands yet"
            self._attr_extra_state_attributes = {}
            return
        if cmd["success"] is None:
            status = f"SENDING (attempt {cmd['attempts']}/{cmd['max_attempts']})"
        elif cmd["success"]:
            status = "OK"
        else:
            status = "FAILED"
        # HA caps a sensor state at 255 chars - keep it short and put
        # the details (including full error text) in attributes.
        self._attr_native_value = f"{status}: {cmd['action']}"[:255]
        self._attr_extra_state_attributes = {
            "attempts_used": cmd["attempts"],
            "max_attempts": cmd["max_attempts"],
            "acknowledged_writes": cmd["acknowledged_writes"],
            "error": cmd["error"],
            "at": cmd["when"].isoformat(),
        }
