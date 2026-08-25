"""Firmware features the light keeps state for by itself.

Both of these live on the device, not in Home Assistant: the light
carries on running them whether or not Home Assistant is up, which is
why they are read back rather than assumed. Their on/off state comes
from the periodic readback, and every write asks the light how wide the
value is first.
"""
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
from .coordinator import MobiusXR15Coordinator

SWITCHES: tuple[tuple[int, str, str, str], ...] = (
    (
        ATTR_ACCLIMATION_ENABLED,
        "acclimation",
        "Acclimation",
        "mdi:chart-timeline-variant",
    ),
    (ATTR_LUNAR_ENABLED, "lunar_phases", "Lunar Phases", "mdi:moon-waning-crescent"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the acclimation and lunar-phase switches."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    async_add_entities(
        MobiusXR15AttributeSwitch(store["coordinator"], mac, attr, key, label, icon)
        for attr, key, label, icon in SWITCHES
    )


class MobiusXR15AttributeSwitch(
    CoordinatorEntity[MobiusXR15Coordinator], SwitchEntity
):
    """A boolean attribute on the light."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MobiusXR15Coordinator,
        mac: str,
        attr: int,
        key: str,
        label: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_id = attr
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_name = label
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.value(self._attr_id)
        return None if value is None else bool(value)

    async def _async_set(self, value: int) -> None:
        await self.coordinator.client.async_write_attribute(self._attr_id, value)
        # Confirm from the light rather than assuming the write landed.
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(0)
