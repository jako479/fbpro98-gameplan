from struct import Struct

# PLN FILE LAYOUT
# ============================
# G95 CHUNK
#   G95_HEADER (12 bytes)
#       0x00 id      (4s) - "G95:"
#       0x04 size    (u32) - payload length (bytes after header)
#       0x08 u0..u3  (u8 x 4) - reserved; observed as 00 01 02 03
#   G95_OFFSETS_TABLE (168 bytes; 84 x u16 offsets, relative to 0x0C)
#   PLAY RECORDS (0-84 variable-length records)
#       0x00 stock_flag (u8) - 0 = custom, 1 = stock
#
#       If stock_flag == 0 (custom play):
#         0x01 play_category    (u8)
#         0x02 special_category (u8)
#         0x03 user_category    (u8)
#         0x04 filename         (cstr) - null-terminated ASCII string
#
#       If stock_flag == 1 (stock play):
#         0x01 play_category    (u8)
#         0x02 special_category (u8)
#         0x03 user_category    (u8)
#         0x04 play_name        (8s) - fixed 8-byte ASCII, not null-terminated
#         0x0C offset           (u32) - position within STOCK98.MAP
#         0x10 size             (u32) - length of play data
#
# J95 CHUNK
#   J95_HEADER (8 bytes)
#       0x00 id    (4s) - "J95:"
#       0x04 size  (u32) - payload length (bytes after header)
#   J95_PLAN_DATA (7 bytes)
#       0x00 profile_type      (u8) - 0 = DEFENSIVE, 1 = OFFENSIVE
#       0x01 num_custom_plays  (u16) - count of custom plays
#       0x03 num_stock_plays   (u16) - count of stock plays
#       0x05 num_special_plays (u16) - count of special plays
#
# S98 CHUNK
#   S98_HEADER (8 bytes)
#       0x00 id    (4s) - "S98:"
#       0x04 size  (u32) - payload length (bytes after header)

G95_HEADER = Struct("<4sIBBBB")
G95_OFFSETS_TABLE = Struct("<84H")
G95_PLAY_CUSTOM = Struct("<BBB")
G95_PLAY_STOCK = Struct("<BBB8sII")
J95_HEADER = Struct("<4sI")
J95_PLAN_DATA = Struct("<BHHH")
S98_HEADER = Struct("<4sI")

ID_G95 = b"G95:"
ID_J95 = b"J95:"
ID_S98 = b"S98:"
