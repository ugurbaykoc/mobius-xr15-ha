"""The Mobius XR15 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant

from .client import MobiusXR15Client
from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mobius XR15 from a config entry."""
    client = MobiusXR15Client(hass, entry.data[CONF_MAC])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"client": client}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
