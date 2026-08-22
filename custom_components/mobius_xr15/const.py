"""Constants for the Mobius XR15 integration."""

DOMAIN = "mobius_xr15"

DEFAULT_NAME = "Radion XR15w G5 Pro"

# The BLE bridge (xr15_server.py) running on the Docker host. All BLE
# protocol work lives there - this integration only speaks HTTP to it.
DEFAULT_URL = "http://127.0.0.1:8765"

MAX_INTENSITY = 1000

# Names confirmed against the Mobius app's own M$VisualID enum (v2.26) -
# see PROTOCOL.md. Channel 31 is MoonlightWhite, and 100/101 are not LEDs
# at all but per-slot storm/cloud probabilities.
CHANNEL_NAMES: dict[int, str] = {
    21: "UV",
    23: "Violet",
    18: "Royal Blue",
    17: "Blue",
    19: "Green",
    20: "Red",
    32: "Moonlight Blue",
    31: "Moonlight White",
    22: "Warm White",
    16: "Cool White",
    # Channel 1 is the schedule's own master dimmer: if it is 0, the light
    # outputs nothing regardless of the color channels. Named to avoid
    # colliding with the light entity's brightness in the UI.
    1: "Master Dimmer",
    # Not LEDs at all: per-slot weather probabilities (M$VisualID 100/101)
    # that the firmware animates by itself.
    100: "Storm Probability",
    101: "Cloud Probability",
}

# LED channels plus the master dimmer, exposed as sliders. Channel 31
# (MoonlightWhite) is written too - a unit without it simply ignores the
# value, and attribute 901 (SupportedColorChannels) can confirm.
COLOR_CHANNELS: tuple[int, ...] = (21, 23, 18, 17, 19, 20, 32, 31, 22, 16, 1)

# Not LEDs: per-slot weather probabilities the firmware acts on itself
# (M$VisualID 100/101). Same 0-1000 scale, written into every slot.
WEATHER_CHANNELS: tuple[int, ...] = (100, 101)

# M$SceneID - instant effects, no schedule write needed.
SCENES: tuple[tuple[str, str, str], ...] = (
    ("feed", "Feed Mode", "mdi:fish"),
    ("thunderstorm", "Thunderstorm", "mdi:weather-lightning"),
    ("cloud_cover", "Cloud Cover", "mdi:weather-cloudy"),
    ("all_off", "All Off", "mdi:lightbulb-off"),
    ("all_on", "All On", "mdi:lightbulb-on"),
    ("all_50", "All 50%", "mdi:lightbulb-on-50"),
)

# Attributes exposed as switches (bridge reads their size before writing).
ATTR_ACCLIMATION_ENABLED = 902
ATTR_LUNAR_ENABLED = 907

# Default per-channel values, taken from the original schedule's noon peak.
DEFAULT_CHANNEL_VALUES: dict[int, int] = {
    21: 800,  # UV
    23: 900,  # Violet
    18: 1000,  # Royal Blue
    17: 800,  # Blue
    19: 300,  # Green
    20: 150,  # Red
    32: 0,  # Moonlight Blue
    31: 0,  # Moonlight White
    22: 300,  # Warm White
    16: 300,  # Cool White
    1: 1000,  # Master Dimmer
    100: 0,  # Storm Probability
    101: 0,  # Cloud Probability
}

# Approximate display color per channel, for a colored slider bar.
CHANNEL_COLORS: dict[int, str] = {
    21: "#7c3aed",  # UV - violet
    23: "#a855f7",  # Violet
    18: "#1d4ed8",  # Royal Blue
    17: "#3b82f6",  # Blue
    19: "#22c55e",  # Green
    20: "#ef4444",  # Red
    32: "#312e81",  # Moonlight Blue - deep indigo
    31: "#c7d2fe",  # Moonlight White - pale indigo
    22: "#fbbf24",  # Warm White - amber
    16: "#bae6fd",  # Cool White - pale cyan
    1: "#f8fafc",  # Master Dimmer - near white
    100: "#64748b",  # Storm Probability - slate
    101: "#94a3b8",  # Cloud Probability - light slate
}
