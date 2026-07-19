"""Helpers for building a schedule from the editable slot/channel entities."""
from __future__ import annotations

from .const import DEFAULT_SCHEDULE_POINTS, MAX_INTENSITY
from .protocol import make_schedule_slot

SLOT_COUNT = len(DEFAULT_SCHEDULE_POINTS)


def default_time(slot_index: int) -> str:
    """Initial HH:MM for a slot, before any user edits."""
    return DEFAULT_SCHEDULE_POINTS[slot_index]["time"]


def default_channel_value(slot_index: int, channel_id: int) -> int:
    """Initial value for a channel at a slot, before any user edits."""
    return DEFAULT_SCHEDULE_POINTS[slot_index]["channels"].get(channel_id, 0)


def brightness_to_intensity(brightness: int) -> int:
    return round(brightness / 255 * MAX_INTENSITY)


def intensity_to_brightness(intensity: int) -> int:
    return round(intensity / MAX_INTENSITY * 255)


def build_slots_from_entities(channel_numbers, slot_times) -> list[bytes]:
    """Build packed 42-byte schedule slots from the live helper entities.

    channel_numbers: iterable of objects with .slot, .channel, .native_value
    slot_times: iterable of objects with .slot, .native_value (a datetime.time)
    Slots are ordered by their configured time, so slots can be edited to a
    different order than they were created in.
    """
    values_by_slot: dict[int, dict[int, int]] = {}
    for entity in channel_numbers:
        values_by_slot.setdefault(entity.slot, {})[entity.channel] = int(entity.native_value or 0)

    time_by_slot = {entity.slot: entity.native_value for entity in slot_times}

    ordered = sorted(
        (
            (time_by_slot[slot].hour * 60 + time_by_slot[slot].minute, values_by_slot.get(slot, {}))
            for slot in time_by_slot
            if time_by_slot[slot] is not None
        ),
        key=lambda item: item[0],
    )
    return [make_schedule_slot(time_min, 0x01, channels) for time_min, channels in ordered]
