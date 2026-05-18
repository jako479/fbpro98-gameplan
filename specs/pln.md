# `.pln` File Format (Little-Endian)

- **Status:** Stable
- **Owner:** PNFL Gameplan Library
- **Encoding:** Integers are little-endian; strings are ASCII unless noted.

---

## 1. Container Overview

A `.pln` contains these blocks in order:

1. **G95** — index and play records (variable length)
2. **J95** — summary counts (fixed 7-byte data)
3. **S98** — stock map filename (NUL-terminated)

Each block begins with a header: `ID (4 bytes)` + `size (4 bytes)`. `size` is the data length excluding the 8 bytes of `ID+size`.

---

## 2. Block: G95 — Index + Play Records

### 2.1 Header (12 bytes)

| Offset | Type    | Name      | Description                                         |
| -----: | :------ | :-------- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID        | `"G95:"`                                            |
| 0x0004 | u32     | size      | Data size in bytes (everything after this field) |
| 0x0008 | u8[4]   | audible   | Audible play indices; always `00 01 02 03`          |

Total G95 block length = `8 + size`. The reader rejects any `audible` ≠ `00 01 02 03`.

### 2.2 Offsets Table (172 bytes)

86 × `u16` little-endian, each pointing to a play record within the G95 block. Offset base is byte `0x0C` (end of G95 header); `0x0000` = empty slot. First play record begins at byte `0xB8` (12 header + 172 offsets).

#### Slot Layout

| Slots | Count | Purpose             | Notes                                     |
| :---- | ----: | :------------------ | :---------------------------------------- |
| 0–63  |    64 | Normal plays        | `special_category = 0`                    |
| 64–83 |    20 | Special-teams plays | Alternating non-stock / stock (see below) |
| 84–85 |     2 | Clock plays         | Offense only                              |

Special-teams slots (64–83) are organized by `special_category` (`0x01`–`0x0A`), alternating non-stock then stock for each:

| Slots | special_category | Offense Name   | Defense Name           | Version          |
| :---- | :--------------- | :------------- | :--------------------- | :--------------- |
| 64–65 | `0x01`           | FG/PAT         | FG/PAT Defense         | non-stock, stock |
| 66–67 | `0x02`           | Kickoff        | Kick Return            | non-stock, stock |
| 68–69 | `0x03`           | Punt           | Punt Return            | non-stock, stock |
| 70–71 | `0x04`           | Onside Kick    | Onside Return          | non-stock, stock |
| 72–73 | `0x05`           | Fake FG Run    | Fake FG Run Defense    | non-stock, stock |
| 74–75 | `0x06`           | Fake FG Pass   | Fake FG Pass Defense   | non-stock, stock |
| 76–77 | `0x07`           | Fake Punt Run  | Fake Punt Run Defense  | non-stock, stock |
| 78–79 | `0x08`           | Fake Punt Pass | Fake Punt Pass Defense | non-stock, stock |
| 80–81 | `0x09`           | Free Kick      | Free Kick Return       | non-stock, stock |
| 82–83 | `0x0A`           | Squib Kick     | Squib Return           | non-stock, stock |

All special-teams plays have `play_category` and `user_category` set per profile: `1` in offensive game plans, `0` in defensive game plans.

Clock plays (slots 84–85) are present only in offensive game plans; defensive game plans leave these offsets as `0x0000`.

### 2.3 Play Record (variable size)

| Offset | Type | Name             | Description                                                              |
| -----: | :--- | :--------------- | :----------------------------------------------------------------------- |
|   0x00 | u8   | stock_flag       | `0` = custom play, `1` = stock play                                      |
|   0x01 | u8   | play_category    | Play attribute; value semantics owned by the `.ply` format               |
|   0x02 | u8   | special_category | Play attribute; `0x00` = normal play, `0x01`–`0x0A` = special-teams (see section 2.2) |
|   0x03 | u8   | user_category    | Play attribute; value semantics owned by the `.ply` format               |

Trailing fields after the 4-byte header depend on `stock_flag`:

If `stock_flag = 0` (custom play):

| Offset | Type | Name     | Description                                    |
| -----: | :--- | :------- | :--------------------------------------------- |
|   0x04 | cstr | filename | NUL-terminated ASCII play file path (`cstr` = ASCII bytes ending in `0x00`) |

If `stock_flag = 1` (stock play):

| Offset | Type    | Name       | Description                          |
| -----: | :------ | :--------- | :----------------------------------- |
|   0x04 | char[8] | play_name  | Fixed 8-byte ASCII name (NUL-padded) |
|   0x0C | u32     | map_offset | Opaque pointer into `STOCK98.MAP`    |
|   0x10 | u16     | map_size   | Opaque size into `STOCK98.MAP`       |

`map_offset` / `map_size` reference the external `STOCK98.MAP` file; the gameplan library carries them through unchanged on round-trip.

---

## 3. Block: J95 — Summary Counts

### 3.1 Header (8 bytes)

| Offset | Type    | Name | Description               |
| -----: | :------ | :--- | :------------------------ |
| 0x0000 | char[4] | ID   | `"J95:"`                  |
| 0x0004 | u32     | size | Data size (always `7`) |

### 3.2 Data (7 bytes)

| Offset | Type | Name              | Description                       |
| -----: | :--- | :---------------- | :-------------------------------- |
|     +0 | u8   | profile_type      | `0` = DEFENSE, `1` = OFFENSE      |
|     +1 | u16  | num_custom_plays  | Count of custom (non-stock) plays |
|     +3 | u16  | num_stock_plays   | Count of stock plays              |
|     +5 | u16  | num_special_plays | Count of special-teams plays      |

These counts must be recomputed from the G95 play records when writing.

---

## 4. Block: S98 — Stock Map Filename

### 4.1 Header (8 bytes)

| Offset | Type    | Name | Description                                         |
| -----: | :------ | :--- | :-------------------------------------------------- |
| 0x0000 | char[4] | ID   | `"S98:"`                                            |
| 0x0004 | u32     | size | Data size in bytes (everything after this field) |

### 4.2 Data

ASCII `"STOCK98.MAP"` followed by a single NUL (`0x00`). Total data size: 12 bytes.

---

## 5. File Size Parity

Total file size: **even** for offense, **odd** for defense. FbPro98's file-open dialog filters by parity. Writer pads defense files with a trailing `\x00` when needed.

---

## 6. Reader Validation

Reader raises `InvalidGamePlanError` for:

- Bad block ID, size, or offset
- Truncated play record
- Missing NUL on custom play filename
- `stock_flag ∉ {0, 1}`
- `profile_type ∉ {0, 1}`
- `audible` bytes ≠ `00 01 02 03`
- J95 counts don't match parsed records
- S98 data ≠ `"STOCK98.MAP\x00"`
- File-size parity wrong for profile type

---

## 7. Writer Contract

Emit play records in slot order 0–85, recompute J95 counts, pad parity per section 5. Round-trip identity required: `write_gameplan(read_gameplan(p), q)` produces bytes identical to `p`.
