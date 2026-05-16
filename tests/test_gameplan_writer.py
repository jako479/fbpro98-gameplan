from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from fbpro98_gameplan import (
    CustomPlay,
    StockPlay,
    build_gameplan_bytes,
    read_gameplan,
    write_gameplan,
)
from fbpro98_gameplan.schema import G95_HEADER, J95_HEADER, J95_PLAN_DATA

TEST_DATA_DIR = Path(__file__).resolve().parent / "data"
OFFENSE_PATH = TEST_DATA_DIR / "offense.pln"
DEFENSE_PATH = TEST_DATA_DIR / "defense.pln"


def _require_fixture(path: Path) -> Path:
    if not path.is_file():
        pytest.skip(f"Missing real gameplan fixture: {path}")
    return path


def _copy_fixture(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copy2(_require_fixture(src), dest)
    return dest


def _make_play(name: str) -> CustomPlay:
    return CustomPlay(
        filename=f"PNFL\\Offense\\PSR\\{name}.ply",
        play_category=9,
        special_category=0,
        user_category=5,
    )


def test_round_trip_byte_identity_offense(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original_bytes = pln_path.read_bytes()

    gameplan = read_gameplan(pln_path)
    write_gameplan(gameplan, pln_path)

    assert pln_path.read_bytes() == original_bytes


def test_build_gameplan_bytes_matches_file(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    gameplan = read_gameplan(pln_path)
    assert build_gameplan_bytes(gameplan) == pln_path.read_bytes()


def test_round_trip_byte_identity_defense(tmp_path: Path) -> None:
    pln_path = _copy_fixture(DEFENSE_PATH, tmp_path)
    original_bytes = pln_path.read_bytes()

    gameplan = read_gameplan(pln_path)
    write_gameplan(gameplan, pln_path)

    assert pln_path.read_bytes() == original_bytes


def test_round_trip_preserves_normal_plays(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    entries: list[CustomPlay | None] = []
    for play in original.normal_plays:
        if isinstance(play, CustomPlay):
            entries.append(play)
        else:
            entries.append(None)

    write_gameplan(original.with_normal_plays(entries), pln_path)
    reloaded = read_gameplan(pln_path)

    for slot, orig_play in enumerate(original.normal_plays):
        new_play = reloaded.normal_plays[slot]
        if not isinstance(orig_play, CustomPlay):
            assert new_play is None
        else:
            assert isinstance(new_play, CustomPlay)
            assert new_play.name == orig_play.name
            assert new_play.filename == orig_play.filename
            assert new_play.play_category == orig_play.play_category
            assert new_play.user_category == orig_play.user_category


def test_special_plays_preserved(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    write_gameplan(original.with_normal_plays([_make_play("TEST01")]), pln_path)
    reloaded = read_gameplan(pln_path)

    for i in range(reloaded.NUMBER_SPECIAL_SLOTS):
        orig_play = original.special_plays[i]
        new_play = reloaded.special_plays[i]
        if orig_play is None:
            assert new_play is None
        else:
            assert new_play is not None
            assert new_play.name == orig_play.name
            assert type(new_play) is type(orig_play)
            if isinstance(orig_play, StockPlay):
                assert isinstance(new_play, StockPlay)
                assert new_play.map_offset == orig_play.map_offset
                assert new_play.map_size == orig_play.map_size


def test_empty_slots_produce_zero_offset(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)
    write_gameplan(
        original.with_normal_plays([None, _make_play("TEST01"), None]),
        pln_path,
    )

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is None
    assert reloaded.normal_plays[1] is not None
    assert reloaded.normal_plays[1].name == "TEST01"
    assert reloaded.normal_plays[2] is None


def test_fewer_than_64_pads_remaining_empty(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(3)]
    write_gameplan(original.with_normal_plays(entries), pln_path)

    reloaded = read_gameplan(pln_path)
    filled = [p for p in reloaded.normal_plays if p is not None]
    assert len(filled) == 3
    for i in range(3, 64):
        assert reloaded.normal_plays[i] is None


def test_all_64_slots_filled(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(64)]
    write_gameplan(original.with_normal_plays(entries), pln_path)

    reloaded = read_gameplan(pln_path)
    filled = [p for p in reloaded.normal_plays if p is not None]
    assert len(filled) == 64


def test_too_many_entries_raises() -> None:
    original = read_gameplan(OFFENSE_PATH)
    entries = [_make_play(f"PLAY{i:02d}") for i in range(65)]
    with pytest.raises(ValueError, match="at most 64"):
        original.with_normal_plays(entries)


def test_j95_counts_updated(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)
    orig_buf = pln_path.read_bytes()
    _, orig_g95_size = G95_HEADER.unpack_from(orig_buf, 0)
    orig_g95_end = G95_HEADER.size + orig_g95_size
    _, _, orig_stock, orig_special = J95_PLAN_DATA.unpack_from(
        orig_buf,
        orig_g95_end + J95_HEADER.size,
    )

    entries = [_make_play(f"PLAY{i:02d}") for i in range(10)]
    write_gameplan(original.with_normal_plays(entries), pln_path)

    buf = pln_path.read_bytes()
    _, new_g95_size = G95_HEADER.unpack_from(buf, 0)
    g95_end = G95_HEADER.size + new_g95_size

    j95_data_offset = g95_end + J95_HEADER.size
    profile_type, num_custom, num_stock, num_special = J95_PLAN_DATA.unpack_from(
        buf,
        j95_data_offset,
    )

    assert num_custom == 10
    assert num_stock == orig_stock
    assert num_special == orig_special
    assert profile_type == 1


def test_defense_round_trip(tmp_path: Path) -> None:
    pln_path = _copy_fixture(DEFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    entries: list[CustomPlay | None] = []
    for play in original.normal_plays:
        if isinstance(play, CustomPlay):
            entries.append(play)
        else:
            entries.append(None)

    write_gameplan(original.with_normal_plays(entries), pln_path)
    reloaded = read_gameplan(pln_path)

    orig_filled = [p for p in original.normal_plays if isinstance(p, CustomPlay)]
    new_filled = [p for p in reloaded.normal_plays if isinstance(p, CustomPlay)]
    assert len(new_filled) == len(orig_filled)
    orig_names = {p.name for p in orig_filled}
    new_names = {p.name for p in new_filled}
    assert orig_names == new_names
