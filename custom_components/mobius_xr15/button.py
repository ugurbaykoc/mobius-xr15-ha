"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CURRENT_SCENE, DOMAIN, MASTER_CHANNEL, SCENES
from .coordinator import MobiusXR15Coordinator
from .presets import PRESETS
from .schedule import brightness_to_intensity, build_point_schedule, build_recipe_schedule


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the apply-schedule button, the scenes, and a manual refresh."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    entities: list[ButtonEntity] = [
        MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac),
        MobiusXR15RefreshButton(store["coordinator"], mac),
        MobiusXR15ImportScheduleButton(hass, entry.entry_id, mac),
    ]
    entities.extend(
        MobiusXR15SceneButton(store["client"], mac, key, label, icon, scene_id)
        for key, label, icon, scene_id in SCENES
    )
    entities.extend(
        MobiusXR15PresetButton(hass, entry.entry_id, mac, key, label, icon, points)
        for key, label, icon, points in PRESETS
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
        # Pushing the sliders means the sliders are what the user wants
        # on the light now, not a template installed earlier.
        store["preset_points"] = None
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


class MobiusXR15ImportScheduleButton(ButtonEntity):
    """Read the schedule the light is playing and adopt it here.

    The Mobius app's coral templates - LPS, SPS and the rest - are not
    in the app's own package; it downloads them. So rather than guess at
    their curves, this reads back whatever the light is actually
    playing. Apply a template in the app, press this, and the sliders
    hold that template's colours, with the whole curve recorded on the
    Schedule sensor.
    """

    _attr_has_entity_name = True
    _attr_name = "Import Schedule"
    _attr_icon = "mdi:download-circle-outline"

    def __init__(self, hass: HomeAssistant, entry_id: str, mac: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_import_schedule"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        slots = await store["client"].async_read_schedule()
        store["schedule"] = slots

        # Take the colours from the brightest point of the day: that is
        # the template's recipe, with the rest of the curve being the
        # same mix scaled down.
        lit = [slot for slot in slots if slot["channels"].get(MASTER_CHANNEL)]
        if lit:
            peak = max(lit, key=lambda slot: slot["channels"][MASTER_CHANNEL])
            for entity in store.get("channel_numbers", []):
                value = peak["channels"].get(entity.channel)
                if value is not None:
                    await entity.async_set_native_value(value)

        if (sensor := store.get("schedule_sensor")) is not None:
            sensor.async_write_ha_state()


class MobiusXR15PresetButton(ButtonEntity):
    """Install a captured schedule exactly as it was read off the light.

    This is not the slider recipe scaled across the day: it is the
    template's own points, so the blue-only dawn and the moonlight
    phase survive. The light remembers it, so turning off and on again
    restores the template rather than the sliders.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        mac: str,
        key: str,
        label: str,
        icon: str,
        points,
    ) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._points = points
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_preset_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        await store["client"].async_write_points_at_current_intensity(
            build_point_schedule(self._points)
        )
        # Remember it, so the light entity reinstalls this rather than
        # the sliders on the next off -> on.
        store["preset_points"] = self._points
        if (light := store.get("light")) is not None:
            light.set_on()
