"""Binary block schema for the FbPro98 .pln file format.

Defines the `struct.Struct` layouts and block identifiers (G95, J95, S98) shared
by the reader and writer. See specs/pln.md for full .pln format documentation.
"""

from struct import Struct

DEFAULT_AUDIBLE = b"\x00\x01\x02\x03"

G95_HEADER = Struct("<4sI")
G95_AUDIBLE = Struct("<4s")
G95_OFFSETS_TABLE = Struct("<86H")
G95_PLAY_HEADER = Struct("<BBBB")
G95_STOCK_PLAY_BODY = Struct("<8sIH")
J95_HEADER = Struct("<4sI")
J95_PLAN_DATA = Struct("<BHHH")
S98_HEADER = Struct("<4sI")
S98_EXPECTED_DATA = b"STOCK98.MAP\x00"

ID_G95 = b"G95:"
ID_J95 = b"J95:"
ID_S98 = b"S98:"
