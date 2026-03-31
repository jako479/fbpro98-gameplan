"""
fbpro98_gameplan
================

PNFL tools library for parsing Front Page Sports Football Pro '98
gameplan (.pln) files.
"""

__version__ = "0.1.0"

from .parser import read_gameplan
from .pln import (
    Gameplan,
    GameplanPlay,
    InvalidGameplanError,
    InvalidPLNError,
    PLN,
    PlayInPlan,
)

__all__ = [
    "Gameplan",
    "GameplanPlay",
    "InvalidGameplanError",
    "InvalidPLNError",
    "PLN",
    "PlayInPlan",
    "read_gameplan",
]
