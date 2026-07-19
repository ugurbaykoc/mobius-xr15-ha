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

SLOT_COUNT = 25
BATCH_SIZE = 8
MAX_INTENSITY = 1000

TX_FINAL_UUID = "01ff0104-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_DATA_UUID = "01ff0101-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
RX_FINAL_UUID = "01ff0102-ba5e-f4ee-5ca1-eb1e5e4b1ce0"
