"""Constants for the Mobius XR15 integration."""

DOMAIN = "mobius_xr15"

DEFAULT_NAME = "Radion XR15w G5 Pro"

MAX_INTENSITY = 1000

# GATT characteristics on the light.
TX_FINAL_UUID = "01ff0104-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_DATA_UUID = "01ff0101-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_FINAL_UUID = "01ff0102-ba5e-f4ee-5ca1-eb1e5e4b1ce0"

# C2 protocol attributes (M$C2Attribute - see PROTOCOL.md).
ATTR_SCHEDULE1 = 500
ATTR_SCHEDULE_PLAYBACK = 510
ATTR_SCHEDULE1_INTENSITY = 511
SCHED_RESUME = bytes([1, 0])  # StartResume, duration Undefined

ATTR_PHYSICAL_VALUES = 101
ATTR_OPERATION_STATE = 104
ATTR_ERROR_STATE = 107
ATTR_MINUTE_OF_DAY = 203
ATTR_CURRENT_SCENE = 401

SLOT_COUNT = 25
BATCH_SIZE = 8  # 8 x 42B slots = 352B, safely inside the 517B MTU

# Channel ids in wire order for a 42-byte slot.
CHANNELS_42: tuple[int, ...] = (21, 23, 18, 17, 19, 20, 31, 32, 22, 16, 1, 101, 100)

# The eleven time points (minutes) the original schedule used, and the
# brightness curve applied across them. The device interpolates linearly
# between points, so these eleven produce a smooth day.
SCHEDULE_TIMES: tuple[int, ...] = (0, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1410)
DAY_CURVE: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.1)

# Channel 1 gates every other channel: at 0 the light stays dark no
# matter what the colours say. The day curve scales this one alone.
MASTER_CHANNEL = 1

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

# M$SceneID - instant effects written to attribute 401, no schedule
# write needed. (key, label, icon, scene id)
SCENES: tuple[tuple[str, str, str, int], ...] = (
    ("feed", "Feed Mode", "mdi:fish", 1),
    ("thunderstorm", "Thunderstorm", "mdi:weather-lightning", 6),
    ("cloud_cover", "Cloud Cover", "mdi:weather-cloudy", 7),
    ("color_cycle", "Color Cycle", "mdi:palette", 4),
    ("all_on", "All On", "mdi:lightbulb-on", 8),
    ("all_50", "All 50%", "mdi:lightbulb-on-50", 9),
    ("all_off", "All Off", "mdi:lightbulb-off", 3),
    ("clear_scene", "Clear Scene", "mdi:backup-restore", 0),
)

# Attributes exposed as switches. Their width is read from the light
# before every write - see MobiusXR15Client.async_write_attribute.
ATTR_ACCLIMATION_ENABLED = 902
ATTR_LUNAR_ENABLED = 907

# M$OperationState - what the device is doing right now.
OPERATION_STATES: dict[int, str] = {
    0: "Out of box",
    1: "Live demo",
    2: "Scene",
    3: "Schedule",
}

# M$ErrorState. The dosing-pump half of the enum is left out: this is a
# light, and an unmapped code still renders as its number.
ERROR_STATES: dict[int, str] = {
    0: "No error",
    1: "Disconnect",
    2: "Temperature",
    3: "Stall",
    4: "Thermistor",
    5: "Under voltage",
    6: "Power supply",
    7: "Schedule playback",
    8: "Over voltage",
    9: "Over current",
    15: "Fan fault",
    16: "Driver temperature",
    17: "LED channel short circuit",
    18: "LED channel current leak",
    19: "LED channel open circuit",
    20: "LED cluster thermistor",
    21: "LED cluster over temperature",
    22: "Device bricked",
    23: "Real-time clock",
    32: "Driver power section",
    67: "Wireless",
    68: "App upgrade",
    128: "PTC trip",
}

# M$PhysicalValues - indices into attribute 101. The scaling the
# firmware uses for each is not documented anywhere we can verify, so
# these are reported as raw numbers rather than dressed up with units
# that might be wrong by a factor of ten.
PHYSICAL_VALUES: dict[int, str] = {
    1: "Driver temperature",
    2: "Motor temperature",
    3: "Cluster temperature",
    4: "Motor power",
    5: "Motor RPM",
    6: "Battery voltage",
    7: "Input voltage",
    8: "Internal temperature",
    9: "Fan speed",
    10: "Motor temperature (stator)",
    11: "Gallons per hour",
    12: "Supply current",
    13: "Fan voltage",
    14: "Module temperature",
    15: "Motor spinning",
    16: "Cluster 2 temperature",
}
PHYSICAL_VALUE_COUNT = 17  # indices 0-16

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
