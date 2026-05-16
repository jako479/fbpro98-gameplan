# fbpro98-gameplan — Architecture

Library that owns the FbPro '98 `.pln` gameplan binary file format end-to-end.

For system-level context (how this library fits with `fbpro98-gameplanreader` and `fbpro98-gameplanwriter`), see [pnfl-docs/Design/gameplan-architecture.md](../pnfl-docs/Design/gameplan-architecture.md).

For the validation responsibility split across the gameplan stack, see [pnfl-docs/Design/gameplan-validation.md](../pnfl-docs/Design/gameplan-validation.md).

## Module layout

```
src/fbpro98_gameplan/
├── __init__.py    # public API re-exports
├── model.py       # GamePlan, Play (CustomPlay | StockPlay), ProfileType, invariants
├── reader.py      # parse_gameplan, read_gameplan, InvalidGamePlanError
├── writer.py      # build_gameplan_bytes, write_gameplan
└── schema.py      # struct format strings for G95/J95/S98 blocks
```

`specs/pln.hexpat` and `specs/pln.md` document the on-disk byte layout independently of this code.

## What this package does

- Parses `.pln` files into a typed in-memory model
- Validates structural correctness of the bytes (block magics, sizes, offsets, parity)
- Validates semantic correctness of the model (slot counts, profile-vs-clock-plays, special-slot type/category alignment)
- Serializes a `GamePlan` back to bytes that round-trip identically
- Exposes a frozen, type-safe model for downstream consumers

## What this package assumes

- Input files come from FbPro '98 or another producer that follows the `.pln` format
- All callers respect the immutability of `GamePlan` and use `with_normal_plays` / `with_custom_special_plays` for updates

## What this package enforces

Structural (raise `InvalidGamePlanError`):
- File ≥ minimum size; `G95:` / `J95:` / `S98:` block magics
- Block declared sizes fit within file
- Audible bytes match expected default
- Play offsets within G95 record region; play headers/bodies not truncated
- Custom play filenames null-terminated
- `stock_flag` ∈ {0, 1}; `profile_type` ∈ {0, 1}
- J95 declared counts match actual play counts
- S98 data = `STOCK98.MAP\0`
- File-size parity (offense even, defense odd)

Model (raise `ValueError` via `__post_init__`):
- Exact slot counts: 64 normal, 20 special, 2 clock
- Offense requires both clock plays; defense forbids them
- Even special-slot indices hold `CustomPlay | None`; odd hold `StockPlay | None`
- Special-slot `special_category` matches slot index
- Normal-slot plays have `special_category == 0`
- Clock slots have `special_category == 11` (spike) and `12` (kneel)
- Play `play_category` parity matches profile (offense odd, defense even)

Mutation methods (raise `ValueError`):
- `with_normal_plays` accepts ≤ 64 entries
- `with_custom_special_plays` rejects out-of-range or duplicate categories

## What this package does NOT do

- Resolve play names to play-pool records (lives in `pnfl-playpool`)
- Parse individual `.ply` play files (lives in `fbpro98-play`)
- CLI argument parsing or text I/O (lives in the reader/writer CLI projects)
- Enforce uniqueness of plays across slots — the binary format permits duplicates; a permissive reader is required for inspecting quirky files. Duplicate detection lives in `fbpro98-gameplanwriter`'s input layer.

## Testing

- `tests/test_gameplan_model.py` — `__post_init__` invariants on synthesized instances
- `tests/test_gameplan_reader.py` — real-fixture parsing + structural error paths via byte-corrupted fixture copies
- `tests/test_gameplan_writer.py` — round-trip byte equality and partial-update semantics of `with_normal_plays` / `with_custom_special_plays`

The fixture `.pln` files in `tests/data/` are game-produced — they are the authoritative ground truth for any wire-format question.
