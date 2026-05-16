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


def _make_custom(*, special_category: int = 1, play_category: int = 0) -> CustomPlay:
    return CustomPlay(
        filename="X.PLY",
        play_category=play_category,
        special_category=special_category,
        user_category=0,
    )


def _make_stock(*, special_category: int = 1, play_category: int = 0) -> StockPlay:
    return StockPlay(
        play_name="X",
        map_offset=0,
        map_size=0,
        play_category=play_category,
        special_category=special_category,
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
    custom = _make_custom(special_category=1)
    stock = _make_stock(special_category=3)
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
    stock_a = _make_stock(special_category=1)
    stock_b = _make_stock(special_category=2)
    specials[1] = stock_a  # category 1 stock
    specials[3] = stock_b  # category 2 stock
    gameplan = GamePlan(
        profile_type=ProfileType.DEFENSE,
        normal_plays=_empty_normals(),
        special_plays=tuple(specials),
        clock_plays=(None, None),
    )

    new_customs: list[CustomPlay | None] = [None] * GamePlan.NUMBER_SPECIAL_CATEGORIES
    new_customs[0] = _make_custom(special_category=1)
    new_customs[4] = _make_custom(special_category=5)

    updated = gameplan.with_custom_special_plays(new_customs)

    assert updated.special_plays[0] is new_customs[0]
    assert updated.special_plays[1] is stock_a
    assert updated.special_plays[3] is stock_b
    assert updated.special_plays[8] is new_customs[4]


def test_with_custom_special_plays_accepts_partial_input():
    """Plays are placed by their own special_category; missing categories stay empty."""
    gameplan = _empty_defense()
    updated = gameplan.with_custom_special_plays([_make_custom(special_category=2), _make_custom(special_category=5)])
    placed = updated.custom_special_plays
    assert placed[1] is not None and placed[1].special_category == 2
    assert placed[4] is not None and placed[4].special_category == 5
    for i, p in enumerate(placed):
        if i not in (1, 4):
            assert p is None


def test_with_custom_special_plays_order_independent():
    """Same set of plays in any order produces the same result."""
    gameplan = _empty_defense()
    a = _make_custom(special_category=3)
    b = _make_custom(special_category=7)
    c = _make_custom(special_category=1)
    out_one = gameplan.with_custom_special_plays([a, b, c])
    out_two = gameplan.with_custom_special_plays([c, b, a])
    assert out_one.custom_special_plays == out_two.custom_special_plays


def test_with_custom_special_plays_rejects_stock_via_post_init():
    """A StockPlay sneaked in still trips __post_init__'s type check."""
    gameplan = _empty_defense()
    with pytest.raises(ValueError, match="must be CustomPlay"):
        gameplan.with_custom_special_plays([_make_stock()])  # type: ignore[list-item]


def test_special_slot_category_mismatch_in_init_raises():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    specials[2] = _make_custom(special_category=5)  # slot 2 expects category 2, got 5
    with pytest.raises(ValueError, match="special_category=2"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(specials),
            clock_plays=(None, None),
        )


def test_with_custom_special_plays_out_of_range_category_raises():
    gameplan = _empty_defense()
    with pytest.raises(ValueError, match="must be 1..10"):
        gameplan.with_custom_special_plays([_make_custom(special_category=11)])


def test_with_custom_special_plays_duplicate_category_raises():
    gameplan = _empty_defense()
    with pytest.raises(ValueError, match="Two custom special plays target special_category=3"):
        gameplan.with_custom_special_plays([_make_custom(special_category=3), _make_custom(special_category=3)])


def test_offensive_play_in_defensive_gameplan_raises():
    normals: list[Play | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=1)  # odd = offensive
    with pytest.raises(ValueError, match="profile_type is DEFENSE"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=tuple(normals),
            special_plays=_empty_specials(),
            clock_plays=(None, None),
        )


def test_defensive_play_in_offensive_gameplan_raises():
    normals: list[Play | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=0, play_category=0)  # even = defensive
    spike = _make_custom(special_category=11, play_category=1)
    kneel = _make_custom(special_category=12, play_category=1)
    with pytest.raises(ValueError, match="profile_type is OFFENSE"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=tuple(normals),
            special_plays=_empty_specials(),
            clock_plays=(spike, kneel),
        )


def test_special_teams_play_in_normal_slot_raises():
    normals: list[Play | None] = [None] * GamePlan.NUMBER_NORMAL_PLAYS
    normals[0] = _make_custom(special_category=2, play_category=0)  # special-teams play
    with pytest.raises(ValueError, match="Normal slot 0 contains a special-teams play"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=tuple(normals),
            special_plays=_empty_specials(),
            clock_plays=(None, None),
        )


def test_clock_slot_wrong_special_category_raises():
    bad_spike = _make_custom(special_category=2, play_category=1)  # should be 11
    kneel = _make_custom(special_category=12, play_category=1)
    with pytest.raises(ValueError, match="Clock slot 0 expects play with special_category=11"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(bad_spike, kneel),
        )


def test_special_plays_wrong_length_raises():
    with pytest.raises(ValueError, match="special_plays must have exactly"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=(None,) * 5,
            clock_plays=(None, None),
        )


def test_clock_plays_wrong_length_raises():
    with pytest.raises(ValueError, match="clock_plays must have exactly"):
        GamePlan(
            profile_type=ProfileType.DEFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(None,),  # type: ignore[arg-type]
        )


def test_defensive_special_play_in_offensive_gameplan_raises():
    specials: list[Play | None] = [None] * GamePlan.NUMBER_SPECIAL_SLOTS
    specials[0] = _make_custom(special_category=1, play_category=0)  # even = defensive
    spike = _make_custom(special_category=11, play_category=1)
    kneel = _make_custom(special_category=12, play_category=1)
    with pytest.raises(ValueError, match="profile_type is OFFENSE"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=_empty_normals(),
            special_plays=tuple(specials),
            clock_plays=(spike, kneel),
        )


def test_defensive_clock_play_in_offensive_gameplan_raises():
    bad_spike = _make_custom(special_category=11, play_category=0)  # even = defensive
    kneel = _make_custom(special_category=12, play_category=1)
    with pytest.raises(ValueError, match="Clock slot 0:.*profile_type is OFFENSE"):
        GamePlan(
            profile_type=ProfileType.OFFENSE,
            normal_plays=_empty_normals(),
            special_plays=_empty_specials(),
            clock_plays=(bad_spike, kneel),
        )


def test_with_normal_plays_too_many_raises():
    gameplan = _empty_defense()
    with pytest.raises(ValueError, match="Expected at most 64 normal plays"):
        gameplan.with_normal_plays([_make_custom(special_category=0)] * 65)


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
    spike = _make_custom(special_category=11, play_category=1)
    kneel = _make_custom(special_category=12, play_category=1)
    offense = GamePlan(
        profile_type=ProfileType.OFFENSE,
        normal_plays=_empty_normals(),
        special_plays=_empty_specials(),
        clock_plays=(spike, kneel),
    )
    assert offense.is_offense is True
    assert offense.is_defense is False

    defense = _empty_defense()
    assert defense.is_offense is False
    assert defense.is_defense is True


def test_with_normal_plays_returns_new_instance():
    gameplan = _empty_defense()
    updated = gameplan.with_normal_plays([_make_custom(special_category=0)])
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
