from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from fbpro98_gameplan import NormalPlayEntry, read_gameplan, write_normal_plays


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


def _make_entry(name: str, slot: int = 0) -> NormalPlayEntry:
    return NormalPlayEntry(
        filename=f"PNFL\\Offense\\PSR\\{name}.ply",
        play_category=9,
        special_category=0,
        user_category=5,
    )


def test_round_trip_preserves_normal_plays(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    entries: list[NormalPlayEntry | None] = []
    for slot in range(original.NUMBER_NORMAL_PLAYS):
        play = original.plays_by_slot.get(slot)
        if play is None or play.is_stock():
            entries.append(None)
        else:
            entries.append(NormalPlayEntry(
                filename=play.filename or "",
                play_category=play.play_category,
                special_category=play.special_category,
                user_category=play.user_category,
            ))

    write_normal_plays(pln_path, entries)
    reloaded = read_gameplan(pln_path)

    for slot in range(original.NUMBER_NORMAL_PLAYS):
        orig_play = original.plays_by_slot.get(slot)
        new_play = reloaded.plays_by_slot.get(slot)
        if orig_play is None:
            assert new_play is None
        else:
            assert new_play is not None
            assert new_play.name == orig_play.name
            assert new_play.filename == orig_play.filename
            assert new_play.play_category == orig_play.play_category
            assert new_play.user_category == orig_play.user_category


def test_special_plays_preserved(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    write_normal_plays(pln_path, [_make_entry("TEST01")])
    reloaded = read_gameplan(pln_path)

    for slot in range(64, 84):
        orig_play = original.plays_by_slot.get(slot)
        new_play = reloaded.plays_by_slot.get(slot)
        if orig_play is None:
            assert new_play is None
        else:
            assert new_play is not None
            assert new_play.name == orig_play.name
            assert new_play.stock_flag == orig_play.stock_flag
            if orig_play.is_stock():
                assert new_play.stock_data == orig_play.stock_data


def test_empty_slots_produce_zero_offset(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    write_normal_plays(pln_path, [None, _make_entry("TEST01"), None])

    reloaded = read_gameplan(pln_path)
    assert 0 not in reloaded.plays_by_slot
    assert 1 in reloaded.plays_by_slot
    assert reloaded.plays_by_slot[1].name == "TEST01"
    assert 2 not in reloaded.plays_by_slot


def test_fewer_than_64_pads_remaining_empty(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    entries = [_make_entry(f"PLAY{i:02d}") for i in range(3)]
    write_normal_plays(pln_path, entries)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 3
    for slot in range(3, 64):
        assert slot not in reloaded.plays_by_slot


def test_all_64_slots_filled(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)
    entries = [_make_entry(f"PLAY{i:02d}") for i in range(64)]
    write_normal_plays(pln_path, entries)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 64


def test_too_many_entries_raises() -> None:
    entries = [_make_entry(f"PLAY{i:02d}") for i in range(65)]
    with pytest.raises(ValueError, match="at most 64"):
        write_normal_plays(OFFENSE_PATH, entries)


def test_j95_counts_updated(tmp_path: Path) -> None:
    pln_path = _copy_fixture(OFFENSE_PATH, tmp_path)

    # Read original J95 counts before writing.
    from fbpro98_gameplan.pln.schema import J95_HEADER, J95_PLAN_DATA
    original = read_gameplan(pln_path)
    orig_buf = pln_path.read_bytes()
    orig_g95_end = 8 + original.g95_size
    _, _, orig_stock, orig_special = J95_PLAN_DATA.unpack_from(
        orig_buf, orig_g95_end + J95_HEADER.size,
    )

    entries = [_make_entry(f"PLAY{i:02d}") for i in range(10)]
    write_normal_plays(pln_path, entries)

    buf = pln_path.read_bytes()
    reloaded = read_gameplan(pln_path)
    g95_end = 8 + reloaded.g95_size

    j95_payload_offset = g95_end + J95_HEADER.size
    profile_type, num_custom, num_stock, num_special = J95_PLAN_DATA.unpack_from(
        buf, j95_payload_offset,
    )

    assert num_custom == 10
    assert num_stock == orig_stock
    assert num_special == orig_special
    assert profile_type == 1  # offense


def test_defense_round_trip(tmp_path: Path) -> None:
    pln_path = _copy_fixture(DEFENSE_PATH, tmp_path)
    original = read_gameplan(pln_path)

    entries: list[NormalPlayEntry | None] = []
    for slot in range(original.NUMBER_NORMAL_PLAYS):
        play = original.plays_by_slot.get(slot)
        if play is None or play.is_stock():
            entries.append(None)
        else:
            entries.append(NormalPlayEntry(
                filename=play.filename or "",
                play_category=play.play_category,
                special_category=play.special_category,
                user_category=play.user_category,
            ))

    write_normal_plays(pln_path, entries)
    reloaded = read_gameplan(pln_path)

    assert len(reloaded.normal_plays) == len(original.normal_plays)
    for name in original.normal_plays:
        assert name in reloaded.normal_plays
