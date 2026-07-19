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

# Default per-slot schedule: the reverse-engineered coral + fish program
# (UV/blue-weighted, day simulation) that used to be hardcoded in
# protocol.py. Now only used to seed the editable number/time entities on
# first setup - after that, the live entity states are the source of truth.
# Channels omitted at a given time default to 0.
DEFAULT_SCHEDULE_POINTS: tuple[dict, ...] = (
    {"time": "00:00", "channels": {32: 150, 17: 50, 1: 200}},
    {"time": "06:00", "channels": {32: 300, 1: 400}},
    {"time": "08:00", "channels": {21: 200, 23: 300, 18: 400, 17: 300, 19: 100, 20: 50, 22: 100, 16: 100, 32: 100, 1: 600}},
    {"time": "10:00", "channels": {21: 600, 23: 700, 18: 800, 17: 600, 19: 200, 20: 100, 22: 200, 16: 200, 1: 800}},
    {"time": "12:00", "channels": {21: 800, 23: 900, 18: 1000, 17: 800, 19: 300, 20: 150, 22: 300, 16: 300, 1: 1000}},
    {"time": "14:00", "channels": {21: 800, 23: 900, 18: 1000, 17: 800, 19: 300, 20: 150, 22: 300, 16: 300, 1: 1000}},
    {"time": "16:00", "channels": {21: 600, 23: 700, 18: 800, 17: 600, 19: 200, 20: 100, 22: 200, 16: 200, 1: 800}},
    {"time": "18:00", "channels": {21: 200, 23: 300, 18: 400, 17: 300, 19: 100, 20: 50, 22: 100, 16: 100, 32: 100, 1: 600}},
    {"time": "20:00", "channels": {18: 100, 17: 100, 32: 300, 1: 400}},
    {"time": "22:00", "channels": {32: 150, 1: 200}},
    {"time": "23:30", "channels": {32: 50, 1: 100}},
)
