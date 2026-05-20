"""In-memory data model for FbPro98 .pln gameplan files.

Defines the immutable types that the reader produces and the writer consumes:
ProfileType, CustomPlay, StockPlay, and the top-level GamePlan dataclass.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
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
    """A user-authored play stored as a filename reference (`stock_flag = 0`).

    See specs/pln.md section 2.3 for the on-disk layout.
    """

    filename: str
    """Filename of the .ply file backing this play, as written on disk (Windows
    path conventions; usually all-uppercase 8.3 form like `MYPLAY.PLY`)."""

    play_category: int
    """Game category byte. Bit 0 is the side-of-ball flag
    (odd = offense / kicking, even = defense / receiving)."""

    special_category: int
    """Special-teams category code (0 = not special teams; 1-10 = the ten
    special-teams categories defined by the game)."""

    user_category: int
    """User category byte. Bits 5-0 hold the game's play category;
    bits 7-6 vary across plays in the same category."""

    @property
    def name(self) -> str:
        """Display name: the filename's stem (without path or extension)."""
        return PureWindowsPath(self.filename).stem


@dataclass(frozen=True, slots=True)
class StockPlay:
    """A built-in play referenced from `STOCK98.MAP` (`stock_flag = 1`).

    See specs/pln.md section 2.3 for the on-disk layout.
    """

    play_name: str
    """Eight-character ASCII play name as stored on disk (with trailing
    nulls/spaces stripped)."""

    map_offset: int
    """Byte offset into `STOCK98.MAP` where this play's bytes begin."""

    map_size: int
    """Number of bytes this play occupies inside `STOCK98.MAP`."""

    play_category: int
    """Game category byte. Bit 0 is the side-of-ball flag
    (odd = offense / kicking, even = defense / receiving)."""

    special_category: int
    """Special-teams category code (0 = not special teams; 1-10 = the ten
    special-teams categories defined by the game)."""

    user_category: int
    """User category byte. Bits 5-0 hold the game's play category;
    bits 7-6 vary across plays in the same category."""

    @property
    def name(self) -> str:
        """Display name: the stock play name (same as `play_name`)."""
        return self.play_name


Play = CustomPlay | StockPlay


@dataclass(frozen=True, slots=True)
class GamePlan:
    """Full in-memory representation of a `.pln` gameplan file.

    See specs/pln.md for the on-disk binary format. Construction validates
    structural invariants (slot counts, side-of-ball consistency, special-
    category alignment, file-size parity) via __post_init__; ValueError is
    raised for any violation.
    """

    NUMBER_NORMAL_PLAYS: ClassVar[int] = 64
    """Number of normal (non-special, non-clock) play slots."""

    NUMBER_SPECIAL_SLOTS: ClassVar[int] = 20
    """Number of special-teams slots (10 categories × 2 custom/stock)."""

    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = 10
    """Number of distinct special-teams categories (kickoff, punt, FG, etc.)."""

    NUMBER_CLOCK_SLOTS: ClassVar[int] = 2
    """Number of clock-management slots (offense only; categories 11 and 12)."""

    NUMBER_PLAY_SLOTS: ClassVar[int] = 86
    """Total slot count in the G95 offsets table (64 normal + 20 special + 2 clock)."""

    profile_type: ProfileType
    """Whether this gameplan is for offense or defense. Determines clock-slot
    population and file-size parity."""

    normal_plays: tuple[Play | None, ...]
    """The 64 normal play slots. None indicates an unused slot."""

    special_plays: tuple[Play | None, ...]
    """The 20 special-teams slots, paired by category: (custom_1, stock_1,
    custom_2, stock_2, ..., custom_10, stock_10). Even indices hold CustomPlay
    or None; odd indices hold StockPlay or None."""

    clock_plays: tuple[Play | None, Play | None]
    """The 2 clock-management slots. Both must be populated for offense
    gameplans; both must be None for defense gameplans."""

    audible: bytes = b"\x00\x01\x02\x03"
    """Four-byte audible play reference stored in the G95 block."""

    map_filename: str = "STOCK98.MAP"
    """Filename of the stock-play map this gameplan references (stored in the
    S98 block)."""

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
            expected_category = i // 2 + 1
            if play.special_category != expected_category:
                raise ValueError(
                    f"Special slot {i} expects play with special_category={expected_category}, "
                    f"got special_category={play.special_category}"
                )

        expected_parity = 1 if self.is_offense else 0
        for label, plays in (
            ("normal", self.normal_plays),
            ("special", self.special_plays),
            ("clock", self.clock_plays),
        ):
            for i, play in enumerate(plays):
                if play is None:
                    continue
                if play.play_category % 2 != expected_parity:
                    play_side = "offensive" if play.play_category % 2 == 1 else "defensive"
                    gp_side = "OFFENSE" if expected_parity == 1 else "DEFENSE"
                    raise ValueError(
                        f"{label.capitalize()} slot {i}: play has {play_side} "
                        f"play_category=0x{play.play_category:02X}, but profile_type is {gp_side}"
                    )

        for i, play in enumerate(self.normal_plays):
            if play is None:
                continue
            if play.special_category != 0:
                raise ValueError(
                    f"Normal slot {i} contains a special-teams play (special_category="
                    f"{play.special_category}); only non-special-teams plays allowed in normal slots"
                )

        clock_special_categories = (11, 12)
        for i, play in enumerate(self.clock_plays):
            if play is None:
                continue
            expected = clock_special_categories[i]
            if play.special_category != expected:
                raise ValueError(
                    f"Clock slot {i} expects play with special_category={expected}, "
                    f"got special_category={play.special_category}"
                )

    @property
    def is_offense(self) -> bool:
        """True if this gameplan is for offense."""
        return self.profile_type == ProfileType.OFFENSE

    @property
    def is_defense(self) -> bool:
        """True if this gameplan is for defense."""
        return self.profile_type == ProfileType.DEFENSE

    @property
    def custom_special_plays(self) -> tuple[CustomPlay | None, ...]:
        """The 10 custom (user-authored) special-teams slots, in special_category
        order (1-10). Derived view over the even indices of `special_plays`."""
        return tuple(cast("CustomPlay | None", self.special_plays[i]) for i in range(0, self.NUMBER_SPECIAL_SLOTS, 2))

    @property
    def stock_special_plays(self) -> tuple[StockPlay | None, ...]:
        """The 10 stock special-teams slots, in special_category order (1-10).
        Derived view over the odd indices of `special_plays`; read-only."""
        return tuple(cast("StockPlay | None", self.special_plays[i]) for i in range(1, self.NUMBER_SPECIAL_SLOTS, 2))

    def with_normal_plays(self, plays: Sequence[Play | None]) -> GamePlan:
        """Return a new GamePlan with `plays` placed in the 64 normal slots.

        The original GamePlan is not mutated. Shorter sequences are right-padded
        with None to fill all 64 slots.

        Args:
            plays: Up to 64 plays (or None entries) in slot order.

        Returns:
            A new GamePlan with the updated normal slots; all other fields copied
            from self.

        Raises:
            ValueError: If `plays` contains more than 64 entries, or if the new
                GamePlan would violate any __post_init__ invariant.
        """
        if len(plays) > self.NUMBER_NORMAL_PLAYS:
            raise ValueError(f"Expected at most {self.NUMBER_NORMAL_PLAYS} normal plays, got {len(plays)}")
        padded = tuple(list(plays) + [None] * (self.NUMBER_NORMAL_PLAYS - len(plays)))
        return replace(self, normal_plays=padded)

    def with_custom_special_plays(self, plays: Iterable[CustomPlay | None]) -> GamePlan:
        """Return a new GamePlan with `plays` written into the 10 custom
        special-teams slots.

        Each play is placed into the slot dictated by its own `special_category`
        (1-10). Order doesn't matter. None entries in `plays` are ignored. Slots
        not covered by any play are cleared. The 10 stock special-teams slots
        (odd indices of the underlying `special_plays` tuple) are preserved.

        Args:
            plays: Iterable of CustomPlay (or None) values; each play's
                `special_category` selects its destination slot.

        Returns:
            A new GamePlan with the updated custom special-teams slots.

        Raises:
            ValueError: If any play's `special_category` is outside 1-10, or if
                two plays target the same category.
        """
        slots: list[CustomPlay | None] = [None] * self.NUMBER_SPECIAL_CATEGORIES
        for play in plays:
            if play is None:
                continue
            if not 1 <= play.special_category <= self.NUMBER_SPECIAL_CATEGORIES:
                raise ValueError(
                    f"Play has special_category={play.special_category}, must be 1..{self.NUMBER_SPECIAL_CATEGORIES}"
                )
            idx = play.special_category - 1
            if slots[idx] is not None:
                raise ValueError(f"Two custom special plays target special_category={play.special_category}")
            slots[idx] = play
        new_special: list[Play | None] = list(self.special_plays)
        for category_index, play in enumerate(slots):
            new_special[category_index * 2] = play
        return replace(self, special_plays=tuple(new_special))
