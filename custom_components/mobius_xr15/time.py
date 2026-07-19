"""Per-slot start-time controls for the Mobius XR15 schedule."""
from __future__ import annotations

from datetime import time as time_of_day

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .schedule import SLOT_COUNT, default_time


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one time entity per schedule slot."""
    mac = entry.data[CONF_MAC]
    entities = [MobiusXR15SlotTime(mac, slot) for slot in range(SLOT_COUNT)]
    async_add_entities(entities)
    hass.data[DOMAIN][entry.entry_id]["slot_times"] = entities


class MobiusXR15SlotTime(TimeEntity, RestoreEntity):
    """Start time for one schedule slot."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, mac: str, slot: int) -> None:
        self.slot = slot
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_slot{slot}_time"
        self._attr_name = f"Slot {slot + 1} Time"
        hour, minute = (int(part) for part in default_time(slot).split(":"))
        self._attr_native_value = time_of_day(hour, minute)
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            hour, minute, *_ = last_state.state.split(":")
            self._attr_native_value = time_of_day(int(hour), int(minute))

    async def async_set_value(self, value: time_of_day) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
