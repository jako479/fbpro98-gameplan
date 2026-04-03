# `.pln` File Format (Little-Endian)

**Status:** Stable
**Owner:** PNFL Gameplan Library
**Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. Container Overview

A `.pln` contains these chunks in order:

1. **G95** — index and play records (variable length)
2. **J95** — summary counts (fixed 7-byte payload)
3. **S98** — stock map filename (NUL-terminated)

Each chunk begins with a header: `ID (4 bytes)` + `size (4 bytes)`.
`size` is the payload length excluding the 8 bytes of `ID+size`.

---

## 2. Chunk: G95 — Index + Play Records

### 2.1 Header (12 bytes)

| Offset | Type    | Name      | Description                                         |
| -----: | :------ | :-------- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID        | `"G95:"`                                            |
| 0x0004 | u32     | size      | Payload size in bytes (everything after this field)  |
| 0x0008 | u8[4]   | audible   | Audible play indices; always `00 01 02 03` in PNFL  |

**Notes**

- Total G95 chunk length = `8 + size`.
- The `audible` bytes represent audible play slot indices. For PNFL game
  plans these are always `00 01 02 03` and can be treated as constant.

### 2.2 Offsets Table (172 bytes)

Exactly **86** entries of `u16` (little-endian), each pointing to a play
record within the G95 chunk.

| Field       | Value / Rule                                               |
| :---------- | :--------------------------------------------------------- |
| Count       | 86                                                         |
| Entry type  | `u16` (little-endian)                                      |
| Total size  | `86 × 2 = 172 bytes`                                      |
| Offset base | Byte `0x0C` (end of G95 header)                           |
| Empty slot  | `0x0000`                                                   |
| Validation  | Each non-zero offset must point within the G95 payload.    |

First play record begins at byte `0xB8` (184 = 12 header + 172 offsets).

#### Slot Layout

| Slots | Count | Purpose             | Notes                                    |
| :---- | ----: | :------------------ | :--------------------------------------- |
| 0–63  |    64 | Normal plays        | `special_category = 0`                   |
| 64–83 |    20 | Special-teams plays | Alternating non-stock / stock (see below) |
| 84–85 |     2 | Clock plays         | Offense only                             |

**Special-teams slot order (64–83):**
Slots are organized by `special_category` (1–10), alternating between the
non-stock and stock version of each:

| Slots | special_category | Version   |
| :---- | ---------------: | :-------- |
| 64–65 |                1 | non-stock, stock |
| 66–67 |                2 | non-stock, stock |
| 68–69 |                3 | non-stock, stock |
| 70–71 |                4 | non-stock, stock |
| 72–73 |                5 | non-stock, stock |
| 74–75 |                6 | non-stock, stock |
| 76–77 |                7 | non-stock, stock |
| 78–79 |                8 | non-stock, stock |
| 80–81 |                9 | non-stock, stock |
| 82–83 |               10 | non-stock, stock |

All special-teams plays have `play_category = 1` and `user_category = 1`.

**Clock plays (84–85):**
Present only in offensive game plans. The writer preserves their original
values from the source file.

### 2.3 Play Record (variable size)

| Offset | Type    | Name             | Description                                      |
| -----: | :------ | :--------------- | :----------------------------------------------- |
|   0x00 | u8      | stock_flag       | `0` = custom play, `1` = stock play              |
|   0x01 | u8      | play_category    | Play category code                               |
|   0x02 | u8      | special_category | Special-teams category (`0` for normal plays)    |
|   0x03 | u8      | user_category    | User category code                               |

**Conditional fields (after the 4-byte header):**

If `stock_flag = 0` (custom play):

| Offset | Type | Name     | Description                          |
| -----: | :--- | :------- | :----------------------------------- |
|   0x04 | cstr | filename | NUL-terminated ASCII play file path  |

If `stock_flag = 1` (stock play):

| Offset | Type    | Name       | Description                              |
| -----: | :------ | :--------- | :--------------------------------------- |
|   0x04 | char[8] | play_name  | Fixed 8-byte ASCII name (NUL-padded)    |
|   0x0C | u32     | offset     | Opaque; unrelated to the game plan file  |
|   0x10 | u16     | size       | Opaque; unrelated to the game plan file  |

**Notes**

- `cstr` = sequence of ASCII bytes ending with `0x00`.
- Decode as ASCII with `errors="replace"`.
- Encode as ASCII on write; reject or replace unmappable characters.
- Stock play `offset` and `size` are carried through unchanged on
  round-trip; their meaning is external to the `.pln` format.

---

## 3. Chunk: J95 — Summary Counts

### 3.1 Header (8 bytes)

| Offset | Type    | Name | Description                                |
| -----: | :------ | :--- | :----------------------------------------- |
| 0x0000 | char[4] | ID   | `"J95:"`                                   |
| 0x0004 | u32     | size | Payload size (always `7`)                  |

### 3.2 Payload (7 bytes)

| Offset | Type | Name             | Description                        |
| -----: | :--- | :--------------- | :--------------------------------- |
|     +0 | u8   | profile_type     | `0` = DEFENSE, `1` = OFFENSE       |
|     +1 | u16  | num_custom_plays | Count of custom (non-stock) plays  |
|     +3 | u16  | num_stock_plays  | Count of stock plays               |
|     +5 | u16  | num_special_plays| Count of special-teams plays       |

These counts must be recomputed from the G95 play records when writing.

---

## 4. Chunk: S98 — Stock Map Filename

### 4.1 Header (8 bytes)

| Offset | Type    | Name | Description                                         |
| -----: | :------ | :--- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID   | `"S98:"`                                            |
| 0x0004 | u32     | size | Payload size in bytes (everything after this field)  |

### 4.2 Payload

ASCII `"STOCK98.MAP"` followed by a single NUL (`0x00`).
Total payload size: 12 bytes.

---

## 5. Reader Contract

- **API:** `read_gameplan(path)` returns a parsed `Gameplan`.
- **Behavior:**
  - Read G95 header (including audible bytes), read 86 offsets, then parse
    one record for each non-zero offset.
  - Classify plays by slot range: normal (0–63), special (64–83),
    clock (84–85).
  - J95 is read for `profile_type`; S98 may be read for metadata.
- **Decoding:** ASCII with replacement.
- **Preservation:** Preserve `audible` bytes as read; do not reinterpret.
- **Errors:** Raise `ValueError`-style exceptions for structural issues
  (bad ID, bad size, out-of-range offset, truncated records).

---

## 6. Writer Contract

- **Input:** Iterable of play records.
- **Steps:**
  1. Write G95 header with preserved `audible` bytes.
  2. Emit the 86-entry offsets table (`0x0000` for unused slots).
  3. Write offsets relative to byte `0x0C`.
  4. Write each play record at the offset specified in the table.
  5. Encode strings as ASCII.
  6. Custom plays: write 4-byte header + NUL-terminated filename.
  7. Stock plays: write 4-byte header + 8-byte name + offset + size.
  8. Recompute all three J95 counts from G95 records.
  9. Write constant S98 payload `"STOCK98.MAP\x00"`.
  10. Use atomic write semantics (`temp file + os.replace`).

---

## 7. Validation & Test Vectors

- Empty index: all 86 offsets are zero; J95 counts are zero; S98 is present.
- Sparse index: offsets at slots 0, 2, and 83; others zero.
- Strings: `cstr` is NUL-terminated ASCII.
- Corruption cases: wrong ID, truncated offsets table, out-of-range
  offset, missing NUL in `cstr`.
