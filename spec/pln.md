# PNFL `.pln` File Format (Little-Endian)

**Status:** Draft → Stable  
**Owner:** PNFL Gameplan Library  
**Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. Container Overview

A `.pln` contains these chunks in order:

1. **G95** — index and play records (variable length)
2. **J95** — summary counts (fixed 7-byte payload)
3. **S98** — stock map filename (NUL-terminated)

Each chunk begins with a header: `ID (4 bytes)` + `size (4 bytes)`.  
`size` is the payload length **excluding** the 8 bytes of `ID+size`.

---

## 2. Chunk: G95 — Index + Play Records

### 2.1 Header (12 bytes total)

| Offset | Type    | Name   | Description                                         |
| -----: | :------ | :----- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID     | "G95:"                                              |
| 0x0004 | u32     | size   | Payload size in bytes (everything after this field) |
| 0x0008 | u8[4]   | u0..u3 | Always 00 01 02 03 (fixed; purpose unknown)         |

**Notes**

- Total G95 chunk length = 8 + size.
- Fields u0..u3 are constant 00 01 02 03 in all observed files and their purpose is unknown.

### 2.2 Offsets Table (fixed 168 bytes)

- Exactly **84** entries.
- Each entry is a **u16** (little-endian) value pointing to a play record.
- Offsets are **relative to the end of the G95 header** (byte 0x0C).
- A value of **0x0000** means _unused slot_.

| Field       | Value / Rule                                               |
| :---------- | :--------------------------------------------------------- |
| Count       | 84                                                         |
| Entry type  | u16 (little-endian)                                        |
| Total size  | 84 × 2 = **168 bytes**                                     |
| Offset base | End of G95 header (byte offset 0x0C)                       |
| Validation  | Each offset must point within the G95 chunk payload range. |

### 2.3 Play Record (variable size)

| Offset | Type | Name             | Description                                    |
| -----: | :--- | :--------------- | :--------------------------------------------- |
|   0x00 | u8   | stock_flag       | 0 = custom play, 1 = stock play                |
|   0x01 | u8   | play_category    | Play category code                             |
|   0x02 | u8   | special_category | Special-teams play category code               |
|   0x03 | u8   | user_category    | User category code                             |
|   0x04 | cstr | filename         | Filename; Present only if stock_flag = 0       |
|      — | cstr | play_name        | Play name; Present only if stock_flag = 1      |
|      — | u32  | offset           | Unknown offset; Present only if stock_flag = 1 |
|      — | u32  | size             | Unknown size; Present only if stock_flag = 1   |

**Conditional fields**

- If `stock_flag = 0` (**custom play**):  
  `filename` contains the custom play’s file name.  
  `offset` and `size` fields are omitted entirely (record ends after `play_name`).
- If `stock_flag = 1` (**stock play**):  
  `play_name`, `offset`, and `size` are present and valid.  
  `filename` is omitted entirely.

**Notes**

- `cstr` = sequence of ASCII bytes ending with `0x00`.
- Decode as ASCII with `errors="replace"`.
- Encode as ASCII on write; reject or replace unmappable characters.

---

## 3. Chunk: J95 — Summary / Counts

### 3.1 Header (8 bytes)

| Offset | Type    | Name | Description                                 |
| -----: | :------ | :--- | :------------------------------------------ |
| 0x0000 | char[4] | ID   | "J95:"                                      |
| 0x0004 | u32     | size | Payload size (everything after this field); |

### 3.2 Payload (7 bytes)

| Offset | Type | Name            | Description              |
| -----: | :--- | :-------------- | :----------------------- |
|     +0 | u8   | profile_type    | 0 = DEFENSE, 1 = OFFENSE |
|     +1 | u16  | numCustomPlays  | Count of custom plays    |
|     +3 | u16  | numStockPlays   | Count of stock plays     |
|     +5 | u16  | numSpecialPlays | Count of special plays   |

- Total payload size: 7 bytes.

---

## 4. Chunk: S98 — Stock Map Filename

### 4.1 Header (8 bytes)

| Offset | Type    | Name | Description                                         |
| -----: | :------ | :--- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID   | "S98:"                                              |
| 0x0004 | u32     | size | Payload size in bytes (everything after this field) |

### 4.2 Payload

- Always ASCII "STOCK98.MAP" followed by a single NUL (0x00).
- Total payload size: 12 bytes.

---

## 5. Reader Contract

- API:
  - `iter_pln(path)` and `iter_pln_stream(f)` return `Iterator[PlayRecord]`.
- Behavior:
  - Read G95 header → read 84 offsets → for each non-zero offset: `seek(offset)` and parse one record.
  - J95/S98 may be read for metadata; not required for play listing.
- Decoding: `ASCII` with replacement.
- Preservation: do not reinterpret or modify `u0..u3`.
- Errors:
  - `ValueError` for structural issues (bad ID, bad size, out-of-range offset).
  - `EOFError` for mid-record truncation (e.g., missing NUL terminator in `cstr`).

---

## 6. Writer Contract

- Input: iterable of `PlayRecord` objects.
- Steps:
  - Write G95 header; set `u0..u3` to their fixed values as defined in the specification.
  - Emit 84-entry offsets table; unused slots = `0x0000`.
  - Write offsets relative to the end of the G95 header (byte offset 0x0C).
  - Write each play record at the offset specified in the offsets table.
  - Encode strings `ASCII`; custom plays omit play_name, offset, and size; stock plays omit filename.
  - J95 counts are recomputed from G95 records, except when performing round-trip test.
  - S98 payload is constant: ASCII "STOCK98.MAP" followed by 0x00 terminator.
  - Atomic write: temp file + `os.replace`.

---

## 7. Validation & Test Vectors

- Empty index: all 84 offsets = 0; J95 = zeros; S98 present.
- Sparse index: offsets at 0, 2, 83; others zero.
- Strings: 'cstr' NUL-terminated; ASCII encoding; replace or reject non-ASCII bytes.
- Corruption: wrong ID; truncated offsets table; out-of-range offset; missing NUL in 'cstr'.

---

## 8. Open Questions
