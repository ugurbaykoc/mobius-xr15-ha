"""HTTP client for the XR15 BLE bridge (xr15_server.py on the host).

There is deliberately no Bluetooth code in this integration anymore.
All BLE work is done by the standalone bridge script running directly
on the host (outside Docker, plain bleak straight to BlueZ) - the one
transport that has reliably controlled this light. Home Assistant only
makes local HTTP calls to it, which either succeed instantly or fail
loudly with a clear error.
"""
from __future__ import annotations

import asyncio

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# The bridge answers immediately (BLE work happens in its background
# task), so anything slower than this means the bridge is down.
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class MobiusXR15Client:
    """Thin async HTTP wrapper around the bridge's endpoints."""

    def __init__(self, hass: HomeAssistant, base_url: str) -> None:
        self._session = async_get_clientsession(hass)
        self._base_url = base_url.rstrip("/")

    async def _request(self, method: str, path: str, json: dict | None = None) -> None:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, json=json, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise HomeAssistantError(
                        f"XR15 bridge returned {resp.status} for {path}: {body[:200]}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HomeAssistantError(
                f"XR15 bridge unreachable at {url} - is xr15_server.py running "
                f"on the host? ({err})"
            ) from err

    async def async_status(self) -> dict:
        """Fetch bridge state + outcome of the last BLE command."""
        url = f"{self._base_url}/status"
        try:
            async with self._session.get(url, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    raise HomeAssistantError(f"XR15 bridge returned {resp.status} for /status")
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HomeAssistantError(
                f"XR15 bridge unreachable at {url} - is xr15_server.py running "
                f"on the host? ({err})"
            ) from err

    async def async_apply(self, channels: dict[int, int], intensity: int) -> None:
        """Install the flat color recipe with the given overall intensity."""
        await self._request(
            "POST",
            "/apply",
            json={"channels": {str(k): v for k, v in channels.items()}, "intensity": intensity},
        )

    async def async_set_intensity(self, intensity: int) -> None:
        """Retarget overall intensity without rewriting the schedule."""
        await self._request("GET", f"/intensity/{intensity}")

    async def async_turn_off(self) -> None:
        """Blank the schedule - the bridge's original, proven off path."""
        await self._request("GET", "/off")

    async def async_reset_bluetooth(self) -> None:
        """Clear a stuck BLE connection and power-cycle the adapter."""
        await self._request("POST", "/reset")

    async def async_scene(self, scene: str) -> None:
        """Trigger an instant scene (feed mode, thunderstorm, ...)."""
        await self._request("POST", "/scene", json={"scene": scene})

    async def async_write_attribute(self, attr: int, value: int) -> None:
        """Write any C2 attribute; the bridge sizes the payload itself."""
        await self._request("POST", "/attr", json={"attr": attr, "value": value})
