"""Periodic readback of the light's own state.

Every poll costs a full BLE connection, and this link has already shown
what happens when something talks to the light more often than it needs
to. So: one connection, all six questions asked inside it, fifteen
minutes apart - and only while something is actually listening. Home
Assistant stops a coordinator that has no subscribed entities, so
disabling the diagnostic sensors really does stop the radio traffic.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MobiusXR15Client
from .const import (
    ATTR_ACCLIMATION_ENABLED,
    ATTR_ERROR_STATE,
    ATTR_LUNAR_ENABLED,
    ATTR_MINUTE_OF_DAY,
    ATTR_OPERATION_STATE,
    ATTR_PHYSICAL_VALUES,
    DOMAIN,
    PHYSICAL_VALUE_COUNT,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=15)

# (attribute, sub, count) - asked in this order over one connection.
READ_SPECS: list[tuple[int, int, int]] = [
    (ATTR_OPERATION_STATE, 0, 1),
    (ATTR_ERROR_STATE, 0, 1),
    (ATTR_MINUTE_OF_DAY, 0, 1),
    (ATTR_ACCLIMATION_ENABLED, 0, 1),
    (ATTR_LUNAR_ENABLED, 0, 1),
    (ATTR_PHYSICAL_VALUES, 0, PHYSICAL_VALUE_COUNT),
]


class MobiusXR15Coordinator(DataUpdateCoordinator[dict[int, dict[str, Any] | None]]):
    """Reads the diagnostic attributes on a slow schedule."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: MobiusXR15Client
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, dict[str, Any] | None]:
        try:
            return await self.client.async_read_attributes(READ_SPECS)
        except Exception as err:  # noqa: BLE001 - surfaced as an unavailable sensor
            raise UpdateFailed(str(err)) from err

    def value(self, attr: int) -> int | None:
        """First value of an attribute, or None if it was not read."""
        reply = (self.data or {}).get(attr)
        if reply is None or not reply["values"]:
            return None
        return reply["values"][0]
