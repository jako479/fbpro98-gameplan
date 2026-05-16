# fbpro98-gameplan

Library for reading and writing Front Page Sports Football Pro '98 gameplan (`.pln`) files.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Usage

### Reading

```python
from fbpro98_gameplan import read_gameplan

plan = read_gameplan("DEN-OGP1.pln")

print(plan.profile_type, plan.is_offense)

# Three fixed-length tuples mirror the file structure:
# - normal_plays: 64 slots (None for empty)
# - special_plays: 20 slots (10 non-stock + 10 stock interleaved)
# - clock_plays: 2 slots (offense only)
for slot, play in enumerate(plan.normal_plays):
    if play is not None:
        print(slot, play.name)
```

Each filled slot is either a `CustomPlay` (a user-authored play, referenced by filename) or a `StockPlay` (a built-in play referenced into `STOCK98.MAP`). Both expose a `.name` property.

### Writing

```python
from fbpro98_gameplan import CustomPlay, read_gameplan, write_gameplan

plan = read_gameplan("DEN-OGP1.pln")

new_normals = [
    CustomPlay(
        filename=r"PNFL\Offense\PSR\AF3ArshZ.ply",
        play_category=0x9B,
        special_category=0x00,
        user_category=0xB3,
    ),
    None,  # empty slot
    # ... up to 64 entries; trailing slots auto-fill with None
]

updated = plan.with_normal_plays(new_normals)
write_gameplan(updated, "DEN-OGP1.pln")
```

`with_normal_plays` returns a new `GamePlan` with only the normal-play slots replaced; special-teams and clock plays are preserved. J95 counts and parity padding are recomputed by `write_gameplan`.

For special-teams updates, `with_custom_special_plays(plays)` places each `CustomPlay` into the slot dictated by its own `special_category` (1-10); uncovered slots are cleared, order doesn't matter, out-of-range or duplicate category raises `ValueError`. The 10 stock special-teams slots are immutable through the API.

### In-memory codec

`parse_gameplan(buffer)` and `build_gameplan_bytes(plan)` are the bytes-in / bytes-out entry points; `read_gameplan` / `write_gameplan` are thin file-I/O wrappers.

## Validation

The reader raises `InvalidGamePlanError` on any structural deviation from the `.pln` format (see [`specs/pln.md`](specs/pln.md) for the full list).

## Testing

```bash
pytest
```
