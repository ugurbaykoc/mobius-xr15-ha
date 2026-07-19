"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule import build_slots_from_entities, brightness_to_intensity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the apply-schedule button."""
    mac = entry.data[CONF_MAC]
    async_add_entities([MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac)])


class MobiusXR15ApplyScheduleButton(ButtonEntity):
    """Pushes the current slot/channel helper values to the device as its schedule.

    The light entity already installs the current schedule whenever it
    transitions off -> on. This button is for pushing edits while the
    light is already on, without a full off/on cycle.
    """

    _attr_has_entity_name = True
    _attr_name = "Apply Schedule"
    _attr_icon = "mdi:content-save-outline"

    def __init__(self, hass: HomeAssistant, entry_id: str, mac: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_apply_schedule"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        slots = build_slots_from_entities(store["channel_numbers"], store["slot_times"])

        light = store.get("light")
        intensity = brightness_to_intensity(light.brightness) if light and light.brightness else 500

        await store["client"].async_write_schedule(slots, intensity)
