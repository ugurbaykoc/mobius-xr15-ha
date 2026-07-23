"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule import brightness_to_intensity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the apply-schedule button."""
    mac = entry.data[CONF_MAC]
    async_add_entities([MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac)])


class MobiusXR15ApplyScheduleButton(ButtonEntity):
    """Pushes the current channel values to the device as its schedule.

    The light entity already installs the current recipe whenever it
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

    @property
    def available(self) -> bool:
        """Unavailable when the bridge itself is unreachable."""
        return self._hass.data[DOMAIN][self._entry_id]["coordinator"].last_update_success

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        channels = {
            entity.channel: int(entity.native_value or 0)
            for entity in store["channel_numbers"]
        }

        light = store.get("light")
        if light is not None and light.brightness is not None:
            intensity = brightness_to_intensity(light.brightness)
        else:
            intensity = 500

        await store["client"].async_apply(channels, intensity)
