from __future__ import annotations

from os import PathLike
from pathlib import Path

from fbpro98_gameplan.pln.model import (
    CustomPlay,
    GamePlan,
    Play,
    ProfileType,
    StockPlay,
)
from fbpro98_gameplan.pln.schema import (
    G95_AUDIBLE,
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_STOCK_PLAY_BODY,
    ID_G95,
    ID_J95,
    ID_S98,
    J95_HEADER,
    J95_PLAN_DATA,
    S98_HEADER,
)

StrPath = str | PathLike[str]


def write_gameplan(gameplan: GamePlan, path: StrPath) -> None:
    """Serialize a `GamePlan` and write it to a `.pln` file."""
    Path(path).write_bytes(build_gameplan_bytes(gameplan))


def build_gameplan_bytes(gameplan: GamePlan) -> bytes:
    """Serialize a `GamePlan` to `.pln` file bytes."""
    output = _build_g95(gameplan) + _build_j95(gameplan) + _build_s98(gameplan)
    needs_odd = gameplan.profile_type == ProfileType.DEFENSE
    if len(output) % 2 != needs_odd:
        output += b"\x00"
    return output


def _build_g95(gameplan: GamePlan) -> bytes:
    all_plays: list[Play | None] = [
        *gameplan.normal_plays,
        *gameplan.special_plays,
        *gameplan.clock_plays,
    ]
    offsets_table_start = G95_HEADER.size + G95_AUDIBLE.size
    records_base = offsets_table_start + G95_OFFSETS_TABLE.size

    offsets = [0] * GamePlan.NUMBER_PLAY_SLOTS
    records = bytearray()
    for slot, play in enumerate(all_plays):
        if play is None:
            continue
        offsets[slot] = records_base + len(records) - offsets_table_start
        records += _build_play(play)

    g95_payload_size = G95_AUDIBLE.size + G95_OFFSETS_TABLE.size + len(records)
    return (
        G95_HEADER.pack(ID_G95, g95_payload_size)
        + G95_AUDIBLE.pack(gameplan.audible)
        + G95_OFFSETS_TABLE.pack(*offsets)
        + bytes(records)
    )


def _build_play(play: Play) -> bytes:
    header = G95_PLAY_HEADER.pack(
        0 if isinstance(play, CustomPlay) else 1,
        play.play_category,
        play.special_category,
        play.user_category,
    )
    if isinstance(play, CustomPlay):
        return header + play.filename.encode("ascii") + b"\x00"
    name_bytes = play.play_name.encode("ascii").ljust(8, b"\x00")[:8]
    return header + G95_STOCK_PLAY_BODY.pack(name_bytes, play.map_offset, play.map_size)


def _build_j95(gameplan: GamePlan) -> bytes:
    num_custom = sum(1 for p in gameplan.normal_plays if isinstance(p, CustomPlay))
    num_stock = sum(1 for p in gameplan.normal_plays if isinstance(p, StockPlay))
    num_special = sum(1 for p in gameplan.special_plays if isinstance(p, CustomPlay))
    return J95_HEADER.pack(ID_J95, J95_PLAN_DATA.size) + J95_PLAN_DATA.pack(
        gameplan.profile_type, num_custom, num_stock, num_special
    )


def _build_s98(gameplan: GamePlan) -> bytes:
    payload = gameplan.map_filename.encode("ascii") + b"\x00"
    return S98_HEADER.pack(ID_S98, len(payload)) + payload
