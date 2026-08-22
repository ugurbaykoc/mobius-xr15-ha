"""Apply-schedule action for the Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SCENES
from .schedule import brightness_to_intensity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the button entities."""
    mac = entry.data[CONF_MAC]
    async_add_entities(
        [
            MobiusXR15ApplyScheduleButton(hass, entry.entry_id, mac),
            MobiusXR15ResetBluetoothButton(hass, entry.entry_id, mac),
        ]
        + [
            MobiusXR15SceneButton(hass, entry.entry_id, mac, key, name, icon)
            for key, name, icon in SCENES
        ]
    )


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


class MobiusXR15ResetBluetoothButton(ButtonEntity):
    """Repairs a wedged Bluetooth adapter without needing SSH.

    Does what `systemctl restart bluetooth` was being used for: clears a
    stuck BLE connection, then power-cycles the adapter. The bridge also
    does this on its own after repeated failures - this is the manual
    escape hatch for the times it hasn't caught up yet.
    """

    _attr_has_entity_name = True
    _attr_name = "Reset Bluetooth"
    _attr_icon = "mdi:bluetooth-off"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry_id: str, mac: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_reset_bluetooth"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def available(self) -> bool:
        """Unavailable when the bridge itself is unreachable."""
        return self._hass.data[DOMAIN][self._entry_id]["coordinator"].last_update_success

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        await store["client"].async_reset_bluetooth()
        # The reset takes ~10s; refresh so Bridge Status reflects it.
        await store["coordinator"].async_request_refresh()


class MobiusXR15SceneButton(ButtonEntity):
    """Triggers one of the firmware's built-in scenes.

    Scenes are a single small write to attribute 401 - no 25-slot
    schedule involved - so they take effect in about a second and cost
    almost nothing on a marginal BLE link. The firmware runs the effect
    itself (thunderstorm and cloud cover are animated on-device) and
    returns to the schedule afterwards.
    """

    _attr_has_entity_name = True

    def __init__(
        self, hass: HomeAssistant, entry_id: str, mac: str,
        scene: str, name: str, icon: str,
    ) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._scene = scene
        self._attr_name = name
        self._attr_icon = icon
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_scene_{scene}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def available(self) -> bool:
        return self._hass.data[DOMAIN][self._entry_id]["coordinator"].last_update_success

    async def async_press(self) -> None:
        store = self._hass.data[DOMAIN][self._entry_id]
        await store["client"].async_scene(self._scene)
        light = store.get("light")
        if light is not None:
            if self._scene == "all_off":
                light._attr_is_on = False
                light.async_write_ha_state()
            elif self._scene in ("all_on", "all_50"):
                light._attr_is_on = True
                light.async_write_ha_state()
