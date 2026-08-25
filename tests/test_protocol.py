"""Framing tests for the Mobius C2 packet builders.

Runnable on its own - `python3 tests/test_protocol.py` - because
protocol.py deliberately has no Home Assistant imports. The point is to
be able to check the wire format without a Home Assistant install, and
to keep the schedule packets that the light already accepts from
drifting while the read path grows around them.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "mobius_xr15"


def _load(name: str):
    package = sys.modules.setdefault("mobius_xr15_test_pkg", types.ModuleType("p"))
    package.__path__ = [str(COMPONENT)]
    spec = importlib.util.spec_from_file_location(
        f"mobius_xr15_test_pkg.{name}", COMPONENT / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"mobius_xr15_test_pkg.{name}"] = module
    spec.loader.exec_module(module)
    return module


const = _load("const")
protocol = _load("protocol")

# Captured from the light itself: a GET of attribute 511 answering 777.
REAL_REPLY = bytes.fromhex("02df17010000000800" "00ff01000102" "0903" "8ac1")


def test_parses_a_real_reply() -> None:
    assert protocol.parse_response([REAL_REPLY]) == {
        "status": 0,
        "attr": 511,
        "sub": 0,
        "count": 1,
        "elem_len": 2,
        "values": [777],
        "raw": "0903",
        "truncated": False,
    }


def test_joins_a_split_reply() -> None:
    # Long replies arrive across several notifications; reading only the
    # first one used to cut the body in half.
    assert protocol.parse_response([REAL_REPLY[:9], REAL_REPLY[9:]])["values"] == [777]


def test_rejects_anything_it_cannot_read() -> None:
    for junk in (b"", b"\x02\xdf\x17", b"nonsense"):
        assert protocol.parse_response([junk]) is None


def test_get_carries_sub_and_count() -> None:
    # A bare attribute id comes back as a status byte instead of a value.
    packet = protocol.build_get_packet(401, 1)
    assert packet[:3] == b"\x02\xde\x17"
    assert packet[9:13] == bytes([0x91, 0x01, 0, 1])
    assert protocol.crc16(packet[1:-2]) == int.from_bytes(packet[-2:], "little")


def test_set_length_comes_from_the_value() -> None:
    # The width is whatever the caller was told by the device - the
    # builder never picks one.
    # Payload starts at byte 9: attr(2) sub(1) count(1) elem_len(1) data.
    assert protocol.build_set_packet(401, bytes([6]), 2)[9:15] == bytes(
        [0x91, 0x01, 0, 1, 1, 6]
    )
    assert protocol.build_set_packet(401, bytes([6, 0]), 2)[9:16] == bytes(
        [0x91, 0x01, 0, 1, 2, 6, 0]
    )


def test_schedule_sequence_is_unchanged() -> None:
    sequence = protocol.build_write_sequence([protocol.make_slot(720, 1, {1: 1000})], 500)
    # 25 slots in batches of 8, then intensity, then resume playback.
    assert len(sequence) == 6
    assert len(sequence[0]) == 1 + 8 + (2 + 3 + 8 * 42) + 2 == 352
    assert protocol.build_intensity_packet(500, 9)[9:16] == bytes(
        [0xFF, 0x01, 0, 1, 2, 0xF4, 0x01]
    )
    assert protocol.build_playback_packet(const.SCHED_RESUME, 9)[9:16] == bytes(
        [0xFE, 0x01, 0, 1, 2, 1, 0]
    )
    for packet in sequence:
        assert protocol.crc16(packet[1:-2]) == int.from_bytes(packet[-2:], "little")


def test_slot_layout() -> None:
    slot = protocol.make_slot(720, 1, {1: 1000})
    assert len(slot) == 42
    assert slot[:3] == bytes([0xD0, 0x02, 1])  # 720 minutes, flags 1
    assert len(const.CHANNELS_42) == 13


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} passed")
