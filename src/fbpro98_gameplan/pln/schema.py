from struct import Struct

# See specs/pln.md for full .pln format documentation.

G95_HEADER = Struct("<4sI4s")
G95_OFFSETS_TABLE = Struct("<86H")
G95_PLAY_HEADER = Struct("<BBBB")
G95_PLAY_CUSTOM = Struct("<BBB")
G95_PLAY_STOCK_TAIL = Struct("<8s6s")
J95_HEADER = Struct("<4sI")
J95_PLAN_DATA = Struct("<BHHH")
S98_HEADER = Struct("<4sI")

ID_G95 = b"G95:"
ID_J95 = b"J95:"
ID_S98 = b"S98:"
