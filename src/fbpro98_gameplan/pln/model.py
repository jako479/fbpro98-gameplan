from __future__ import annotations

from dataclasses import dataclass
from pathlib import PureWindowsPath


@dataclass(frozen=True, slots=True)
class GameplanPlay:
    """A single play entry as stored in a `.pln` file."""

    slot: int
    stock_flag: int
    play_category: int
    special_category: int
    user_category: int
    filename: str | None = None
    play_name: str | None = None
    offset: int | None = None
    size: int | None = None

    @property
    def name(self) -> str:
        if self.filename:
            return PureWindowsPath(self.filename).stem
        return self.play_name or ""

    @property
    def special_flag(self) -> int:
        # `pnfl-pdbtoexcel` historically used both names for the same raw byte.
        return self.special_category

    def get_name(self) -> str:
        return self.name

    def is_custom(self) -> bool:
        return self.stock_flag == 0

    def is_stock(self) -> bool:
        return self.stock_flag == 1
