# FLY-IN TEST REPORT

==================
Date: 2026-09-11
Python / uv version: Python 3.11.15 (.venv), uv 0.11.16

S1 Setup:            PASS
   - `make install` completed successfully
   - `uv run python -c "import src; print('IMPORT_OK')"` printed IMPORT_OK

S2 Lint:             flake8+mypy PASS   strict PASS
   - Fixed: flake8 was not actually reading the `[tool.flake8]` block in
     pyproject.toml (flake8 core does not support pyproject.toml without the
     `Flake8-pyproject` plugin), so it silently fell back to the 79-char
     default and `make lint` failed outright on 5 lines. Added `.flake8`
     with `max-line-length = 100` so the documented policy is actually
     enforced.
   - Fixed: `make lint` and `make test` both failed unconditionally before
     this pass because `tests/` did not exist yet (flake8: `E902
     FileNotFoundError`; pytest: `file or directory not found: tests/`).
     A full `tests/` suite (37 tests) now exists; both commands pass clean.

S3 Provided maps:    ALL PASS
   - easy_01.map:   EXIT=0, 4 turns
   - easy_02.map:   EXIT=0, 7 turns
   - easy_03.map:   EXIT=0, 5 turns
   - medium_01.map: EXIT=0, 8 turns
   - medium_02.map: EXIT=0, 4 turns
   - medium_03.map: EXIT=0, 7 turns
   - hard_01.map:   EXIT=0, 17 turns (turn schedule changed slightly after
     the S5 bug fix below; total turn count unchanged, still well under
     the <=30 target)
   - hard_02.map:   EXIT=0, 14 turns
   - visual mode (easy_01.map --visual): EXIT=0

S4 Parser errors:
   4a no_drones:     EXIT=2 (parse error: Missing nb_drones declaration)
   4b no_start:      EXIT=2 (parse error: Missing start_hub declaration)
   4c no_end:        EXIT=2 (parse error: Missing end_hub declaration)
   4d dup_zone:      EXIT=2 (parse error: Duplicate zone name)
   4e dup_conn:      EXIT=2 (parse error: Duplicate connection)
   4f bad_type:      EXIT=2 (parse error: Invalid zone type)
   4g undef_zone:    EXIT=2 (parse error: Connection references unknown zone)
   4h zero_cap:      EXIT=2 (parse error: max_drones must be a positive integer)
   4i garbage:       EXIT=2 (parse error: Unrecognised line)
   4j not_found:     EXIT=1
   4k nopath:        EXIT=3 (pathfinding error: No path from 'a' to 'b')

S5 Rule validation:
   - line (single drone, 3-hop):        3 turns.      PASS
   - corridor (2 drones, capacity-1):   3 turns, no simultaneous
     occupancy of the shared zone.      PASS
   - fork (2 drones, disjoint paths):   2 turns (fork < corridor).  PASS
     -> confirms the scheduler actually distributes drones across
        disjoint paths rather than serializing them onto one.
   - restricted (1 drone, 2-turn zone): 3 turns, connection token
     (`D1-<from>-<to>`) appears on the departure turn, zone token on
     the arrival turn.                 PASS

   BUG FOUND AND FIXED: a restricted zone's capacity was only reserved
   when a drone *arrived* (2 turns after departing), not when it
   departed. Two drones routed toward the same capacity-1 restricted
   zone could therefore both depart on the same turn and both land on
   it together one turn later, exceeding `max_drones`. Reproduced with:

       nb_drones: 2
       start_hub: a 0 0 / end_hub: z 5 0
       hub: c 2 0 [zone=restricted max_drones=1]
       hub: p1 1 0 / hub: p2 1 1 / hub: q 3 0
       connection: a-p1, a-p2, p1-c, p2-c, c-q, q-z

   Before the fix, turn 3 showed `D1-c D2-c` simultaneously (capacity
   violation). Fixed in `src/simulation.py::SimulationEngine.step` by
   reserving the destination zone's occupancy slot the instant a drone
   becomes IN_FLIGHT (departure), not on arrival; this also fixed a
   latent double-decrement of the origin zone's occupancy. Covered by
   `tests/test_simulation.py::TestRestrictedZoneTiming::
   test_restricted_zone_capacity_is_reserved_on_departure`. One of the
   provided maps (hard_01.map) actually exercised this path — its turn
   schedule changed after the fix, though its total turn count did not.

S6 Determinism:      YES (3 runs equal)
   - All 3 runs of medium_01.map showed "Total turns: 8"

S7 Stress 50 drones: EXIT=0, time-ok? YES (73 turns, well under the 60s
   timeout, no traceback)

S8 Validator: automated pytest assertions (see `tests/test_simulation.py`)
   replace the standalone `/tmp/validate_flyin.py` script from
   DEBUG_TEST_PLAN.md — same checks (adjacency/capacity), but run on every
   `make test` instead of ad hoc.

OVERALL: PASS (all of S1, S2, S3, S4, S5, S6, S7 pass; S5's bug was found,
fixed, and regression-tested rather than glossed over).

Fixes applied this pass:
1. `src/simulation.py`: restricted-zone destination capacity now reserved
   on departure, not arrival (correctness fix, see S5 above).
2. Added `.flake8` so the project's documented 100-char line-length policy
   is actually enforced by `flake8` (it wasn't, silently).
3. Added `tests/` (37 pytest tests) so `make lint` and `make test` — both
   mandatory Makefile targets — actually run instead of erroring out.
4. Refactored `src/parser.py`, `src/pathfinding.py`, and `src/__main__.py`
   from free functions into classes (`MapParser`, `PathFinder`,
   `FlyInApplication`, `SimulationReport`) per the subject's "must be
   completely object-oriented" constraint.
5. README: fixed the required first line to use Markdown italics instead
   of an `<i>` HTML tag, added an Object-Oriented Architecture section and
   a Visual Representation section, and brought the Testing Strategy /
   AI Usage sections in line with what's actually in the repo.
