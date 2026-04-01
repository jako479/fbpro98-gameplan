from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .model import GameplanPlay
from .reader import Gameplan
from .schema import (
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_PLAY_STOCK_TAIL,
    ID_G95,
    J95_HEADER,
    J95_PLAN_DATA,
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

    Slots 64-83 (special and stock-special plays) are preserved unchanged.
    J95 counts are recalculated. S98 chunk is preserved.

    ``entries`` must have at most 64 items. Each item is either a
    ``NormalPlayEntry`` (custom play) or ``None`` (empty slot).
    """
    path = Path(path)
    buffer = path.read_bytes()
    gameplan = Gameplan(path)

    if len(entries) > Gameplan.NUMBER_NORMAL_PLAYS:
        raise ValueError(
            f"Expected at most {Gameplan.NUMBER_NORMAL_PLAYS} entries, got {len(entries)}"
        )

    padded = list(entries) + [None] * (Gameplan.NUMBER_NORMAL_PLAYS - len(entries))

    # Collect existing special/stock-special play records in slot order.
    preserved_plays: list[GameplanPlay] = []
    for slot in range(Gameplan.NUMBER_NORMAL_PLAYS, Gameplan.NUMBER_PLAY_SLOTS):
        play = gameplan.plays_by_slot.get(slot)
        if play is not None:
            preserved_plays.append(play)

    # Build play records blob and offsets table.
    offsets = [0] * Gameplan.NUMBER_PLAY_SLOTS
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

    # Write preserved special/stock-special play records (slots 64-83).
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
    g95_payload_size = G95_OFFSETS_TABLE.size + 4 + len(records)  # offsets + unknowns + records
    g95 = bytearray()
    g95 += G95_HEADER.pack(
        ID_G95, g95_payload_size,
        gameplan.unknown1, gameplan.unknown2, gameplan.unknown3, gameplan.unknown4,
    )
    g95 += G95_OFFSETS_TABLE.pack(*offsets)
    g95 += records

    # Recalculate J95 counts.
    num_custom = sum(1 for e in padded if e is not None)
    num_custom += sum(1 for p in preserved_plays if p.is_custom())
    num_stock = sum(1 for p in preserved_plays if p.is_stock())
    num_special = len(preserved_plays)

    # Read original J95 to get profile_type.
    g95_original_end = 8 + gameplan.g95_size
    j95_id, j95_size = J95_HEADER.unpack_from(buffer, g95_original_end)
    profile_type = J95_PLAN_DATA.unpack_from(buffer, g95_original_end + J95_HEADER.size)[0]

    j95 = bytearray()
    j95 += J95_HEADER.pack(b"J95:", J95_PLAN_DATA.size)
    j95 += J95_PLAN_DATA.pack(profile_type, num_custom, num_stock, num_special)

    # Preserve S98 chunk as-is.
    s98_start = g95_original_end + J95_HEADER.size + j95_size
    s98 = buffer[s98_start:]

    path.write_bytes(bytes(g95 + j95 + s98))
