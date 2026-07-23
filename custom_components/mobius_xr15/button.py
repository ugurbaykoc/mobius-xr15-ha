"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule import build_flat_schedule, brightness_to_intensity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the apply-schedule button."""
    mac = entry.data[CONF_MAC]
    async_add_entities([MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac)])


class MobiusXR15ApplyScheduleButton(ButtonEntity):
    """Pushes the current channel values to the device as its schedule.

    This is the only path that writes the full 25-slot schedule - the
    light entity itself only retargets intensity (on/off/brightness), so
    color recipe edits reach the device exclusively through this button.
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
        slots = build_flat_schedule(store["channel_numbers"])

        light = store.get("light")
        if light is not None and not light.is_on:
            # Install the recipe without relighting the tank - the write
            # sequence always carries an intensity value, so honor "off".
            intensity = 0
        elif light is not None and light.brightness is not None:
            intensity = brightness_to_intensity(light.brightness)
        else:
            intensity = 500

        await store["client"].async_write_schedule(slots, intensity)
