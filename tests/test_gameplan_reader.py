from __future__ import annotations

import struct
from pathlib import Path

import pytest

from fbpro98_gameplan import (
    CustomPlay,
    GamePlan,
    InvalidGamePlanError,
    StockPlay,
    parse_gameplan,
    read_gameplan,
)
from fbpro98_gameplan.pln.schema import G95_HEADER, J95_HEADER, J95_PLAN_DATA


TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
OFFENSE_PATH = TEST_DATA_DIR / "offense.pln"
DEFENSE_PATH = TEST_DATA_DIR / "defense.pln"


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real gameplan fixture: {path}")
    return path


def _load_fixture_bytes(path: Path) -> bytearray:
    return bytearray(_require_fixture(path).read_bytes())


def _first_used_slot_offset(data: bytes | bytearray) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset != 0:
            return slot, 12 + relative_offset
    raise AssertionError("Fixture does not contain any play records")


def _first_custom_record_offset(data: bytes | bytearray) -> tuple[int, int]:
    offsets = struct.unpack_from("<86H", data, 12)
    for slot, relative_offset in enumerate(offsets):
        if relative_offset == 0:
            continue
        record_offset = 12 + relative_offset
        if data[record_offset] == 0:
            return slot, record_offset
    pytest.skip("Fixture does not contain a custom play record")


def _g95_end(data: bytes | bytearray) -> int:
    _, g95_size = G95_HEADER.unpack_from(data, 0)
    return G95_HEADER.size + g95_size


def _s98_start(data: bytes | bytearray) -> int:
    return _g95_end(data) + J95_HEADER.size + J95_PLAN_DATA.size


def _assert_plan_sane(plan: GamePlan) -> None:
    assert isinstance(plan, GamePlan)

    has_any = (
        any(p is not None for p in plan.normal_plays)
        or any(p is not None for p in plan.special_plays)
        or any(p is not None for p in plan.clock_plays)
    )
    assert has_any

    for tup in (plan.normal_plays, plan.special_plays, plan.clock_plays):
        for play in tup:
            if play is None:
                continue
            assert isinstance(play, (CustomPlay, StockPlay))
            assert play.name


def test_real_offense_gameplan_parses():
    plan = read_gameplan(_require_fixture(OFFENSE_PATH))
    _assert_plan_sane(plan)
    assert plan.is_offense


def test_real_defense_gameplan_parses():
    plan = read_gameplan(_require_fixture(DEFENSE_PATH))
    _assert_plan_sane(plan)
    assert plan.is_defense


def test_parse_gameplan_from_buffer():
    buffer = _require_fixture(OFFENSE_PATH).read_bytes()
    plan = parse_gameplan(buffer)
    assert plan.is_offense
    _assert_plan_sane(plan)


# --- Validation tests below ----------------------------------------------------


def test_file_too_small_raises(tmp_path):
    gameplan_path = tmp_path / "tiny.pln"
    gameplan_path.write_bytes(b"G95:" + b"\x00" * 4)
    with pytest.raises(InvalidGamePlanError, match="File too small"):
        read_gameplan(gameplan_path)


def test_invalid_g95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data[0:4] = b"BAD!"
    gameplan_path = tmp_path / "bad_g95.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid header.*at 0x0"):
        read_gameplan(gameplan_path)


def test_g95_chunk_extends_past_eof_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    struct.pack_into("<I", data, 4, len(data) * 10)
    gameplan_path = tmp_path / "bad_g95_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="G95 chunk extends past"):
        read_gameplan(gameplan_path)


def test_invalid_audible_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data[8] = 0xFF
    gameplan_path = tmp_path / "bad_audible.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Audible"):
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


def test_invalid_stock_flag_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    _, record_offset = _first_custom_record_offset(data)
    data[record_offset] = 0x77
    gameplan_path = tmp_path / "bad_stock_flag.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid stock flag"):
        read_gameplan(gameplan_path)


def test_invalid_j95_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    data[j95_pos : j95_pos + 4] = b"BAD!"
    gameplan_path = tmp_path / "bad_j95.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_invalid_j95_payload_size_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    struct.pack_into("<I", data, j95_pos + 4, 99)
    gameplan_path = tmp_path / "bad_j95_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="J95 payload size"):
        read_gameplan(gameplan_path)


def test_invalid_profile_type_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_pos = _g95_end(data)
    data[j95_pos + J95_HEADER.size] = 5
    gameplan_path = tmp_path / "bad_profile.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="profile type"):
        read_gameplan(gameplan_path)


def test_j95_count_mismatch_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    j95_payload = _g95_end(data) + J95_HEADER.size
    struct.pack_into("<H", data, j95_payload + 1, 9999)
    gameplan_path = tmp_path / "bad_j95_count.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="J95 counts"):
        read_gameplan(gameplan_path)


def test_invalid_s98_header_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    data[s98_pos : s98_pos + 4] = b"BAD!"
    gameplan_path = tmp_path / "bad_s98.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="Invalid header"):
        read_gameplan(gameplan_path)


def test_invalid_s98_payload_size_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    struct.pack_into("<I", data, s98_pos + 4, 99)
    gameplan_path = tmp_path / "bad_s98_size.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="S98 payload size"):
        read_gameplan(gameplan_path)


def test_invalid_s98_payload_content_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    s98_pos = _s98_start(data)
    data[s98_pos + 8] = ord("X")
    gameplan_path = tmp_path / "bad_s98_content.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="S98 payload"):
        read_gameplan(gameplan_path)


def test_wrong_parity_raises(tmp_path):
    data = _load_fixture_bytes(OFFENSE_PATH)
    data.append(0)
    gameplan_path = tmp_path / "bad_parity.pln"
    gameplan_path.write_bytes(data)
    with pytest.raises(InvalidGamePlanError, match="wrong parity"):
        read_gameplan(gameplan_path)
