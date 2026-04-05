from __future__ import annotations

import struct
from pathlib import Path

import pytest

from fbpro98_gameplan import InvalidGamePlanError, GamePlan, read_gameplan


TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
OFFENSE_PATH = TEST_DATA_DIR / "offense.pln"
DEFENSE_PATH = TEST_DATA_DIR / "defense.pln"


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real gameplan fixture: {path}")
    return path


def _load_fixture_bytes(path: Path) -> bytearray:
    return bytearray(_require_fixture(path).read_bytes())


def _first_used_slot_offset(data: bytes) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset != 0:
            return slot, 12 + relative_offset
    raise AssertionError("Fixture does not contain any play records")


def _first_custom_record_offset(data: bytes) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset == 0:
            continue
        record_offset = 12 + relative_offset
        if data[record_offset] == 0:
            return slot, record_offset
    pytest.skip("Fixture does not contain a custom play record")


def _assert_plan_sane(plan: GamePlan) -> None:
    assert isinstance(plan, GamePlan)
    assert plan.plays_by_slot
    assert plan.normal_plays or plan.special_plays or plan.clock_plays

    for slot, play in plan.plays_by_slot.items():
        assert 0 <= slot < plan.NUMBER_PLAY_SLOTS
        assert play.slot == slot
        assert play.name
        if play.is_stock():
            assert play.stock_data is not None
            assert len(play.stock_data) == 6

        if slot < plan.NUMBER_NORMAL_PLAYS:
            assert play.name in plan.normal_plays
        elif slot < plan.NUMBER_NORMAL_PLAYS + plan.NUMBER_SPECIAL_SLOTS:
            assert play.name in plan.special_plays
        else:
            assert play.name in plan.clock_plays


def test_real_offense_gameplan_parses():
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    _assert_plan_sane(plan)


def test_real_defense_gameplan_parses():
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    _assert_plan_sane(plan)


def test_invalid_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data[0:4] = b"BAD!"
    gameplan_path = tmp_path / "bad_header.pln"
    gameplan_path.write_bytes(data)

    with pytest.raises(InvalidGamePlanError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_out_of_range_offset_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    slot, _ = _first_used_slot_offset(data)
    struct.pack_into("<H", data, 12 + (slot * 2), 1)
    gameplan_path = tmp_path / "bad_offset.pln"
    gameplan_path.write_bytes(data)

    with pytest.raises(InvalidGamePlanError, match="out of range"):
        read_gameplan(gameplan_path)


def test_missing_null_terminator_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    _, record_offset = _first_custom_record_offset(data)
    string_start = record_offset + 4
    string_end = data.index(0, string_start)
    data[string_end] = ord("X")
    gameplan_path = tmp_path / "bad_string.pln"
    gameplan_path.write_bytes(data)

    with pytest.raises(InvalidGamePlanError, match="Missing null terminator"):
        read_gameplan(gameplan_path)
