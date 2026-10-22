"""Schedules captured from the light rather than invented here.

The Mobius app's coral templates are downloaded from EcoTech's servers,
so there is nothing to extract from its package. These are read off a
real XR15w G5 Pro with Import Schedule after applying the template in
the app - times, channels and values exactly as the firmware reported
them.

Keeping the original point times matters. They are not round numbers
because the app derives them from ramp durations, and the device
interpolates linearly between whatever points it is given: the odd
times are the shape.
"""
from __future__ import annotations

# Channel ids, for readability below. See CHANNEL_NAMES in const.py.
_UV, _VIOLET, _ROYAL_BLUE, _BLUE = 21, 23, 18, 17
_GREEN, _RED, _WARM_WHITE, _COOL_WHITE = 19, 20, 22, 16
_MOON_WHITE, _MOON_BLUE, _MASTER = 31, 32, 1

# (minute of day, {channel: 0-1000})
Points = tuple[tuple[int, dict[int, int]], ...]

# Read from the light on 2026-10-22 after applying LPS in Mobius.
#
# The character of it: whites held right down at 150 while every blue
# sits at full, which is what makes an LPS tank look the way it does.
# Dawn and dusk are blue-only at half master; the evening has its own
# moonlight phase on the two moonlight channels.
LPS: Points = (
    (180, {_MASTER: 1000}),  # 03:00 - anchor, colours dark
    (249, {_UV: 1000, _VIOLET: 1000, _ROYAL_BLUE: 1000, _BLUE: 1000, _MASTER: 500}),
    (
        319,  # 05:19 - full spectrum, start of the long plateau
        {
            _UV: 1000, _VIOLET: 1000, _ROYAL_BLUE: 1000, _BLUE: 1000,
            _GREEN: 200, _RED: 250, _WARM_WHITE: 150, _COOL_WHITE: 150,
            _MASTER: 1000,
        },
    ),
    (
        1163,  # 19:23 - end of the plateau, fourteen hours later
        {
            _UV: 1000, _VIOLET: 1000, _ROYAL_BLUE: 1000, _BLUE: 1000,
            _GREEN: 200, _RED: 250, _WARM_WHITE: 150, _COOL_WHITE: 150,
            _MASTER: 1000,
        },
    ),
    (1233, {_UV: 1000, _VIOLET: 1000, _ROYAL_BLUE: 1000, _BLUE: 1000, _MASTER: 500}),
    (1305, {_MOON_WHITE: 250, _MOON_BLUE: 250}),  # 21:45 - master 0, blues fade out
    (1314, {_MOON_WHITE: 1000, _MOON_BLUE: 1000, _MASTER: 1000}),
    (1353, {_MOON_WHITE: 1000, _MOON_BLUE: 1000, _MASTER: 1000}),
    (1364, {_MASTER: 1000}),  # 22:44 - colours dark again
)

# (key, label, icon, points)
PRESETS: tuple[tuple[str, str, str, Points], ...] = (
    ("lps", "LPS Program", "mdi:jellyfish-outline", LPS),
)
