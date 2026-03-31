from __future__ import annotations

from os import PathLike

from .pln import Gameplan

StrPath = str | PathLike[str]


def read_gameplan(path: StrPath) -> Gameplan:
    """Read a Football Pro '98 gameplan (.pln) file."""
    return Gameplan(path)
