from __future__ import annotations

from os import PathLike
from pathlib import Path
from struct import Struct

from .model import GameplanPlay
from .schema import G95_HEADER, G95_OFFSETS_TABLE, ID_G95

StrPath = str | PathLike[str]
STOCK_RECORD_TAIL = Struct("<8sII")


class InvalidGameplanError(ValueError):
    """Raised when a `.pln` file is structurally invalid."""


class Gameplan:
    NUMBER_NORMAL_PLAYS = 64
    NUMBER_SPECIAL_PLAYS = 10
    NUMBER_STOCK_SPECIAL_PLAYS = 10
    NUMBER_PLAY_SLOTS = NUMBER_NORMAL_PLAYS + NUMBER_SPECIAL_PLAYS + NUMBER_STOCK_SPECIAL_PLAYS
    G95_HEADER_SIZE = G95_HEADER.size
    G95_OFFSETS_TABLE_SIZE = G95_OFFSETS_TABLE.size

    def __init__(self, filename: StrPath):
        self.filename = str(filename)
        self.path = Path(filename)
        self.normal_plays: dict[str, GameplanPlay] = {}
        self.special_plays: dict[str, GameplanPlay] = {}
        self.stock_special_plays: dict[str, GameplanPlay] = {}
        self.plays_by_slot: dict[int, GameplanPlay] = {}
        self.g95_size = 0
        self.unknown1 = 0
        self.unknown2 = 1
        self.unknown3 = 2
        self.unknown4 = 3

        buffer = self.path.read_bytes()
        self._parse(buffer)

    def _parse(self, buffer: bytes) -> None:
        minimum_size = self.G95_HEADER_SIZE + self.G95_OFFSETS_TABLE_SIZE
        if len(buffer) < minimum_size:
            raise InvalidGameplanError(
                f"File too small to contain PLN header and offsets table in {self.path}"
            )

        chunk_id, self.g95_size, self.unknown1, self.unknown2, self.unknown3, self.unknown4 = (
            G95_HEADER.unpack_from(buffer, 0)
        )
        self.id = chunk_id.decode("ASCII", errors="replace")
        if chunk_id != ID_G95:
            raise InvalidGameplanError(f"Invalid header '{self.id}' at 0x0 in {self.path}")

        g95_end = 8 + self.g95_size
        if g95_end > len(buffer):
            raise InvalidGameplanError(f"G95 chunk extends past end of file in {self.path}")

        offsets = G95_OFFSETS_TABLE.unpack_from(buffer, self.G95_HEADER_SIZE)
        records_start = self.G95_HEADER_SIZE + self.G95_OFFSETS_TABLE_SIZE
        for slot, relative_offset in enumerate(offsets):
            if relative_offset == 0:
                continue

            record_offset = self.G95_HEADER_SIZE + relative_offset
            if record_offset < records_start or record_offset >= g95_end:
                raise InvalidGameplanError(
                    f"Play offset {relative_offset:#x} for slot {slot} is out of range in {self.path}"
                )

            play = self._parse_play(buffer, record_offset, g95_end, slot)
            self.plays_by_slot[slot] = play
            self._store_play(play)

    def _parse_play(
        self, buffer: bytes, buffer_offset: int, g95_end: int, slot: int
    ) -> GameplanPlay:
        if buffer_offset + 4 > g95_end:
            raise InvalidGameplanError(
                f"Truncated play header at {buffer_offset:#x} in {self.path}"
            )

        stock_flag = buffer[buffer_offset]
        play_category = buffer[buffer_offset + 1]
        special_category = buffer[buffer_offset + 2]
        user_category = buffer[buffer_offset + 3]
        buffer_offset += 4

        if stock_flag == 0:
            filename = self._read_c_string(buffer, buffer_offset, g95_end)
            return GameplanPlay(
                slot=slot,
                stock_flag=stock_flag,
                play_category=play_category,
                special_category=special_category,
                user_category=user_category,
                filename=filename,
            )

        if stock_flag == 1:
            if buffer_offset + STOCK_RECORD_TAIL.size > g95_end:
                raise InvalidGameplanError(
                    f"Truncated stock play record at {buffer_offset:#x} in {self.path}"
                )
            name_bytes, offset, size = STOCK_RECORD_TAIL.unpack_from(buffer, buffer_offset)
            play_name = name_bytes.decode("ASCII", errors="replace").rstrip("\x00 ")
            return GameplanPlay(
                slot=slot,
                stock_flag=stock_flag,
                play_category=play_category,
                special_category=special_category,
                user_category=user_category,
                play_name=play_name,
                offset=offset,
                size=size,
            )

        raise InvalidGameplanError(
            f"Invalid stock flag {stock_flag:#x} at slot {slot} in {self.path}"
        )

    def _read_c_string(self, buffer: bytes, buffer_offset: int, g95_end: int) -> str:
        string_end = buffer.find(b"\x00", buffer_offset, g95_end)
        if string_end == -1:
            raise InvalidGameplanError(
                f"Missing null terminator for play record at {buffer_offset:#x} in {self.path}"
            )
        return buffer[buffer_offset:string_end].decode("ASCII", errors="replace")

    def _store_play(self, play: GameplanPlay) -> None:
        if play.slot < self.NUMBER_NORMAL_PLAYS:
            self.normal_plays[play.name] = play
        elif play.slot < self.NUMBER_NORMAL_PLAYS + self.NUMBER_SPECIAL_PLAYS:
            self.special_plays[play.name] = play
        else:
            self.stock_special_plays[play.name] = play


PLN = Gameplan
PlayInPlan = GameplanPlay
InvalidPLNError = InvalidGameplanError
