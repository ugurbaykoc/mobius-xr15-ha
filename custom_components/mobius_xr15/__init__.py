"""The Mobius XR15 integration (direct BLE via Home Assistant Bluetooth)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from .client import MobiusXR15Client
from .const import DOMAIN
from .coordinator import MobiusXR15Coordinator

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mobius XR15 from a config entry."""
    client = MobiusXR15Client(hass, entry.data[CONF_MAC])
    coordinator = MobiusXR15Coordinator(hass, entry, client)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    entry.async_on_unload(
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, lambda _event: hass.async_create_task(
                client.async_shutdown()
            )
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # The first read happens in the background: setup must not hang on a
    # radio link that has already proven it can be slow, and the light is
    # controllable whether or not its diagnostics answered.
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), name=f"{DOMAIN} first refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        store = hass.data[DOMAIN].pop(entry.entry_id)
        # The light accepts one connection at a time; do not walk away
        # still holding it.
        await store["client"].async_shutdown()
    return unloaded
