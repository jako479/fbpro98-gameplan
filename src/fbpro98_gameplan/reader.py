"""Parse FbPro98 .pln gameplan files into GamePlan objects.

Reads the three on-disk blocks (G95 plays + offsets, J95 plan metadata, S98
stock-map filename) and validates structural invariants (offset bounds, J95
declared counts, file-size parity by profile type).
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path

from fbpro98_gameplan.model import (
    CustomPlay,
    GamePlan,
    Play,
    ProfileType,
    StockPlay,
)
from fbpro98_gameplan.schema import (
    DEFAULT_AUDIBLE,
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
    S98_EXPECTED_DATA,
    S98_HEADER,
)

StrPath = str | PathLike[str]


class InvalidGamePlanError(ValueError):
    """Raised when a `.pln` file is structurally invalid."""


def read_gameplan(path: StrPath) -> GamePlan:
    """Read and parse a .pln gameplan file from disk.

    Args:
        path: Filesystem path to the .pln file.

    Returns:
        Parsed GamePlan.

    Raises:
        InvalidGamePlanError: If the file is not a structurally valid .pln (bad
            block IDs, mismatched sizes, truncated structure, J95 counts that
            don't match the parsed plays, or wrong file-size parity for the
            profile type).
        ValueError: If the parsed data violates a GamePlan invariant in
            __post_init__ (e.g., a special slot holds a play with the wrong
            `special_category`).
        OSError: If the file cannot be opened or read (subclasses include
            FileNotFoundError, PermissionError, IsADirectoryError).
    """
    file_path = Path(path)
    return parse_gameplan(file_path.read_bytes(), file_path)


def parse_gameplan(buffer: bytes, path: StrPath = "<buffer>") -> GamePlan:
    """Parse a .pln gameplan from raw bytes.

    Args:
        buffer: Full contents of a .pln file.
        path: Path used only in error messages. Defaults to "<buffer>" when
            parsing data that did not come from disk.

    Returns:
        Parsed GamePlan.

    Raises:
        InvalidGamePlanError: If the buffer does not contain a valid G95+J95+S98
            block sequence. Triggered by wrong block IDs, mismatched sizes,
            truncated structure, J95 counts that disagree with the parsed plays,
            or wrong file-size parity for the profile type.
        ValueError: If the parsed data violates a GamePlan invariant in
            __post_init__.
    """
    file_path = Path(path)
    g95_size, audible, plays_by_slot = _parse_g95(buffer, file_path)
    g95_end = G95_HEADER.size + g95_size
    profile_type, declared_counts = _parse_j95(buffer, g95_end, file_path)
    s98_start = g95_end + J95_HEADER.size + J95_PLAN_DATA.size
    map_filename = _parse_s98(buffer, s98_start, file_path)

    _validate_j95_counts(plays_by_slot, declared_counts, file_path)
    _validate_parity(len(buffer), profile_type, file_path)

    n_normal = GamePlan.NUMBER_NORMAL_PLAYS
    n_special = GamePlan.NUMBER_SPECIAL_SLOTS
    return GamePlan(
        profile_type=profile_type,
        normal_plays=tuple(plays_by_slot[:n_normal]),
        special_plays=tuple(plays_by_slot[n_normal : n_normal + n_special]),
        clock_plays=(
            plays_by_slot[n_normal + n_special],
            plays_by_slot[n_normal + n_special + 1],
        ),
        audible=audible,
        map_filename=map_filename,
    )


def _parse_g95(buffer: bytes, path: Path) -> tuple[int, bytes, list[Play | None]]:
    offsets_table_start = G95_HEADER.size + G95_AUDIBLE.size
    records_start = offsets_table_start + G95_OFFSETS_TABLE.size
    if len(buffer) < records_start:
        raise InvalidGamePlanError(f"File too small to contain PLN header and offsets table in {path}")

    block_id, g95_size = G95_HEADER.unpack_from(buffer, 0)
    if block_id != ID_G95:
        block_id_str = block_id.decode("ASCII", errors="replace")
        raise InvalidGamePlanError(f"Invalid header '{block_id_str}' at 0x0 in {path}")

    g95_end = G95_HEADER.size + g95_size
    if g95_end > len(buffer):
        raise InvalidGamePlanError(f"G95 block extends past end of file in {path}")

    (audible,) = G95_AUDIBLE.unpack_from(buffer, G95_HEADER.size)
    if audible != DEFAULT_AUDIBLE:
        raise InvalidGamePlanError(f"Audible bytes {audible!r} != expected {DEFAULT_AUDIBLE!r} in {path}")

    offsets: tuple[int, ...] = G95_OFFSETS_TABLE.unpack_from(buffer, offsets_table_start)
    record_offsets: list[tuple[int, int]] = []
    for slot, relative_offset in enumerate(offsets):
        if relative_offset == 0:
            continue
        record_offset = offsets_table_start + relative_offset
        if record_offset < records_start or record_offset >= g95_end:
            raise InvalidGamePlanError(f"Play offset {relative_offset:#x} for slot {slot} is out of range in {path}")
        record_offsets.append((slot, record_offset))

    plays_by_slot: list[Play | None] = [None] * GamePlan.NUMBER_PLAY_SLOTS
    for index, (slot, record_offset) in enumerate(record_offsets):
        record_end = record_offsets[index + 1][1] if index + 1 < len(record_offsets) else g95_end
        plays_by_slot[slot] = _parse_play(buffer, record_offset, record_end, slot, path)

    return g95_size, audible, plays_by_slot


def _parse_play(buffer: bytes, start: int, end: int, slot: int, path: Path) -> Play:
    if start + G95_PLAY_HEADER.size > end:
        raise InvalidGamePlanError(f"Truncated play header at {start:#x} in {path}")

    stock_flag, play_category, special_category, user_category = G95_PLAY_HEADER.unpack_from(buffer, start)
    body_start = start + G95_PLAY_HEADER.size

    if stock_flag == 0:
        string_end = buffer.find(b"\x00", body_start, end)
        if string_end == -1:
            raise InvalidGamePlanError(f"Missing null terminator for play record at {body_start:#x} in {path}")
        filename = buffer[body_start:string_end].decode("ASCII", errors="replace")
        return CustomPlay(
            filename=filename,
            play_category=play_category,
            special_category=special_category,
            user_category=user_category,
        )

    if stock_flag == 1:
        if body_start + G95_STOCK_PLAY_BODY.size > end:
            raise InvalidGamePlanError(f"Truncated stock play record at {body_start:#x} in {path}")
        name_bytes, map_offset, map_size = G95_STOCK_PLAY_BODY.unpack_from(buffer, body_start)
        play_name = name_bytes.decode("ASCII", errors="replace").rstrip("\x00 ")
        return StockPlay(
            play_name=play_name,
            map_offset=map_offset,
            map_size=map_size,
            play_category=play_category,
            special_category=special_category,
            user_category=user_category,
        )

    raise InvalidGamePlanError(f"Invalid stock flag {stock_flag:#x} at slot {slot} in {path}")


def _parse_j95(buffer: bytes, g95_end: int, path: Path) -> tuple[ProfileType, tuple[int, int, int]]:
    if len(buffer) < g95_end + J95_HEADER.size + J95_PLAN_DATA.size:
        raise InvalidGamePlanError(f"File too small to contain J95 block in {path}")
    j95_id, j95_len = J95_HEADER.unpack_from(buffer, g95_end)
    if j95_id != ID_J95:
        block_id_str = j95_id.decode("ASCII", errors="replace")
        raise InvalidGamePlanError(f"Invalid header '{block_id_str}' at {g95_end:#x} in {path}")
    if j95_len != J95_PLAN_DATA.size:
        raise InvalidGamePlanError(f"J95 data size {j95_len} != expected {J95_PLAN_DATA.size} in {path}")
    profile_type, num_custom, num_stock, num_special = J95_PLAN_DATA.unpack_from(buffer, g95_end + J95_HEADER.size)
    try:
        profile = ProfileType(profile_type)
    except ValueError:
        raise InvalidGamePlanError(f"Invalid J95 profile type {profile_type} in {path}") from None
    return profile, (num_custom, num_stock, num_special)


def _parse_s98(buffer: bytes, s98_start: int, path: Path) -> str:
    if len(buffer) < s98_start + S98_HEADER.size:
        raise InvalidGamePlanError(f"File too small to contain S98 block header in {path}")
    s98_id, s98_len = S98_HEADER.unpack_from(buffer, s98_start)
    if s98_id != ID_S98:
        block_id_str = s98_id.decode("ASCII", errors="replace")
        raise InvalidGamePlanError(f"Invalid header '{block_id_str}' at {s98_start:#x} in {path}")
    if s98_len != len(S98_EXPECTED_DATA):
        raise InvalidGamePlanError(f"S98 data size {s98_len} != expected {len(S98_EXPECTED_DATA)} in {path}")
    data_start = s98_start + S98_HEADER.size
    data_end = data_start + s98_len
    if data_end > len(buffer):
        raise InvalidGamePlanError(f"S98 block data extends past end of file in {path}")
    data = buffer[data_start:data_end]
    if data != S98_EXPECTED_DATA:
        raise InvalidGamePlanError(f"S98 data {data!r} != expected {S98_EXPECTED_DATA!r} in {path}")
    return data.rstrip(b"\x00").decode("ASCII", errors="replace")


def _validate_j95_counts(
    plays_by_slot: list[Play | None],
    declared: tuple[int, int, int],
    path: Path,
) -> None:
    declared_custom, declared_stock, declared_special = declared
    n_normal = GamePlan.NUMBER_NORMAL_PLAYS
    n_special = GamePlan.NUMBER_SPECIAL_SLOTS
    actual_custom = sum(1 for p in plays_by_slot[:n_normal] if isinstance(p, CustomPlay))
    actual_stock = sum(1 for p in plays_by_slot[:n_normal] if isinstance(p, StockPlay))
    actual_special = sum(1 for p in plays_by_slot[n_normal : n_normal + n_special] if isinstance(p, CustomPlay))
    if (declared_custom, declared_stock, declared_special) != (actual_custom, actual_stock, actual_special):
        raise InvalidGamePlanError(
            f"J95 counts (custom={declared_custom}, stock={declared_stock}, "
            f"special={declared_special}) don't match parsed plays "
            f"(custom={actual_custom}, stock={actual_stock}, special={actual_special}) in {path}"
        )


def _validate_parity(buffer_len: int, profile_type: ProfileType, path: Path) -> None:
    expected_parity = 1 if profile_type == ProfileType.DEFENSE else 0
    if buffer_len % 2 != expected_parity:
        expected_word = "odd" if expected_parity else "even"
        raise InvalidGamePlanError(
            f"File size {buffer_len} has wrong parity for {profile_type.name.lower()} "
            f"profile (expected {expected_word}) in {path}"
        )
