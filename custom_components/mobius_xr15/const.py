"""Constants for the Mobius XR15 integration."""

DOMAIN = "mobius_xr15"

DEFAULT_NAME = "Radion XR15w G5 Pro"

# The BLE bridge (xr15_server.py) running on the Docker host. All BLE
# protocol work lives there - this integration only speaks HTTP to it.
DEFAULT_URL = "http://127.0.0.1:8765"

MAX_INTENSITY = 1000

CHANNEL_NAMES: dict[int, str] = {
    21: "UV",
    23: "Violet",
    18: "Royal Blue",
    17: "Blue",
    19: "Green",
    20: "Red",
    32: "Moonlight Blue",
    22: "Warm White",
    16: "Cool White",
    1: "Brightness",
}

# Channels exposed as user-editable color sliders (the 3 unidentified
# protocol channels are left at 0 by the bridge and not exposed).
COLOR_CHANNELS: tuple[int, ...] = (21, 23, 18, 17, 19, 20, 32, 22, 16, 1)

# Default per-channel values, taken from the original schedule's noon peak.
DEFAULT_CHANNEL_VALUES: dict[int, int] = {
    21: 800,  # UV
    23: 900,  # Violet
    18: 1000,  # Royal Blue
    17: 800,  # Blue
    19: 300,  # Green
    20: 150,  # Red
    32: 0,  # Moonlight Blue
    22: 300,  # Warm White
    16: 300,  # Cool White
    1: 1000,  # Brightness
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
    22: "#fbbf24",  # Warm White - amber
    16: "#bae6fd",  # Cool White - pale cyan
    1: "#f8fafc",  # Brightness - near white
}
