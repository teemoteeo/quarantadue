# FIX PLAN — milestone_3 (codexion, fly_in, call_me_maybe)

Order by risk: **codexion** first (eval-fatal bugs), **fly_in** second (invalid simulations + crash), **call_me_maybe** last (works, compliance polish). Each phase ends with a verification gate. Estimated total: ~2–3 work days.

---

## PHASE 1 — codexion (highest risk)

### 1.1 Parser hardening (small, independent — do first)

| # | Fix | Files |
|---|-----|-------|
| 1 | Bound `nb_coders <= MAX_CODERS` (currently 300 coders → out-of-bounds writes, UB, hang) | `parser.c` |
| 2 | Overflow guard in `ft_atoi` (reject values > INT_MAX) | `parser.c` |

### 1.2 Core acquisition rewrite (fixes 4 CRITICALs together)

Single redesign, not patches. New acquisition path:

1. **Per-coder state mutex** — add `state_mutex` to `t_coder`; all reads/writes of `state` and `last_compile_start` go through it (fixes monitor data race / UB).
2. **Take-both-or-nothing** — lock both dongle mutexes in index order, check both available, take both or neither. Kills: phantom "has taken a dongle" logs, cooldown poisoning (release-without-compile path gone), take/release churn.
3. **Single-coder case** — `first == second`: take the lone dongle, log once, wait for stop flag, release, exit. Monitor declares burnout at `time_to_burnout`. (Currently a lone coder compiles with ONE dongle — instant eval fail.)
4. **Wire the scheduler** — currently FIFO/EDF heap is dead code, never called. Move wait queue into `t_dongle` (per-dongle queue; subject wording is per-dongle arbitration). Wait via `pthread_cond_timedwait` ~1 ms loop; grant only when coder is queue front AND dongle free. FIFO priority = enqueue time; EDF = `last_compile_start + time_to_burnout` (read under state mutex). Reuse existing sift functions — "must implement a priority queue" stays satisfied. Delete global `wait_queue` from `t_simulation`. Also fixes head-of-line blocking and the blind `heap_pop` race in current scheduler.c.
5. **Forbidden functions** — heap: single `malloc` sized `nb_coders` (bounded: each coder waits on one dongle at a time), drop `realloc`. Replace `die()`/`exit()` with error returns propagated to `main`. (`realloc`, `exit` are not in the allowed external functions list.)

Files: `codexion.h`, `coder.c`, `coder_utils.c`, `dongle.c`, `dongle_utils.c`, `scheduler.c`, `heap.c`, `simulation.c`, `simulation_utils.c`, `main.c`.

### 1.3 Timing + logging correctness

| # | Fix | Files |
|---|-----|-------|
| 1 | `ft_usleep`: chunked loop (≤500 µs slices) against `now_ms()` deadline, checks stop flag (single `usleep(ms*1000)` may EINVAL for ≥1 s and cannot react to stop) | `simulation.c` |
| 2 | Stop right after final compile: `break` before debug/refactor when `compiles_done >= compiles_required` (sim currently overruns by debug+refactor time) | `coder_utils.c` |
| 3 | No messages after burnout: `log_msg` checks stop flag under `log_mutex`; monitor prints burnout + sets stop flag while holding log mutex | `logger.c`, `monitor.c` |

### 1.4 Dead code purge

Delete: unused `dongle_try_acquire` copy, `dongle_try_acquire_timed` + loop, `dongle_is_available`, `scheduler_utils.c` (empty file — remove from Makefile SRCS), `BURNOUT_TOLERANCE_MS`, `state_since` field, `set_stop_and_return` (inline it). Unify three time functions into `now_ms()` + start offset.

### 1.5 README sync

Rewrite "Blocking cases handled" / "Thread Synchronization Mechanisms" sections to describe the **new actual** mechanism (per-dongle queue, cond_timedwait, state mutexes). Update architecture diagram. README currently documents EDF timeouts / cond_timedwait monitor that do not exist — defense killer.

### GATE 1 — verify

```sh
make re                                  # -Wall -Wextra -Werror clean, no relink
norminette src include                   # 0 errors
./codexion 1 410 200 100 100 2 50 fifo   # one take, burnout at ~410 ms, clean exit
./codexion 3 310 200 100 100 2 600 edf   # no phantom takes, EDF order observable
./codexion 300 500 100 100 100 1 0 fifo  # clean error message, no hang
./codexion 4 2000 200 100 100 2 0 fifo   # stops right after last compile
./codexion 5 800 200 200 200 7 0 fifo    # long run: every "is compiling" preceded by exactly
                                         # two takes; no line after "burned out" (grep script)
valgrind --tool=helgrind ./codexion 4 …  # no data races
valgrind ./codexion 4 …                  # no leaks
```

---

## PHASE 2 — fly_in

### 2.1 Crash + capacity correctness (CRITICALs)

| # | Fix | Files |
|---|-----|-------|
| 1 | Catch pydantic `ValidationError` in parser → `ParserError`; validate `nb_drones >= 1` at its line with line number (currently `nb_drones: 0` → raw traceback) | `parser.py` |
| 2 | Restricted transit: reserve destination occupancy at transit start; remove Phase-1 double departure decrement; add persistent `_inflight_links` counter so link capacity holds across the 2-turn transit (verified: two drones currently end up inside a capacity-1 restricted zone) | `simulation.py` |
| 3 | Drop start/end zone-type override, keep only the capacity exemption (fixes pathfinding-vs-engine divergence when end_hub is restricted) | `simulation.py` |

### 2.2 Parser completeness

| # | Fix |
|---|-----|
| 1 | Reject dashes in zone names: name pattern `([^\s\-]+)` in all four regexes + explicit error (currently `hub: my-zone …` accepted) |
| 2 | Reject unknown metadata keys and `=`-less tokens (whitelist per context, ParserError with line + cause; currently `[max_dornes=5]` silently ignored) |
| 3 | Duplicate-name check in `start_hub:`/`end_hub:` branches (currently only `hub:` checks) |
| 4 | Connection-references-unknown-zone error at its own line number, not post-hoc line 0 |

### 2.3 Output format (subject-literal)

- Default stdout = bare movement lines only (`D1-roof1 D2-corridorA`), skip empty turns. No `Turn N:` prefix, no `(no movement)`, no header/footer.
- Header / turn prefixes / stats → behind `--visual` (or stats to stderr).
- `--visual` mode upgrade: color movements by destination zone type, use parsed `color=` metadata, add per-turn zone-state line (closes "zone states" visual requirement). Keep default spec-compliant; document `--visual` in README.

### 2.4 Algorithm quality

| # | Fix |
|---|-----|
| 1 | Path assignment: greedy by estimated finish time (path cost + drones already queued on path) instead of blind round-robin over k paths |
| 2 | Deadlock: on stall, reroute blocked drones via existing `_find_path_avoiding_edges` with saturated edges blocked; `RuntimeError` only as last resort (subject demands strategic waiting/avoidance, not a crash) |
| 3 | `_avg_turns_per_drone`: record `delivered_turn` on `Drone`, average that; delete string-parsing reconstruction in `__main__.py` |

### 2.5 OO refactor (explicit subject constraint: "completely object-oriented")

- `MapParser` class wrapping parse state/methods (`parser.py` currently procedural).
- `PathFinder` class (holds graph; `shortest()`, `k_shortest()`); merge the two duplicate Dijkstras into one with a `blocked` param; prev-pointer path reconstruction instead of carrying full paths in the heap.
- `SimulationEngine` takes `ZoneGraph` — delete duplicated capacity/type/link dicts (two sources of truth caused the start/end divergence).
- `__main__`: thin `App` class or at minimum move cost calc to graph (reuse `MOVE_COST`).

### 2.6 Tooling + docs

| # | Fix |
|---|-----|
| 1 | Add real `.flake8` file (pyproject `[tool.flake8]` block is dead — flake8 ignores pyproject); `make lint` → `flake8 .` + subject mypy flags; remove nonexistent `tests` refs from Makefile **or** add the minimal pytest suite the README claims (preferred: add) |
| 2 | Commit `uv.lock` |
| 3 | Docstrings for all missing classes/functions (`__main__` helpers, `DroneState`/`Drone`/`TurnLog`/`SimulationEngine`/`run`, `TerminalVisualizer` + methods, graph property accessors) — PEP 257 |
| 4 | README: remove false claims (strategic delays, re-routing caching, test suite) or make them true after 2.4; document real visual features |

### GATE 2 — verify

```sh
make lint && make lint-strict            # clean, including new .flake8
python -m src /tmp/zero.map              # clean error, no traceback (nb_drones: 0)
python -m src /tmp/restr.map             # never 2 drones in a cap-1 restricted zone
python -m src /tmp/dash.map              # parse error on dashed zone name
for m in data/maps/*.map; do python -m src "$m"; done
                                         # all benchmark targets still met POST-fix
                                         # (capacity fixes may raise turn counts — retune 2.4.1 if missed)
# default output byte-diff vs subject example format (bare lines only)
```

Write a **validator script**: replays output against the map, asserts zone occupancy + link capacity every turn. Run on all maps. Key regression net for 2.1.2.

---

## PHASE 3 — call_me_maybe ✅ DONE (2026-06-10, all gate checks passed)

> Deviation from plan: 3.1.5 (`torch` move into llm_sdk) **not** applied —
> `[tool.uv.sources]` index pins only apply to direct dependencies, so
> removing torch from the root would pull the GPU wheel from PyPI for
> reviewers. Kept in root with an explanatory comment + README section.
> Addition beyond plan: repetition-triggered early force-close in
> `generate_string` (degenerate loops close immediately instead of filling
> the 64-token budget; total runtime 4m22s → 2m35s).

### 3.1 Compliance quick wins (≤1 h total)

| # | Fix | Files |
|---|-----|-------|
| 1 | CLI defaults (`data/input/functions_definition.json`, `data/input/function_calling_tests.json`, `data/output/function_calling_results.json`), drop `required=True` — subject command must work bare | `src/__main__.py` |
| 2 | Wrap model load in try/except → clear error message + nonzero exit (offline/bad model id currently tracebacks) | `src/__main__.py` |
| 3 | `debug` Makefile rule → `$(PY) -m pdb -m $(SRC) …` (keep `--debug` flag as separate `debug-trace` target) | `Makefile` |
| 4 | Translate README to English; restore exact required first line *"This project has been created as part of the 42 curriculum by tcostant."* | `README.md` |
| 5 | Move `torch` dep out of project deps into `llm_sdk/pyproject.toml` | both pyprojects |
| 6 | Delete dead `[tool.flake8]` pyproject block and dead `# noqa: BLE001` | `pyproject.toml`, `src/__main__.py` |

### 3.2 Decoder correctness

| # | Fix |
|---|-----|
| 1 | Prefix-ambiguous function names (`fn_add` vs `fn_add_numbers`): keep decoding while a longer candidate exists; stop-vs-continue decided by logits (closing-quote token vs best continuation) instead of unconditional early return |
| 2 | Terminator double-feed: number/bool decoding already consumed `,`/`}` into ids — append `", "` only after string params (currently context becomes `40,, "b":`) |
| 3 | Integer grammar: `allow_fraction=False` in `_walk_number` when `spec.type == "integer"` (currently `2.7` decoded then silently truncated to 2) |
| 4 | Replace loop-detector + 3 fallback heuristics (~100 lines: `_extract_string_fallback`, `_find_repeating_segment`, `_strip_invalid_suffix`) with forced-close: near step budget, mask to string-completing tokens only — guarantees termination by construction |
| 5 | Failure fallback: retry with bigger budget; never emit `name: ""` — emit best-logit catalog function with type-correct neutral args (empty name violates output validation rules) |

### 3.3 Performance + pydantic + style

| # | Fix |
|---|-----|
| 1 | Precompute `clean_vocab` list in `TokenizedLLM._load_vocab` — kills per-step 151k-token forbidden-char rescan in every grammar loop |
| 2 | Drop `_NumberWalk` class (return plain str like `_walk_string`); `_ValueResult` → pydantic BaseModel; extract shared literal-choice helper for boolean branch (subject: "All classes must use pydantic") |
| 3 | Docstrings → English, PEP 257 form (capitalized first line, period) |
| 4 | Typo `recent_suffices` (removed anyway by 3.2.4) |

### GATE 3 — verify

```sh
uv run python -m src                     # runs with defaults, no args
make lint && make lint-strict            # clean
make run                                 # output JSON parses, schema-valid, no empty names,
                                         # runtime < 5 min
# ad-hoc catalog with fn_add + fn_add_numbers → correct selection
# integer-param prompt with fractional temptation → integer-only decode path
HF_HUB_OFFLINE=1 uv run python -m src    # (cache moved) clean error message, no traceback
```

---

## CROSS-CUTTING (apply during every phase)

1. **README ↔ code audit**: per project, grep every README claim for a call site before commit. Delete the claim or wire the code.
2. **`edge_cases.txt` files already exist in repos** — convert into executable test scripts; run at every gate.
3. **Byte-diff outputs vs subject example blocks** wherever a format is specified (codexion log pattern, fly_in movement lines, call_me_maybe usage string).

## Commit sequence

One branch per project: `fix/codexion-core`, `fix/flyin-correctness`, `fix/cmm-compliance`. One commit per phase row group (parser bounds, acquisition rewrite, timing, dead code, docs). Gate checks green before merge to main.

---

## Severity rollup (from audit, 2026-06-10)

| Project | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| codexion | 5 | 3 | 5 | 2 |
| fly_in | 3 | 4 | 9 | 4 |
| call_me_maybe | 0 | 4 | 8 | 5 |

Key verified evidence behind the CRITICALs:

- codexion: lone coder compiles with one dongle; phantom takes + cooldown poisoning (`310 1 burned out` with 600 ms cooldown); 300 coders → silent hang (OOB/UB); FIFO/EDF scheduler entirely dead code; monitor reads coder state without synchronization.
- fly_in: `Turn 3: D1-r D2-r` — two drones inside a `max_drones=1` restricted zone; `nb_drones: 0` → raw pydantic traceback; double departure decrement corrupts occupancy.
- call_me_maybe: bare `python -m src` rejected (subject says args optional); README Italian (must be English, exact first line); model load unguarded.
