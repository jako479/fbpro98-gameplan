# fbpro98-gameplan

Library for parsing Front Page Sports Football Pro '98 gameplan (`.pln`) files.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

> **When do I need `pip install -e ".[dev]"`?**
>
> The `-e` flag installs a package in "editable" mode — Python reads directly from the
> source files instead of copying them into the venv. This matters in two cases:
>
> 1. **Within this project's own venv:** If the project has a `src/` layout and its own
>    tests import the package (e.g., `from mypackage import something`), `-e` lets the
>    tests see source changes immediately without reinstalling.
> 2. **In a consuming project's venv:** If another project depends on this package, you
>    can install it into that project's venv with `pip install -e ..\this-package`. Changes
>    to this package's source files are then picked up immediately by the consuming project.
>    Without `-e`, you'd have to re-run `pip install ..\this-package` after every change.
>
> If you're just running scripts directly (e.g., `python my_script.py`) and nothing else
> imports this project as a package, you don't need it.

## Usage

Current public API:

```python
from fbpro98_gameplan import read_gameplan

plan = read_gameplan("DEN-OGP1.pln")

play = plan.normal_plays["SHOTGUN"]
print(play.slot)
print(play.name)
```

## Scope

Implemented:

- Parse the `G95` play table used by existing PNFL tooling.
- Expose lookups by slot and by normalized play name.
- Preserve the compatibility names `PLN`, `PlayInPlan`, and `InvalidPLNError` for `pnfl-pdbtoexcel`.
- Validate real offense and defense `.pln` fixtures in the test suite.

Deliberately not implemented:

- writing or editing `.pln` files
- broader domain abstractions beyond the current reader surface

This library is intentionally narrow. New behavior should generally be added only
when a consuming tool actually needs it, rather than growing speculative APIs here.

## Testing

```bash
.\.venv\Scripts\python -m pytest tests
.\.venv\Scripts\python -m ruff check src tests
```
