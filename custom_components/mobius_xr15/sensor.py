"""Signal strength diagnostic sensor for the Mobius XR15 integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the diagnostic sensors."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    async_add_entities(
        [
            MobiusXR15SignalSensor(store["client"], mac),
            MobiusXR15LastErrorSensor(store["client"], mac),
        ]
    )


class MobiusXR15SignalSensor(SensorEntity):
    """Last-seen advertisement RSSI, as reported by Home Assistant.

    With a Bluetooth proxy next to the tank this reads the proxy's view
    of the light, which is the number that actually matters: it is the
    link commands travel over.
    """

    _attr_has_entity_name = True
    _attr_name = "Signal Strength"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, mac: str) -> None:
        self._client = client
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_rssi"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self) -> int | None:
        return self._client.rssi

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Per-radio RSSI, so a mis-placed proxy is visible at a glance.

        The state is the best of these; the attributes say which radio
        produced it and what the others hear.
        """
        sources = self._client.signal_sources
        if not sources:
            return {}
        best = max(sources, key=sources.get)
        return {"best_source": best, "sources": sources}


class MobiusXR15LastErrorSensor(SensorEntity):
    """Why the last command failed, or 'ok'.

    Saves digging through the log to tell a signal problem from a
    protocol one - the exception type is part of the state.
    """

    _attr_has_entity_name = True
    _attr_name = "Last Error"
    _attr_icon = "mdi:bluetooth-transfer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, mac: str) -> None:
        self._client = client
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_last_error"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self) -> str:
        return (self._client.last_error or "ok")[:255]
