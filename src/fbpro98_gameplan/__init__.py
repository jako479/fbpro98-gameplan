"""
fbpro98_gameplan
================

Library for reading and writing Front Page Sports Football Pro '98
gameplan (.pln) files.
"""

__version__ = "0.1.0"

from .parser import read_gameplan
from .pln import (
    GamePlan,
    GamePlanPlay,
    InvalidGamePlanError,
    NormalPlayEntry,
    write_normal_plays,
)

__all__ = [
    "GamePlan",
    "GamePlanPlay",
    "InvalidGamePlanError",
    "NormalPlayEntry",
    "read_gameplan",
    "write_normal_plays",
]
