"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CURRENT_SCENE, DOMAIN, SCENES
from .coordinator import MobiusXR15Coordinator
from .schedule import brightness_to_intensity, build_recipe_schedule


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the apply-schedule button, the scenes, and a manual refresh."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    entities: list[ButtonEntity] = [
        MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac),
        MobiusXR15RefreshButton(store["coordinator"], mac),
    ]
    entities.extend(
        MobiusXR15SceneButton(store["client"], mac, key, label, icon, scene_id)
        for key, label, icon, scene_id in SCENES
    )
    async_add_entities(entities)


class MobiusXR15ApplyScheduleButton(ButtonEntity):
    """Pushes the current channel values to the light.

    The light entity installs the recipe whenever it goes off -> on;
    this is for pushing slider edits while it is already on, without a
    full off/on cycle.
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
        channels = {
            entity.channel: int(entity.native_value or 0)
            for entity in store.get("channel_numbers", [])
        }
        light = store.get("light")
        if light is not None and not light.is_on:
            # Install the recipe without relighting the tank.
            intensity = 0
        elif light is not None and light.brightness is not None:
            intensity = brightness_to_intensity(light.brightness)
        else:
            intensity = 500
        await store["client"].async_write_schedule(build_recipe_schedule(channels), intensity)


class MobiusXR15SceneButton(ButtonEntity):
    """One of the light's built-in scenes.

    Scenes are instant: the firmware runs them itself, so pressing one
    is a single small write rather than a schedule install. Feed Mode
    and the weather scenes end on their own; Clear Scene puts the light
    back on its schedule.
    """

    _attr_has_entity_name = True

    def __init__(
        self, client, mac: str, key: str, label: str, icon: str, scene_id: int
    ) -> None:
        self._client = client
        self._scene_id = scene_id
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_scene_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_press(self) -> None:
        await self._client.async_write_attribute(ATTR_CURRENT_SCENE, self._scene_id)


class MobiusXR15RefreshButton(ButtonEntity):
    """Read the light's diagnostics now instead of waiting for the poll."""

    _attr_has_entity_name = True
    _attr_name = "Refresh Diagnostics"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str) -> None:
        self._coordinator = coordinator
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_refresh"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_press(self) -> None:
        await self._coordinator.async_request_refresh()
