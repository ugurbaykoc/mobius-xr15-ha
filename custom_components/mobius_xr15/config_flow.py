"""Config flow for the Mobius XR15 integration."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_MAC, CONF_NAME, CONF_URL
from homeassistant.helpers.device_registry import format_mac

from .const import DEFAULT_NAME, DEFAULT_URL, DOMAIN

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_URL, default=DEFAULT_URL): str,
    }
)


class MobiusXR15ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mobius XR15."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial setup: the light's MAC (device identity) and bridge URL."""
        errors: dict[str, str] = {}
        if user_input is not None:
            mac = user_input[CONF_MAC].strip()
            if not MAC_RE.match(mac):
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(format_mac(mac))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_MAC: mac.upper(),
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_URL: user_input[CONF_URL].strip(),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
