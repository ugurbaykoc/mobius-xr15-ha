"""Bridge status diagnostic sensor for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

# Read from the device by the bridge's background telemetry poll and
# served out of its cache, so these cost no extra BLE traffic.
TELEMETRY_SENSORS: tuple[tuple[str, str, str, str | None, str | None], ...] = (
    ("puck_temperature", "LED Temperature", "mdi:thermometer",
     UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("driver_temperature", "Driver Temperature", "mdi:thermometer",
     UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("internal_temperature", "Internal Temperature", "mdi:thermometer",
     UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("fan_speed", "Fan Speed", "mdi:fan", None, None),
    ("operation_state", "Operation State", "mdi:state-machine", None, None),
    ("error_state", "Error State", "mdi:alert-circle-outline", None, None),
    ("device_time", "Device Clock", "mdi:clock-outline", None, None),
    ("firmware_version", "Firmware Version", "mdi:chip", None, None),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the bridge status sensor."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    coordinator = store["coordinator"]
    async_add_entities(
        [MobiusXR15BridgeSensor(coordinator, mac)]
        + [
            MobiusXR15TelemetrySensor(coordinator, mac, key, name, icon, unit, dev_cls)
            for key, name, icon, unit, dev_cls in TELEMETRY_SENSORS
        ]
    )


class MobiusXR15BridgeSensor(CoordinatorEntity, SensorEntity):
    """Outcome of the last BLE command, as reported by the bridge.

    State examples: "OK: off", "FAILED: apply (intensity 1000)",
    "SENDING: on", or "idle" right after a bridge restart. The full
    error text and timestamp are exposed as attributes.
    """

    _attr_has_entity_name = True
    _attr_name = "Bridge Status"
    _attr_icon = "mdi:bluetooth-transfer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator)
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_bridge_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        last = data.get("last_result") or {}
        label = last.get("label") or ""
        if last.get("ok") is True:
            return f"OK: {label}"
        if last.get("ok") is False:
            return f"FAILED: {label}"
        if label:
            return f"SENDING: {label}"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        last = data.get("last_result") or {}
        return {
            "bridge_state": data.get("state"),
            "error": last.get("error"),
            "at": last.get("at"),
            "consecutive_failures": data.get("consecutive_failures"),
        }


class MobiusXR15TelemetrySensor(CoordinatorEntity, SensorEntity):
    """One value read from the light itself.

    The device exposes real telemetry over the C2 protocol (attribute 101
    PhysicalValues plus scalars like 1511 PuckTemperature). The bridge
    reads them on a slow background loop and caches the result, so these
    entities are free to update - no BLE traffic per poll.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator, mac: str, key: str, name: str,
        icon: str, unit: str | None, device_class: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        if unit:
            self._attr_native_unit_of_measurement = unit
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if device_class:
            self._attr_device_class = device_class
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self):
        telemetry = (self.coordinator.data or {}).get("telemetry") or {}
        return telemetry.get(self._key)

    @property
    def available(self) -> bool:
        """Hidden until the device has actually reported this value."""
        telemetry = (self.coordinator.data or {}).get("telemetry") or {}
        return self.coordinator.last_update_success and self._key in telemetry
