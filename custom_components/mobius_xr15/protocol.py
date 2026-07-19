"""Pure functions for building Mobius/EcoTech C2 BLE packets.

No I/O and no side effects: every function here takes data in and returns
bytes out, so the wire protocol can be reasoned about (and tested)
independently of the BLE transport that sends it.
"""
from __future__ import annotations

import struct

from .const import (
    ATTR_SCHEDULE1,
    ATTR_SCHEDULE1_INTENSITY,
    ATTR_SCHEDULE_PLAYBACK,
    BATCH_SIZE,
    CHANNELS_42,
    SCHED_RESUME,
    SLOT_COUNT,
)

CRC16_TABLE: tuple[int, ...] = (
    0, 4129, 8258, 12387, 16516, 20645, 24774, 28903,
    -32504, -28375, -24246, -20117, -15988, -11859, -7730, -3601,
    4657, 528, 12915, 8786, 21173, 17044, 29431, 25302,
    -27847, -31976, -19589, -23718, -11331, -15460, -3073, -7202,
    9314, 13379, 1056, 5121, 25830, 29895, 17572, 21637,
    -23190, -19125, -31448, -27383, -6674, -2609, -14932, -10867,
    13907, 9842, 5649, 1584, 30423, 26358, 22165, 18100,
    -18597, -22662, -26855, -30920, -2081, -6146, -10339, -14404,
    18628, 22757, 26758, 30887, 2112, 6241, 10242, 14371,
    -13876, -9747, -5746, -1617, -30392, -26263, -22262, -18133,
    23285, 19156, 31415, 27286, 6769, 2640, 14899, 10770,
    -9219, -13348, -1089, -5218, -25735, -29864, -17605, -21734,
    27814, 31879, 19684, 23749, 11298, 15363, 3168, 7233,
    -4690, -625, -12820, -8755, -21206, -17141, -29336, -25271,
    32407, 28342, 24277, 20212, 15891, 11826, 7761, 3696,
    -97, -4162, -8227, -12292, -16613, -20678, -24743, -28808,
    -28280, -32343, -20022, -24085, -12020, -16083, -3762, -7825,
    4224, 161, 12482, 8419, 20484, 16421, 28742, 24679,
    -31815, -27752, -23557, -19494, -15555, -11492, -7297, -3234,
    689, 4752, 8947, 13010, 16949, 21012, 25207, 29270,
    -18966, -23093, -27224, -31351, -2706, -6833, -10964, -15091,
    13538, 9411, 5280, 1153, 29798, 25671, 21540, 17413,
    -22565, -18438, -30823, -26696, -6305, -2178, -14563, -10436,
    9939, 14066, 1681, 5808, 26199, 30326, 17941, 22068,
    -9908, -13971, -1778, -5841, -26168, -30231, -18038, -22101,
    22596, 18533, 30726, 26663, 6336, 2273, 14466, 10403,
    -13443, -9380, -5313, -1250, -29703, -25640, -21573, -17510,
    19061, 23124, 27191, 31254, 2801, 6864, 10931, 14994,
    -722, -4849, -8852, -12979, -16982, -21109, -25112, -29239,
    31782, 27655, 23652, 19525, 15522, 11395, 7392, 3265,
    -4321, -194, -12451, -8324, -20581, -16454, -28711, -24584,
    28183, 32310, 20053, 24180, 11923, 16050, 3793, 7920,
)


def crc16(data: bytes) -> int:
    """Compute the CRC16 used to trail every C2 request frame."""
    crc = 0xFFFF
    for byte in data:
        crc = ((crc << 8) ^ (CRC16_TABLE[(byte ^ (crc >> 8)) & 0xFF] & 0xFFFF)) & 0xFFFF
    return crc


def _frame(opcode: int, msg_id: int, payload: bytes) -> bytes:
    """Wrap a payload in the 0xDE C2 request envelope with its CRC16 trailer."""
    body = (
        bytes([0xDE, opcode])
        + struct.pack("<H", msg_id)
        + b"\x00\x00"
        + struct.pack("<H", len(payload))
        + payload
    )
    return b"\x02" + body + struct.pack("<H", crc16(body))


def make_schedule_slot(
    time_min: int, flags: int, channel_values: dict[int, int] | None = None
) -> bytes:
    """Build one 42-byte schedule slot: time + flags + 13 channel values."""
    values = {channel: 0 for channel in CHANNELS_42}
    if channel_values:
        values.update(channel_values)
    channels = b"".join(
        bytes([channel]) + struct.pack("<H", values[channel]) for channel in CHANNELS_42
    )
    return struct.pack("<H", time_min) + bytes([flags]) + channels


def _pad_schedule(slots: list[bytes]) -> list[bytes]:
    return slots + [bytes(42)] * (SLOT_COUNT - len(slots))


def build_schedule_packet(sub: int, slots: list[bytes], msg_id: int) -> bytes:
    payload = struct.pack("<H", ATTR_SCHEDULE1) + bytes([sub, len(slots), 42]) + b"".join(slots)
    return _frame(0x18, msg_id, payload)


def build_intensity_packet(intensity: int, msg_id: int) -> bytes:
    value = struct.pack("<H", intensity)
    payload = struct.pack("<H", ATTR_SCHEDULE1_INTENSITY) + bytes([0, 1, len(value)]) + value
    return _frame(0x18, msg_id, payload)


def build_playback_packet(action: bytes, msg_id: int) -> bytes:
    payload = struct.pack("<H", ATTR_SCHEDULE_PLAYBACK) + bytes([0, 1, len(action)]) + action
    return _frame(0x18, msg_id, payload)


def build_write_sequence(slots: list[bytes], intensity: int) -> list[bytes]:
    """Full sequence to install a 25-slot schedule and resume playback."""
    padded = _pad_schedule(slots)
    packets: list[bytes] = []
    msg_id = 1
    for start in range(0, SLOT_COUNT, BATCH_SIZE):
        chunk = padded[start : start + BATCH_SIZE]
        packets.append(build_schedule_packet(start, chunk, msg_id))
        msg_id += 1
    packets.append(build_intensity_packet(intensity, msg_id))
    msg_id += 1
    packets.append(build_playback_packet(SCHED_RESUME, msg_id))
    return packets


def build_intensity_sequence(intensity: int) -> list[bytes]:
    """Lightweight sequence to retarget intensity without rewriting the schedule."""
    return [
        build_intensity_packet(intensity, 1),
        build_playback_packet(SCHED_RESUME, 2),
    ]


def build_blank_schedule() -> list[bytes]:
    """25 all-zero slots — the schedule plays silence (light off)."""
    return [bytes(42)] * SLOT_COUNT


def build_original_schedule() -> list[bytes]:
    """Coral + fish schedule (UV/blue-weighted, day simulation).

    Channel IDs: UV=21, Violet=23, RoyalBlue=18, Blue=17, Green=19, Red=20,
    WarmWhite=22, CoolWhite=16, MoonlightBlue=32, Brightness=1.
    Time is in minutes (e.g. 06:00 = 360).
    """

    def slot(time_min: int, flags: int, channels: dict[int, int] | None = None) -> bytes:
        return make_schedule_slot(time_min, flags, channels or {})

    slots = [
        # 00:00 - night darkness (start of day)
        slot(0, 0x01, {32: 150, 17: 50, 1: 200}),
        # 06:00 - soft wake-up, moonlight blue only
        slot(360, 0x01, {32: 300, 1: 400}),
        # 08:00 - gradual ramp-up
        slot(480, 0x01, {21: 200, 23: 300, 18: 400, 17: 300, 19: 100, 20: 50, 22: 100, 16: 100, 32: 100, 1: 600}),
        # 10:00 - morning
        slot(600, 0x01, {21: 600, 23: 700, 18: 800, 17: 600, 19: 200, 20: 100, 22: 200, 16: 200, 1: 800}),
        # 12:00 - peak (noon)
        slot(720, 0x01, {21: 800, 23: 900, 18: 1000, 17: 800, 19: 300, 20: 150, 22: 300, 16: 300, 1: 1000}),
        # 14:00 - peak continues
        slot(840, 0x01, {21: 800, 23: 900, 18: 1000, 17: 800, 19: 300, 20: 150, 22: 300, 16: 300, 1: 1000}),
        # 16:00 - afternoon, gradual decline
        slot(960, 0x01, {21: 600, 23: 700, 18: 800, 17: 600, 19: 200, 20: 100, 22: 200, 16: 200, 1: 800}),
        # 18:00 - evening starts
        slot(1080, 0x01, {21: 200, 23: 300, 18: 400, 17: 300, 19: 100, 20: 50, 22: 100, 16: 100, 32: 100, 1: 600}),
        # 20:00 - evening, blue/night tone
        slot(1200, 0x01, {18: 100, 17: 100, 32: 300, 1: 400}),
        # 22:00 - night mode
        slot(1320, 0x01, {32: 150, 1: 200}),
        # 23:30 - almost dark
        slot(1410, 0x01, {32: 50, 1: 100}),
    ]
    return slots
