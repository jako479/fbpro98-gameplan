from __future__ import annotations

from os import PathLike

from .pln import GamePlan

StrPath = str | PathLike[str]


def read_gameplan(path: StrPath) -> GamePlan:
    """Read a Football Pro '98 gameplan (.pln) file."""
    return GamePlan.from_file(path)
