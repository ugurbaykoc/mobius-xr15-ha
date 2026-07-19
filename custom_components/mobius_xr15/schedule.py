"""Helpers for building a flat, single-recipe schedule from the color entities."""
from __future__ import annotations

from .const import FIXED_SCHEDULE_TIMES, MAX_INTENSITY
from .protocol import make_schedule_slot


def brightness_to_intensity(brightness: int) -> int:
    return round(brightness / 255 * MAX_INTENSITY)


def intensity_to_brightness(intensity: int) -> int:
    return round(intensity / MAX_INTENSITY * 255)


def build_flat_schedule(channel_numbers) -> list[bytes]:
    """Write the same channel mix at every known-good time point.

    channel_numbers: iterable of objects with .channel, .native_value
    """
    values = {entity.channel: int(entity.native_value or 0) for entity in channel_numbers}
    return [make_schedule_slot(time_min, 0x01, values) for time_min in FIXED_SCHEDULE_TIMES]
