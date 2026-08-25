"""Diagnostic sensors for the Mobius XR15 integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ERROR_STATE,
    ATTR_MINUTE_OF_DAY,
    ATTR_OPERATION_STATE,
    ATTR_PHYSICAL_VALUES,
    DOMAIN,
    ERROR_STATES,
    OPERATION_STATES,
    PHYSICAL_VALUES,
)
from .coordinator import MobiusXR15Coordinator

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the diagnostic sensors."""
    store = hass.data[DOMAIN][entry.entry_id]
    mac = entry.data[CONF_MAC]
    coordinator: MobiusXR15Coordinator = store["coordinator"]
    async_add_entities(
        [
            MobiusXR15SignalSensor(store["client"], mac),
            MobiusXR15LastErrorSensor(store["client"], mac),
            MobiusXR15OperationStateSensor(coordinator, mac),
            MobiusXR15ErrorStateSensor(coordinator, mac),
            MobiusXR15ClockSensor(coordinator, mac),
            MobiusXR15TelemetrySensor(coordinator, mac),
        ]
    )


class MobiusXR15SignalSensor(SensorEntity):
    """Last-seen advertisement RSSI, as reported by Home Assistant.

    With a Bluetooth proxy next to the tank this reads the proxy's view
    of the light, which is the number that actually matters: it is the
    link commands travel over.
    """

    _attr_has_entity_name = True
    _attr_name = "Signal Strength"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, mac: str) -> None:
        self._client = client
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_rssi"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self) -> int | None:
        return self._client.rssi

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Per-radio RSSI, so a mis-placed proxy is visible at a glance.

        The state is the best of these; the attributes say which radio
        produced it and what the others hear.
        """
        sources = self._client.signal_sources
        if not sources:
            return {}
        best = max(sources, key=sources.get)
        return {"best_source": best, "sources": sources}


class MobiusXR15LastErrorSensor(SensorEntity):
    """Why the last command failed, or 'ok'.

    Saves digging through the log to tell a signal problem from a
    protocol one - the exception type is part of the state.
    """

    _attr_has_entity_name = True
    _attr_name = "Last Error"
    _attr_icon = "mdi:bluetooth-transfer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, mac: str) -> None:
        self._client = client
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_last_error"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def native_value(self) -> str:
        return (self._client.last_error or "ok")[:255]


class MobiusXR15ReadSensor(CoordinatorEntity[MobiusXR15Coordinator], SensorEntity):
    """Base for sensors fed by the periodic attribute readback."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str, key: str) -> None:
        super().__init__(coordinator)
        device_id = format_mac(mac)
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})


class MobiusXR15OperationStateSensor(MobiusXR15ReadSensor):
    """Whether the light is playing its schedule, a scene, or nothing."""

    _attr_name = "Operation State"
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "operation_state")

    @property
    def native_value(self) -> str | None:
        state = self.coordinator.value(ATTR_OPERATION_STATE)
        if state is None:
            return None
        return OPERATION_STATES.get(state, f"Unknown ({state})")


class MobiusXR15ErrorStateSensor(MobiusXR15ReadSensor):
    """The light's own error code, decoded.

    Distinct from Last Error, which is about our end of the radio: this
    is the light complaining about itself - an open LED channel, an
    over-temperature cluster, a clock it has lost.
    """

    _attr_name = "Device Error"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "device_error")

    @property
    def native_value(self) -> str | None:
        state = self.coordinator.value(ATTR_ERROR_STATE)
        if state is None:
            return None
        return ERROR_STATES.get(state, f"Error {state}")


class MobiusXR15ClockSensor(MobiusXR15ReadSensor):
    """The light's own clock, and how far it has drifted.

    The schedule runs on this clock, not on Home Assistant's. If a
    schedule fires at the wrong time - or never - this is the first
    thing to look at, and it is invisible without asking the device.
    """

    _attr_name = "Device Clock"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "device_clock")

    @property
    def native_value(self) -> str | None:
        minute = self.coordinator.value(ATTR_MINUTE_OF_DAY)
        if minute is None:
            return None
        return f"{minute // 60 % 24:02d}:{minute % 60:02d}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        minute = self.coordinator.value(ATTR_MINUTE_OF_DAY)
        if minute is None:
            return {}
        now = dt_util.now()
        drift = (minute - (now.hour * 60 + now.minute) + 720) % 1440 - 720
        return {"minute_of_day": minute, "drift_minutes": drift}


class MobiusXR15TelemetrySensor(MobiusXR15ReadSensor):
    """Everything attribute 101 reports, as raw numbers.

    The firmware's scaling for each index is not documented anywhere we
    can check, so nothing here is labelled with a unit it might not have
    - a temperature could be degrees or tenths of a degree, and guessing
    would produce a plausible, wrong reading. The state is how many
    values came back; the numbers themselves are attributes, ready to be
    matched against what the app shows for the same light.

    Off by default: enabling it is what starts the fifteen-minute poll.
    """

    _attr_name = "Telemetry"
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: MobiusXR15Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "telemetry")

    @property
    def native_value(self) -> int | None:
        reply = (self.coordinator.data or {}).get(ATTR_PHYSICAL_VALUES)
        return None if reply is None else len(reply["values"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reply = (self.coordinator.data or {}).get(ATTR_PHYSICAL_VALUES)
        if reply is None:
            return {}
        values = {
            PHYSICAL_VALUES.get(index, f"Index {index}"): value
            for index, value in enumerate(reply["values"])
            if index
        }
        return {**values, "raw": reply["raw"], "element_bytes": reply["elem_len"]}
