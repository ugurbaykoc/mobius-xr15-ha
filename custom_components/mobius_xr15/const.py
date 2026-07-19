"""Constants for the Mobius XR15 integration."""

DOMAIN = "mobius_xr15"

DEFAULT_NAME = "Radion XR15w G5 Pro"

# Mobius C2 protocol attribute IDs.
ATTR_SCHEDULE1 = 500
ATTR_SCHEDULE1_INTENSITY = 511
ATTR_SCHEDULE_PLAYBACK = 510

SCHED_RESUME = bytes([1, 0])

# Channel IDs, in wire order, for a 42-byte schedule slot.
CHANNELS_42: tuple[int, ...] = (21, 23, 18, 17, 19, 20, 31, 32, 22, 16, 1, 101, 100)

CHANNEL_NAMES: dict[int, str] = {
    21: "UV",
    23: "Violet",
    18: "Royal Blue",
    17: "Blue",
    19: "Green",
    20: "Red",
    31: "Unknown 31",
    32: "Moonlight Blue",
    22: "Warm White",
    16: "Cool White",
    1: "Brightness",
    101: "Unknown 101",
    100: "Unknown 100",
}

SLOT_COUNT = 25
BATCH_SIZE = 8
MAX_INTENSITY = 1000

TX_FINAL_UUID = "01ff0104-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_DATA_UUID = "01ff0101-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_FINAL_UUID = "01ff0102-ba5e-f4ee-5ca1-eb1e5e4b1ce0"

# The original reverse-engineered schedule wrote 11 time points across the
# day (dawn ramp, noon peak, dusk, night). The editable UI is now a single
# flat "color recipe" - no per-time-of-day editing - but the same 11 times
# are still used on the wire, all carrying that one recipe, since they're
# known-good against the device's schedule parser.
FIXED_SCHEDULE_TIMES: tuple[int, ...] = (0, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1410)

# Channels exposed as user-editable color sliders (excludes the 3 unknown
# channels, which are left at 0).
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
