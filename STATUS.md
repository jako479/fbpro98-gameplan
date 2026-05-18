# fbpro98-gameplan — Status

**Status: Complete**

Library for reading and writing Front Page Sports Football Pro '98 gameplan (`.pln`) files.

## Implemented

- Parses `.pln` files into a typed, frozen in-memory `GamePlan` model (normal, special-teams, and clock plays)
- Distinguishes user-authored `CustomPlay` records from built-in `StockPlay` references
- Structural validation of the binary format, raising `InvalidGamePlanError` on any deviation
- Semantic model invariants (slot counts, profile-vs-clock-plays, special-slot type/category alignment)
- Serializes a `GamePlan` back to bytes that round-trip identically, recomputing J95 counts and parity padding
- Immutable update methods `with_normal_plays` and `with_custom_special_plays`
- In-memory codec entry points (`parse_gameplan` / `build_gameplan_bytes`) and file-I/O wrappers (`read_gameplan` / `write_gameplan`)

## Remaining

- Nothing outstanding for the current scope.
