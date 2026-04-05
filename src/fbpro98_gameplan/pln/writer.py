from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .model import GamePlanPlay
from .reader import GamePlan
from .schema import (
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_PLAY_STOCK_TAIL,
    ID_G95,
    J95_HEADER,
    J95_PLAN_DATA,
    S98_HEADER,
)

StrPath = str | PathLike[str]


@dataclass(frozen=True, slots=True)
class NormalPlayEntry:
    filename: str
    play_category: int
    special_category: int
    user_category: int


def write_normal_plays(
    path: StrPath,
    entries: Sequence[NormalPlayEntry | None],
) -> None:
    """Update the 64 normal-play slots in an existing .pln file.

    Slots 64-83 (special-teams plays) and 84-85 (clock plays) are preserved.
    J95 counts are recalculated. S98 chunk is preserved.

    ``entries`` must have at most 64 items. Each item is either a
    ``NormalPlayEntry`` (custom play) or ``None`` (empty slot).
    """
    path = Path(path)
    buffer = path.read_bytes()
    gameplan = GamePlan.from_buffer(buffer, path)

    if len(entries) > GamePlan.NUMBER_NORMAL_PLAYS:
        raise ValueError(
            f"Expected at most {GamePlan.NUMBER_NORMAL_PLAYS} entries, got {len(entries)}"
        )

    padded = list(entries) + [None] * (GamePlan.NUMBER_NORMAL_PLAYS - len(entries))

    # Collect existing special-teams play records (slots 64-83) in slot order.
    preserved_plays: list[GamePlanPlay] = []
    for slot in range(GamePlan.NUMBER_NORMAL_PLAYS, GamePlan.NUMBER_PLAY_SLOTS):
        play = gameplan.plays_by_slot.get(slot)
        if play is not None:
            preserved_plays.append(play)

    # Build play records blob and offsets table (86 entries: 64 normal + 20 special + 2 clock).
    offsets = [0] * GamePlan.NUMBER_PLAY_SLOTS
    records = bytearray()
    records_base = G95_HEADER.size + G95_OFFSETS_TABLE.size

    # Write normal play records (slots 0-63).
    for slot, entry in enumerate(padded):
        if entry is None:
            continue
        offsets[slot] = records_base + len(records) - G95_HEADER.size
        records += G95_PLAY_HEADER.pack(
            0, entry.play_category, entry.special_category, entry.user_category,
        )
        records += entry.filename.encode("ascii") + b"\x00"

    # Preserve clock slot offsets (84-85) from the original file.
    orig_offsets = G95_OFFSETS_TABLE.unpack_from(buffer, G95_HEADER.size)
    clock_start = GamePlan.NUMBER_NORMAL_PLAYS + GamePlan.NUMBER_SPECIAL_SLOTS
    for slot in range(clock_start, GamePlan.NUMBER_PLAY_SLOTS):
        offsets[slot] = orig_offsets[slot]

    # Write preserved special-teams play records (slots 64-83).
    for play in preserved_plays:
        offsets[play.slot] = records_base + len(records) - G95_HEADER.size
        if play.is_custom():
            records += G95_PLAY_HEADER.pack(
                0, play.play_category, play.special_category, play.user_category,
            )
            records += (play.filename or "").encode("ascii") + b"\x00"
        elif play.is_stock():
            records += G95_PLAY_HEADER.pack(
                1, play.play_category, play.special_category, play.user_category,
            )
            name_bytes = (play.play_name or "").encode("ascii").ljust(8, b"\x00")[:8]
            records += G95_PLAY_STOCK_TAIL.pack(name_bytes, play.stock_data or b"\x00" * 6)

    # Build G95 chunk.
    g95_payload_size = G95_OFFSETS_TABLE.size + 4 + len(records)  # offsets + audible + records
    g95 = bytearray()
    g95 += G95_HEADER.pack(ID_G95, g95_payload_size, gameplan.audible)
    g95 += G95_OFFSETS_TABLE.pack(*offsets)
    g95 += records

    # Build J95 counts from the plays we're writing.
    num_custom = sum(1 for e in padded if e is not None)
    num_stock = 0  # normal slots only contain custom plays for now
    num_special = sum(1 for p in preserved_plays if p.is_custom())

    g95_original_end = 8 + gameplan.g95_size
    _, j95_size = J95_HEADER.unpack_from(buffer, g95_original_end)

    j95 = bytearray()
    j95 += J95_HEADER.pack(b"J95:", J95_PLAN_DATA.size)
    j95 += J95_PLAN_DATA.pack(gameplan.profile_type, num_custom, num_stock, num_special)

    # Write S98 chunk (header + declared payload only).
    s98_start = g95_original_end + J95_HEADER.size + j95_size
    _, s98_size = S98_HEADER.unpack_from(buffer, s98_start)
    s98 = buffer[s98_start:s98_start + S98_HEADER.size + s98_size]

    output = bytes(g95 + j95 + s98)

    # Pad to correct parity: offense = even, defense = odd.
    needs_odd = gameplan.profile_type == GamePlan.PROFILE_DEFENSE
    if len(output) % 2 != needs_odd:
        output += b"\x00"

    path.write_bytes(output)
