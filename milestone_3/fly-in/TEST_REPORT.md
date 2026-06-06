# FLY-IN TEST REPORT

==================
Date: 2026-06-06
Python / uv version: Python 3.14.5, uv 0.11.16

S1 Setup:            PASS
   - make install completed successfully
   - IMPORT_OK printed

S2 Lint:             flake8+mypy PASS   strict PASS
   - All E501 (line too long) violations fixed in:
     * src/__main__.py
     * src/parser.py (including function signature wrapping)
     * src/pathfinding.py
     * src/simulation.py

S3 Provided maps:    ALL PASS
   - easy_01.map: EXIT=0, 4 turns, SIM_OK
   - easy_02.map: EXIT=0, 7 turns, SIM_OK
   - easy_03.map: EXIT=0, 5 turns, SIM_OK
   - hard_01.map: EXIT=0, 17 turns, SIM_OK
   - hard_02.map: EXIT=0, 14 turns, SIM_OK
   - medium_01.map: EXIT=0, 8 turns, SIM_OK
   - medium_02.map: EXIT=0, 4 turns, SIM_OK
   - medium_03.map: EXIT=0, 7 turns, SIM_OK
   - visual mode test: EXIT=0

S4 Parser errors:
   4a no_drones:     EXIT=2 ✓
   4b no_start:      EXIT=2 ✓
   4c no_end:        EXIT=2 ✓
   4d dup_zone:      EXIT=2 ✓
   4e dup_conn:      EXIT=2 ✓
   4f bad_type:      EXIT=2 ✓ (fixed: now raises ParserError)
   4g undef_zone:    EXIT=2 ✓
   4h zero_cap:      EXIT=2 ✓ (fixed: now raises ParserError)
   4i garbage:       EXIT=2 ✓
   4j not_found:     EXIT=1 ✓
   4k nopath:        EXIT=3 ✓

S5 Rule validation:
   - line (turns=3), SIM_OK: PASS
   - corridor (turns=3), SIM_OK: PASS
   - fork (turns=2), SIM_OK: PASS
   - restricted (turns=3), SIM_OK: PASS
   - fork < corridor ? YES (2 < 3): PASS (drones distributed across paths)

S6 Determinism:      YES (3 runs equal)
   - All 3 runs showed "Total turns: 8" for medium_01.map

S7 Stress 50 drones: EXIT=0, time-ok? YES (73 turns, no timeout)

S8 Validator script: Used successfully

OVERALL: PASS

Bug fixes applied:
1. Fixed exit codes for invalid zone type (4f) and max_drones=0 (4h):
   - Changed _build_zone_metadata to raise ParserError instead of ValueError
   - Changed _build_conn_metadata to raise ParserError instead of ValueError
   - Updated call sites to pass line_no parameter

2. Fixed lint violations (E501):
   - Wrapped long function signatures across multiple lines
   - Split long conditional statements with backslash
   - Broke long string concatenations across multiple lines
