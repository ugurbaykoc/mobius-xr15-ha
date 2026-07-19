"""Per-channel color/value controls for the Mobius XR15 flat schedule."""
from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CHANNEL_NAMES, COLOR_CHANNELS, DEFAULT_CHANNEL_VALUES, DOMAIN, MAX_INTENSITY


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one number entity per color channel."""
    mac = entry.data[CONF_MAC]
    entities = [MobiusXR15ChannelNumber(mac, channel) for channel in COLOR_CHANNELS]
    async_add_entities(entities)
    hass.data[DOMAIN][entry.entry_id]["channel_numbers"] = entities


class MobiusXR15ChannelNumber(RestoreNumber):
    """One channel's value (0-1000) in the flat color recipe."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_INTENSITY
    _attr_native_step = 10
    _attr_mode = NumberMode.SLIDER

    def __init__(self, mac: str, channel: int) -> None:
        self.channel = channel
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_ch{channel}"
        self._attr_name = CHANNEL_NAMES[channel]
        self._attr_native_value = DEFAULT_CHANNEL_VALUES[channel]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_number_data()
        if last_data is not None and last_data.native_value is not None:
            self._attr_native_value = last_data.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
