# PNFL `.pln` File Format (Little-Endian)

**Status:** Draft -> Stable
**Owner:** PNFL Gameplan Library
**Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. Container Overview

A `.pln` contains these chunks in order:

1. **G95** - index and play records (variable length)
2. **J95** - summary counts (fixed 7-byte payload)
3. **S98** - stock map filename (NUL-terminated)

Each chunk begins with a header: `ID (4 bytes)` + `size (4 bytes)`.
`size` is the payload length excluding the 8 bytes of `ID+size`.

---

## 2. Chunk: G95 - Index + Play Records

### 2.1 Header (12 bytes total)

| Offset | Type    | Name   | Description                                         |
| -----: | :------ | :----- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID     | `"G95:"`                                            |
| 0x0004 | u32     | size   | Payload size in bytes (everything after this field) |
| 0x0008 | u8[4]   | u0..u3 | Always `00 01 02 03` (fixed; purpose unknown)       |

**Notes**

- Total G95 chunk length = `8 + size`.
- Fields `u0..u3` are constant `00 01 02 03` in all observed files.

### 2.2 Offsets Table (fixed 168 bytes)

- Exactly 84 entries.
- Each entry is a `u16` little-endian value pointing to a play record.
- Offsets are relative to the end of the G95 header (byte `0x0C`).
- A value of `0x0000` means the slot is unused.

| Field       | Value / Rule                                               |
| :---------- | :--------------------------------------------------------- |
| Count       | 84                                                         |
| Entry type  | `u16` (little-endian)                                      |
| Total size  | `84 * 2 = 168 bytes`                                       |
| Offset base | End of G95 header (byte offset `0x0C`)                     |
| Validation  | Each offset must point within the G95 chunk payload range. |

### 2.3 Play Record (variable size)

| Offset | Type    | Name             | Description                                           |
| -----: | :------ | :--------------- | :---------------------------------------------------- |
|   0x00 | u8      | stock_flag       | `0` = custom play, `1` = stock play                   |
|   0x01 | u8      | play_category    | Play category code                                    |
|   0x02 | u8      | special_category | Special-teams play category code                      |
|   0x03 | u8      | user_category    | User category code                                    |
|   0x04 | cstr    | filename         | Present only if `stock_flag = 0`                      |
|      - | char[8] | play_name        | Present only if `stock_flag = 1`                      |
|      - | u8[6]   | stock_data       | Opaque trailing bytes; present only if `stock_flag = 1` |

**Conditional fields**

- If `stock_flag = 0` (custom play):
  `filename` contains the custom play file name and the record ends after its NUL terminator.
- If `stock_flag = 1` (stock play):
  `play_name` and `stock_data` are present, and `filename` is omitted.

**Notes**

- `cstr` means a sequence of ASCII bytes ending with `0x00`.
- Decode as ASCII with `errors="replace"`.
- Encode as ASCII on write; reject or replace unmappable characters.

---

## 3. Chunk: J95 - Summary / Counts

### 3.1 Header (8 bytes)

| Offset | Type    | Name | Description                                 |
| -----: | :------ | :--- | :------------------------------------------ |
| 0x0000 | char[4] | ID   | `"J95:"`                                    |
| 0x0004 | u32     | size | Payload size (everything after this field)  |

### 3.2 Payload (7 bytes)

| Offset | Type | Name            | Description              |
| -----: | :--- | :-------------- | :----------------------- |
|     +0 | u8   | profile_type    | `0` = DEFENSE, `1` = OFFENSE |
|     +1 | u16  | numCustomPlays  | Count of custom plays    |
|     +3 | u16  | numStockPlays   | Count of stock plays     |
|     +5 | u16  | numSpecialPlays | Count of special plays   |

- Total payload size: 7 bytes.

---

## 4. Chunk: S98 - Stock Map Filename

### 4.1 Header (8 bytes)

| Offset | Type    | Name | Description                                         |
| -----: | :------ | :--- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID   | `"S98:"`                                            |
| 0x0004 | u32     | size | Payload size in bytes (everything after this field) |

### 4.2 Payload

- Always ASCII `"STOCK98.MAP"` followed by a single NUL (`0x00`).
- Total payload size: 12 bytes.

---

## 5. Reader Contract

- API:
  - `read_gameplan(path)` returns a parsed `Gameplan`.
- Behavior:
  - Read G95 header, read 84 offsets, then parse one record for each non-zero offset.
  - J95 and S98 may be read later for metadata; they are not required for the current play listing API.
- Decoding:
  - Use ASCII with replacement.
- Preservation:
  - Preserve `u0..u3` as read; do not reinterpret them.
- Errors:
  - Raise `ValueError`-style exceptions for structural issues such as bad ID, bad size, out-of-range offset, or truncated records.

---

## 6. Writer Contract

- Input: iterable of play records.
- Steps:
  - Write G95 header and fixed `u0..u3` bytes.
  - Emit the 84-entry offsets table with unused slots as `0x0000`.
  - Write offsets relative to the end of the G95 header (`0x0C`).
  - Write each play record at the offset specified in the offsets table.
  - Encode strings as ASCII.
  - Custom plays omit `play_name` and `stock_data`.
  - Stock plays omit `filename`.
  - Recompute J95 counts from G95 records unless performing a strict round-trip test.
  - Write constant S98 payload `"STOCK98.MAP\x00"`.
  - Use atomic write semantics (`temp file + os.replace`).

---

## 7. Validation & Test Vectors

- Empty index: all 84 offsets are zero; J95 counts are zero; S98 is present.
- Sparse index: offsets at 0, 2, and 83; others zero.
- Strings: `cstr` is NUL-terminated ASCII.
- Corruption cases: wrong ID, truncated offsets table, out-of-range offset, missing NUL in `cstr`.

---

## 8. Open Questions

- The meaning of `stock_data`'s six bytes is still unknown.
