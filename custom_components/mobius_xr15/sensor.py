"""Bridge status diagnostic sensor for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the bridge status sensor."""
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [MobiusXR15BridgeSensor(store["coordinator"], entry.data[CONF_MAC])]
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
        }
