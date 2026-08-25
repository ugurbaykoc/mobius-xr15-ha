"""Turning the user's colour recipe into a day-long schedule."""
from __future__ import annotations

from .const import DAY_CURVE, MASTER_CHANNEL, MAX_INTENSITY, SCHEDULE_TIMES
from .protocol import make_slot


def brightness_to_intensity(brightness: int) -> int:
    return round(brightness / 255 * MAX_INTENSITY)


def intensity_to_brightness(intensity: int) -> int:
    return round(intensity / MAX_INTENSITY * 255)


def build_recipe_schedule(channel_values: dict[int, int], curve: bool = True) -> list[bytes]:
    """Write the recipe across the day.

    The device interpolates linearly between consecutive slots and wraps
    across midnight - confirmed by decompiling the Mobius app's own
    PointSchedule.getIntensitiesAtTime (see PROTOCOL.md). So scaling the
    master dimmer along DAY_CURVE gives a genuinely smooth sunrise/sunset
    with only these eleven points; the colour channels stay fixed so the
    colour balance is identical at every hour and only brightness moves.
    """
    master = int(channel_values.get(MASTER_CHANNEL, 0))
    slots = []
    for time_min, factor in zip(SCHEDULE_TIMES, DAY_CURVE):
        values = dict(channel_values)
        if curve:
            values[MASTER_CHANNEL] = max(0, min(MAX_INTENSITY, round(master * factor)))
        slots.append(make_slot(time_min, 0x01, values))
    return slots
