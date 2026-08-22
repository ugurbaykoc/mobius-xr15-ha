"""Firmware feature toggles for the Mobius XR15 integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ACCLIMATION_ENABLED, ATTR_LUNAR_ENABLED, DOMAIN

SWITCHES: tuple[tuple[str, int, str, str], ...] = (
    ("acclimation_enabled", ATTR_ACCLIMATION_ENABLED, "Acclimation", "mdi:sprout"),
    ("lunar_enabled", ATTR_LUNAR_ENABLED, "Lunar Cycle", "mdi:moon-waning-crescent"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the firmware feature switches."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    async_add_entities(
        [
            MobiusXR15FeatureSwitch(store, mac, key, attr, name, icon)
            for key, attr, name, icon in SWITCHES
        ]
    )


class MobiusXR15FeatureSwitch(CoordinatorEntity, SwitchEntity):
    """A firmware feature the light runs by itself once enabled.

    Acclimation ramps intensity up gradually over a configured period so
    new corals are not shocked; the lunar cycle varies moonlight with the
    real moon phase. Both live in the device, not in Home Assistant - we
    only flip the attribute and read the state back from telemetry.
    """

    _attr_has_entity_name = True

    def __init__(
        self, store: dict, mac: str, key: str, attr: int, name: str, icon: str
    ) -> None:
        super().__init__(store["coordinator"])
        self._store = store
        self._key = key
        self._attr_id = attr
        self._attr_name = name
        self._attr_icon = icon
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def is_on(self) -> bool | None:
        """None until telemetry has actually read the device."""
        telemetry = (self.coordinator.data or {}).get("telemetry") or {}
        return telemetry.get(self._key)

    async def _async_set(self, value: int) -> None:
        await self._store["client"].async_write_attribute(self._attr_id, value)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(0)
