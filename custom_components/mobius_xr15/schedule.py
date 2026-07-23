"""Brightness conversions between HA (0-255) and the device (0-1000)."""
from __future__ import annotations

from .const import MAX_INTENSITY


def brightness_to_intensity(brightness: int) -> int:
    return round(brightness / 255 * MAX_INTENSITY)


def intensity_to_brightness(intensity: int) -> int:
    return round(intensity / MAX_INTENSITY * 255)
