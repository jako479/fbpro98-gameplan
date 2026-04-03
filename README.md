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
play = plan.normal_plays["SHOTGUN"]
print(play.slot, play.name)
print(plan.is_offense, plan.profile_type)
```
### Writing normal plays
```python
from fbpro98_gameplan import NormalPlayEntry, write_normal_plays

entries = [
    NormalPlayEntry(
        filename=r"PNFL\Offense\PSR\AF3ArshZ.ply",
        play_category=0x9B,
        special_category=0x00,
        user_category=0xB3,
    ),
    None,  # empty slot
]
write_normal_plays("DEN-OGP1.pln", entries)
```
`write_normal_plays` modifies only the 64 normal-play slots. Special-teams
plays (slots 64-83) and clock plays (slots 84-85) are preserved. J95 counts
are recalculated.
## Testing
```bash
pytest
```
