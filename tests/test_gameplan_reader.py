from __future__ import annotations

import struct

import pytest

from fbpro98_gameplan import InvalidPLNError, PLN, read_gameplan


def custom_record(filename: str, *, play_category: int = 0, special_category: int = 0, user_category: int = 0) -> bytes:
    return (
        bytes([0, play_category, special_category, user_category])
        + filename.encode("ASCII")
        + b"\x00"
    )


def stock_record(
    play_name: str,
    *,
    play_category: int = 0,
    special_category: int = 0,
    user_category: int = 0,
    offset: int = 0x1000,
    size: int = 0x20,
) -> bytes:
    name_bytes = play_name.encode("ASCII")[:8].ljust(8, b" ")
    return (
        bytes([1, play_category, special_category, user_category])
        + struct.pack("<8sII", name_bytes, offset, size)
    )


def build_pln(records_by_slot: dict[int, bytes]) -> bytes:
    offsets = [0] * 84
    records = bytearray()
    table_size = 84 * 2
    for slot, record in sorted(records_by_slot.items()):
        offsets[slot] = table_size + len(records)
        records.extend(record)

    g95_payload = bytes([0, 1, 2, 3]) + struct.pack("<84H", *offsets) + bytes(records)
    j95_payload = struct.pack("<BHHH", 0, 0, 0, 0)
    s98_payload = b"STOCK98.MAP\x00"

    return (
        b"G95:"
        + struct.pack("<I", len(g95_payload))
        + g95_payload
        + b"J95:"
        + struct.pack("<I", len(j95_payload))
        + j95_payload
        + b"S98:"
        + struct.pack("<I", len(s98_payload))
        + s98_payload
    )


def test_read_gameplan_exposes_plays_by_slot_and_name(tmp_path):
    gameplan_path = tmp_path / "sample.pln"
    gameplan_path.write_bytes(
        build_pln(
            {
                0: custom_record(r"PNFL\Offense\RL\HBBlast.ply", play_category=9, user_category=5),
                5: stock_record("SHOTGUN", play_category=2, special_category=1, offset=0x1234, size=0x56),
                64: custom_record(r"PNFL\Special\FG\SAFE.ply", play_category=7),
                74: stock_record("KICKOFF", play_category=8),
            }
        )
    )

    plan = read_gameplan(gameplan_path)

    assert isinstance(plan, PLN)
    assert set(plan.normal_plays) == {"HBBlast", "SHOTGUN"}
    assert plan.normal_plays["HBBlast"].slot == 0
    assert plan.normal_plays["HBBlast"].get_name() == "HBBlast"
    assert plan.normal_plays["SHOTGUN"].offset == 0x1234
    assert plan.normal_plays["SHOTGUN"].special_flag == 1
    assert plan.special_plays["SAFE"].slot == 64
    assert plan.stock_special_plays["KICKOFF"].slot == 74
    assert plan.plays_by_slot[74].play_name == "KICKOFF"


def test_invalid_header_raises(tmp_path):
    gameplan_path = tmp_path / "bad_header.pln"
    data = build_pln({})
    gameplan_path.write_bytes(b"BAD!" + data[4:])

    with pytest.raises(InvalidPLNError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_out_of_range_offset_raises(tmp_path):
    gameplan_path = tmp_path / "bad_offset.pln"
    offsets = [0] * 84
    offsets[0] = 1
    g95_payload = bytes([0, 1, 2, 3]) + struct.pack("<84H", *offsets)
    gameplan_path.write_bytes(b"G95:" + struct.pack("<I", len(g95_payload)) + g95_payload)

    with pytest.raises(InvalidPLNError, match="out of range"):
        read_gameplan(gameplan_path)


def test_missing_null_terminator_raises(tmp_path):
    gameplan_path = tmp_path / "bad_string.pln"
    bad_record = bytes([0, 1, 0, 0]) + b"PNFL\\Offense\\RL\\BROKEN"
    gameplan_path.write_bytes(build_pln({0: bad_record}))

    with pytest.raises(InvalidPLNError, match="Missing null terminator"):
        read_gameplan(gameplan_path)
