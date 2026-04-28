from __future__ import annotations

import pytest

from fbpro98_gameplan import (
    CustomPlay,
    GamePlan,
    Play,
    ProfileType,
    StockPlay,
)


def _empty_normals() -> tuple[Play | None, ...]:
    return (None,) * GamePlan.NUMBER_NORMAL_PLAYS


def _empty_specials() -> tuple[Play | None, ...]:
    return (None,) * GamePlan.NUMBER_SPECIAL_SLOTS


def _make_custom() -> CustomPlay:
    return CustomPlay(filename="X.PLY", play_category=0, special_category=0, user_category=0)


def _make_stock() -> StockPlay:
    return StockPlay(
        play_name="X",
        map_offset=0,
        map_size=0,
        play_category=0,
        special_category=0,
        user_category=0,
    )


def _empty_defense() -> GamePlan:
    return GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals(),
        special_plays=_empty_specials(),
        clock_plays=(None, None),
    )


def test_defense_with_clock_plays_raises():
    with pytest.raises(ValueError, match="must not have clock plays"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(_make_stock(), None),
        )


def test_offense_without_clock_plays_raises():
    with pytest.raises(ValueError, match="require both clock plays"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(None, None),
        )


def test_offense_with_partial_clock_plays_raises():
    with pytest.raises(ValueError, match="require both clock plays"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(_make_stock(), None),
        )


def test_special_slot_custom_at_odd_index_raises():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    specials[1] = _make_custom()
    with pytest.raises(ValueError, match="must be StockPlay"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(specials),
            clock_plays=(None, None),
        )


def test_special_slot_stock_at_even_index_raises():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    specials[0] = _make_stock()
    with pytest.raises(ValueError, match="must be CustomPlay"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(specials),
            clock_plays=(None, None),
        )


def test_custom_special_plays_returns_10_entries():
    gameplan = _empty_defense()
    assert len(gameplan.custom_special_plays) == GamePlan.NUMBER_SPECIAL_CATEGORIES
    assert len(gameplan.stock_special_plays) == GamePlan.NUMBER_SPECIAL_CATEGORIES


def test_custom_and_stock_views_pick_correct_slots():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    custom = _make_custom()
    stock = _make_stock()
    specials[0] = custom  # category 1 non-stock
    specials[5] = stock  # category 3 stock
    gameplan = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals(),
        special_plays=tuple(specials),
        clock_plays=(None, None),
    )
    assert gameplan.custom_special_plays[0] is custom
    assert all(p is None for p in gameplan.custom_special_plays[1:])
    assert gameplan.stock_special_plays[2] is stock
    assert all(p is None for i, p in enumerate(gameplan.stock_special_plays) if i != 2)


def test_with_custom_special_plays_preserves_stock():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    stock_a = _make_stock()
    stock_b = _make_stock()
    specials[1] = stock_a  # category 1 stock
    specials[3] = stock_b  # category 2 stock
    gameplan = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals(),
        special_plays=tuple(specials),
        clock_plays=(None, None),
    )

    new_customs: list[CustomPlay | None] = [None] * GamePlan.NUMBER_SPECIAL_CATEGORIES
    new_customs[0] = _make_custom()
    new_customs[4] = _make_custom()

    updated = gameplan.with_custom_special_plays(new_customs)

    assert updated.special_plays[0] is new_customs[0]
    assert updated.special_plays[1] is stock_a
    assert updated.special_plays[3] is stock_b
    assert updated.special_plays[8] is new_customs[4]


def test_with_custom_special_plays_wrong_length_raises():
    gameplan = _empty_defense()
    with pytest.raises(ValueError, match="Expected exactly 10"):
        gameplan.with_custom_special_plays([None] * 5)


def test_with_custom_special_plays_rejects_stock_via_post_init():
    gameplan = _empty_defense()
    bad: list[CustomPlay | None] = [None] * GamePlan.NUMBER_SPECIAL_CATEGORIES
    bad[0] = _make_stock()  # type: ignore[list-item]
    with pytest.raises(ValueError, match="must be CustomPlay"):
        gameplan.with_custom_special_plays(bad)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("PNFL\\Offense\\PSR\\OR45RL01.PLY", "OR45RL01"),
        ("X.ply", "X"),
        ("X", "X"),
        ("dir\\sub\\PLAY.PLY", "PLAY"),
    ],
)
def test_custom_play_name_extracts_stem(filename: str, expected: str) -> None:
    play = CustomPlay(filename=filename, play_category=0, special_category=0, user_category=0)
    assert play.name == expected


def test_is_offense_and_is_defense_match_profile_type():
    custom = _make_custom()
    offense = GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=_empty_normals(),
        special_plays=_empty_specials(),
        clock_plays=(custom, custom),
    )
    assert offense.is_offense is True
    assert offense.is_defense is False

    defense = _empty_defense()
    assert defense.is_offense is False
    assert defense.is_defense is True


def test_with_normal_plays_returns_new_instance():
    gameplan = _empty_defense()
    updated = gameplan.with_normal_plays([_make_custom()])
    assert updated is not gameplan
    assert gameplan.normal_plays[0] is None
    assert updated.normal_plays[0] is not None


def test_normal_plays_wrong_length_raises():
    with pytest.raises(ValueError, match="normal_plays must have exactly"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=(None, None),
            special_plays=_empty_specials(),
            clock_plays=(None, None),
        )
