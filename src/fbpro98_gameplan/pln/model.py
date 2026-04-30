"""In-memory data model for FbPro98 .pln gameplan files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, CustomPlay, StockPlay, and the top-level GamePlan dataclass.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import IntEnum
from pathlib import PureWindowsPath
from typing import ClassVar, cast


class ProfileType(IntEnum):
    """Whether a gameplan is for defense (0) or offense (1). Encoded in J95 plan data."""

    DEFENSE = 0
    OFFENSE = 1


@dataclass(frozen=True, slots=True)
class CustomPlay:
    """A user-authored play stored as a filename reference (`stock_flag = 0`)."""

    filename: str
    play_category: int
    special_category: int
    user_category: int

    @property
    def name(self) -> str:
        return PureWindowsPath(self.filename).stem


@dataclass(frozen=True, slots=True)
class StockPlay:
    """A built-in play referenced from `STOCK98.MAP` (`stock_flag = 1`)."""

    play_name: str
    map_offset: int
    map_size: int
    play_category: int
    special_category: int
    user_category: int

    @property
    def name(self) -> str:
        return self.play_name


Play = CustomPlay | StockPlay


@dataclass(frozen=True, slots=True)
class GamePlan:
    """Full in-memory representation of a `.pln` gameplan file."""

    NUMBER_NORMAL_PLAYS: ClassVar[int] = 64
    NUMBER_SPECIAL_SLOTS: ClassVar[int] = 20
    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 10
    NUMBER_CLOCK_SLOTS: ClassVar[int] = 2
    NUMBER_PLAY_SLOTS: ClassVar[int] = 86

    profile_type: ProfileType
    normal_plays: tuple[Play | None, ...]
    special_plays: tuple[Play | None, ...]
    clock_plays: tuple[Play | None, Play | None]
    audible: bytes = b"\x00\x01\x02\x03"
    map_filename: str = "STOCK98.MAP"

    def __post_init__(self) -> None:
        if len(self.normal_plays) != self.NUMBER_NORMAL_PLAYS:
            raise ValueError(
                f"normal_plays must have exactly {self.NUMBER_NORMAL_PLAYS} entries, got {len(self.normal_plays)}"
            )
        if len(self.special_plays) != self.NUMBER_SPECIAL_SLOTS:
            raise ValueError(
                f"special_plays must have exactly {self.NUMBER_SPECIAL_SLOTS} entries, got {len(self.special_plays)}"
            )
        if len(self.clock_plays) != self.NUMBER_CLOCK_SLOTS:
            raise ValueError(
                f"clock_plays must have exactly {self.NUMBER_CLOCK_SLOTS} entries, got {len(self.clock_plays)}"
            )

        if self.is_offense and any(p is None for p in self.clock_plays):
            raise ValueError("Offense gameplans require both clock plays")
        if self.is_defense and any(p is not None for p in self.clock_plays):
            raise ValueError("Defense gameplans must not have clock plays")

        for i, play in enumerate(self.special_plays):
            if play is None:
                continue
            if i % 2 == 0 and not isinstance(play, CustomPlay):
                raise ValueError(f"Special slot {i} (non-stock) must be CustomPlay or None, got {type(play).__name__}")
            if i % 2 == 1 and not isinstance(play, StockPlay):
                raise ValueError(f"Special slot {i} (stock) must be StockPlay or None, got {type(play).__name__}")

    @property
    def is_offense(self) -> bool:
        return self.profile_type == ProfileType.OFFENSE

    @property
    def is_defense(self) -> bool:
        return self.profile_type == ProfileType.DEFENSE

    @property
    def custom_special_plays(self) -> tuple[CustomPlay | None, ...]:
        """The 10 non-stock special-teams slots, in special_category order (1–10)."""
        return tuple(cast("CustomPlay | None", self.special_plays[i]) for i in range(0, self.NUMBER_SPECIAL_SLOTS, 2))

    @property
    def stock_special_plays(self) -> tuple[StockPlay | None, ...]:
        """The 10 stock special-teams slots, in special_category order (1–10). Read-only."""
        return tuple(cast("StockPlay | None", self.special_plays[i]) for i in range(1, self.NUMBER_SPECIAL_SLOTS, 2))

    def with_normal_plays(self, plays: Sequence[Play | None]) -> GamePlan:
        """Return a new GamePlan with `plays` placed in the 64 normal slots.

        Shorter sequences are right-padded with None to fill all 64 slots;
        longer sequences raise ValueError. Original GamePlan is not mutated.
        """
        if len(plays) > self.NUMBER_NORMAL_PLAYS:
            raise ValueError(f"Expected at most {self.NUMBER_NORMAL_PLAYS} normal plays, got {len(plays)}")
        padded = tuple(list(plays) + [None] * (self.NUMBER_NORMAL_PLAYS - len(plays)))
        return replace(self, normal_plays=padded)

    def with_custom_special_plays(self, plays: Sequence[CustomPlay | None]) -> GamePlan:
        """Return a new GamePlan with `plays` written into the 10 custom special-teams slots.

        Must be exactly NUMBER_SPECIAL_CATEGORIES (10) entries — one per category.
        These are stored at even indices (0, 2, 4, ...) of the underlying special_plays
        tuple; stock special plays at odd indices are preserved unchanged. Original
        GamePlan is not mutated.
        """
        if len(plays) != self.NUMBER_SPECIAL_CATEGORIES:
            raise ValueError(
                f"Expected exactly {self.NUMBER_SPECIAL_CATEGORIES} custom special plays, got {len(plays)}"
            )
        new_special: list[Play | None] = list(self.special_plays)
        for category_index, play in enumerate(plays):
            new_special[category_index * 2] = play
        return replace(self, special_plays=tuple(new_special))
