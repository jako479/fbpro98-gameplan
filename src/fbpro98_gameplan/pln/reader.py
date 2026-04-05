from __future__ import annotations

from os import PathLike
from pathlib import Path

from .model import GamePlanPlay
from .schema import (
    G95_HEADER,
    G95_OFFSETS_TABLE,
    G95_PLAY_HEADER,
    G95_PLAY_STOCK_TAIL,
    ID_G95,
    ID_J95,
    J95_HEADER,
    J95_PLAN_DATA,
)

StrPath = str | PathLike[str]


class InvalidGamePlanError(ValueError):
    """Raised when a `.pln` file is structurally invalid."""


class GamePlan:
    NUMBER_NORMAL_PLAYS = 64
    NUMBER_SPECIAL_SLOTS = 20  # 10 special-teams categories x 2 (non-stock + stock)
    NUMBER_CLOCK_SLOTS = 2     # Offense only
    NUMBER_PLAY_SLOTS = NUMBER_NORMAL_PLAYS + NUMBER_SPECIAL_SLOTS + NUMBER_CLOCK_SLOTS  # 86
    PROFILE_DEFENSE = 0
    PROFILE_OFFENSE = 1
    G95_HEADER_SIZE = G95_HEADER.size
    G95_OFFSETS_TABLE_SIZE = G95_OFFSETS_TABLE.size

    def __init__(
        self,
        filename: StrPath,
        normal_plays: dict[str, GamePlanPlay],
        special_plays: dict[str, GamePlanPlay],
        clock_plays: dict[str, GamePlanPlay],
        plays_by_slot: dict[int, GamePlanPlay],
        g95_size: int,
        audible: bytes,
        profile_type: int,
    ):
        self.filename = str(filename)
        self.path = Path(filename)
        self.normal_plays = normal_plays
        self.special_plays = special_plays
        self.clock_plays = clock_plays
        self.plays_by_slot = plays_by_slot
        self.g95_size = g95_size
        self.audible = audible
        self.profile_type = profile_type

    @classmethod
    def from_file(cls, filename: StrPath) -> GamePlan:
        """Read and parse a .pln file."""
        path = Path(filename)
        return cls.from_buffer(path.read_bytes(), filename)

    @classmethod
    def from_buffer(cls, buffer: bytes, filename: StrPath = "<buffer>") -> GamePlan:
        """Parse a .pln from raw bytes. Separates I/O from parsing."""
        path = Path(filename)
        minimum_size = cls.G95_HEADER_SIZE + cls.G95_OFFSETS_TABLE_SIZE
        if len(buffer) < minimum_size:
            raise InvalidGamePlanError(
                f"File too small to contain PLN header and offsets table in {path}"
            )

        chunk_id, g95_size, audible = G95_HEADER.unpack_from(buffer, 0)
        chunk_id_str = chunk_id.decode("ASCII", errors="replace")
        if chunk_id != ID_G95:
            raise InvalidGamePlanError(f"Invalid header '{chunk_id_str}' at 0x0 in {path}")

        g95_end = 8 + g95_size
        if g95_end > len(buffer):
            raise InvalidGamePlanError(f"G95 chunk extends past end of file in {path}")

        offsets = G95_OFFSETS_TABLE.unpack_from(buffer, cls.G95_HEADER_SIZE)
        records_start = cls.G95_HEADER_SIZE + cls.G95_OFFSETS_TABLE_SIZE
        record_offsets: list[tuple[int, int]] = []
        for slot, relative_offset in enumerate(offsets):
            if relative_offset == 0:
                continue
            record_offset = cls.G95_HEADER_SIZE + relative_offset
            if record_offset < records_start or record_offset >= g95_end:
                raise InvalidGamePlanError(
                    f"Play offset {relative_offset:#x} for slot {slot} is out of range in {path}"
                )
            record_offsets.append((slot, record_offset))

        normal_plays: dict[str, GamePlanPlay] = {}
        special_plays: dict[str, GamePlanPlay] = {}
        clock_plays: dict[str, GamePlanPlay] = {}
        plays_by_slot: dict[int, GamePlanPlay] = {}

        for index, (slot, record_offset) in enumerate(record_offsets):
            if index + 1 < len(record_offsets):
                record_end = record_offsets[index + 1][1]
            else:
                record_end = g95_end

            play = cls._parse_play(buffer, record_offset, record_end, slot, path)
            plays_by_slot[slot] = play
            if slot < cls.NUMBER_NORMAL_PLAYS:
                normal_plays[play.name] = play
            elif slot < cls.NUMBER_NORMAL_PLAYS + cls.NUMBER_SPECIAL_SLOTS:
                special_plays[play.name] = play
            else:
                clock_plays[play.name] = play

        profile_type = cls._parse_j95(buffer, g95_end)

        return cls(
            filename, normal_plays, special_plays, clock_plays,
            plays_by_slot, g95_size, audible, profile_type,
        )

    @property
    def is_offense(self) -> bool:
        return self.profile_type == self.PROFILE_OFFENSE

    @property
    def is_defense(self) -> bool:
        return self.profile_type == self.PROFILE_DEFENSE

    @staticmethod
    def _parse_j95(buffer: bytes, g95_end: int) -> int:
        if len(buffer) < g95_end + J95_HEADER.size + J95_PLAN_DATA.size:
            return 0
        j95_id, _ = J95_HEADER.unpack_from(buffer, g95_end)
        if j95_id != ID_J95:
            return 0
        return J95_PLAN_DATA.unpack_from(buffer, g95_end + J95_HEADER.size)[0]

    @staticmethod
    def _parse_play(
        buffer: bytes, buffer_offset: int, record_end: int, slot: int, path: Path,
    ) -> GamePlanPlay:
        if buffer_offset + 4 > record_end:
            raise InvalidGamePlanError(
                f"Truncated play header at {buffer_offset:#x} in {path}"
            )

        stock_flag, play_category, special_category, user_category = G95_PLAY_HEADER.unpack_from(
            buffer, buffer_offset
        )
        buffer_offset += 4

        if stock_flag == 0:
            string_end = buffer.find(b"\x00", buffer_offset, record_end)
            if string_end == -1:
                raise InvalidGamePlanError(
                    f"Missing null terminator for play record at {buffer_offset:#x} in {path}"
                )
            filename = buffer[buffer_offset:string_end].decode("ASCII", errors="replace")
            return GamePlanPlay(
                slot=slot,
                stock_flag=stock_flag,
                play_category=play_category,
                special_category=special_category,
                user_category=user_category,
                filename=filename,
            )

        if stock_flag == 1:
            if buffer_offset + G95_PLAY_STOCK_TAIL.size > record_end:
                raise InvalidGamePlanError(
                    f"Truncated stock play record at {buffer_offset:#x} in {path}"
                )
            name_bytes, stock_data = G95_PLAY_STOCK_TAIL.unpack_from(buffer, buffer_offset)
            play_name = name_bytes.decode("ASCII", errors="replace").rstrip("\x00 ")
            return GamePlanPlay(
                slot=slot,
                stock_flag=stock_flag,
                play_category=play_category,
                special_category=special_category,
                user_category=user_category,
                play_name=play_name,
                stock_data=stock_data,
            )

        raise InvalidGamePlanError(
            f"Invalid stock flag {stock_flag:#x} at slot {slot} in {path}"
        )
