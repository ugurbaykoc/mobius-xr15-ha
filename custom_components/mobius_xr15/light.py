"""Light platform for the Mobius XR15 integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .client import MobiusXR15Client
from .const import DOMAIN
from .protocol import build_blank_schedule
from .schedule import brightness_to_intensity, build_recipe_schedule, intensity_to_brightness

DEFAULT_INTENSITY = 500


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Mobius XR15 light."""
    store = hass.data[DOMAIN][entry.entry_id]
    light = MobiusXR15Light(store["client"], entry)
    store["light"] = light
    async_add_entities([light])


class MobiusXR15Light(LightEntity, RestoreEntity):
    """The light itself.

    State is optimistic - the protocol offers no dependable readback of
    what the light is currently showing - and is restored across restarts.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, client: MobiusXR15Client, entry: ConfigEntry) -> None:
        self._client = client
        self._entry_id = entry.entry_id
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = format_mac(mac)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=entry.data.get(CONF_NAME, entry.title),
            manufacturer="EcoTech Marine",
            model="Radion XR15w G5 Pro",
        )
        self._attr_is_on = False
        self._attr_brightness = intensity_to_brightness(DEFAULT_INTENSITY)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
            if (brightness := last_state.attributes.get(ATTR_BRIGHTNESS)) is not None:
                self._attr_brightness = brightness

    def _recipe(self) -> dict[int, int]:
        store = self.hass.data[DOMAIN][self._entry_id]
        return {
            entity.channel: int(entity.native_value or 0)
            for entity in store.get("channel_numbers", [])
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        intensity = brightness_to_intensity(self._attr_brightness)
        if intensity == 0:
            intensity = DEFAULT_INTENSITY
            self._attr_brightness = intensity_to_brightness(intensity)

        if self._attr_is_on:
            # Already playing: retarget intensity, 2 packets instead of ~8.
            await self._client.async_set_intensity(intensity)
        else:
            await self._client.async_write_schedule(
                build_recipe_schedule(self._recipe()), intensity
            )

        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.async_write_schedule(build_blank_schedule(), DEFAULT_INTENSITY)
        self._attr_is_on = False
        self.async_write_ha_state()
