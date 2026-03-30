Put two real `.pln` files in this directory for local test runs:

- `offense.pln`
- `defense.pln`

These tests no longer build synthetic gameplan files. They parse the real files above
and derive corruption cases from those bytes for validation/error-path coverage.
