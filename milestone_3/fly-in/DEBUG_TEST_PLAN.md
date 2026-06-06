# Fly-in — Debug & Test Plan

> **Executor model: read this first.**
> You are running a fixed test script, not improvising. Follow steps **in order**.
> For every step: run the exact command, capture output, compare to the **PASS
> criteria**, and write `PASS`/`FAIL` in the report (Section 9).
> **Do NOT edit source files.** If a step fails, record it and continue.
> **Do NOT trust `edge_cases.txt`** — it is the author's claim. Re-verify every
> item mechanically. A ✅ there counts only when your command reproduces it.

Project root for all commands: the folder containing this file (`fly-in/`).
`cd` into it first.

Invocation:
```
uv run python -m src <map_file> [--visual]
```

**Exit codes are the contract** (from `src/__main__.py`) — memorise them:

| Exit | Meaning                          |
|------|----------------------------------|
| 0    | success (all drones delivered)   |
| 1    | map file not found               |
| 2    | parse error (`ParserError`)      |
| 3    | pathfinding error (`ValueError`) |
| 4    | simulation error (`RuntimeError`)|

Helper:
```bash
run() { uv run python -m src "$@"; echo "EXIT=$?"; }
```

---

## Section 1 — Setup (BLOCKING)

```bash
make install 2>&1 | tee /tmp/flyin_install.log
uv run python -c "import src; print('IMPORT_OK')"
```
PASS: `make install` finishes with no error and `IMPORT_OK` prints.
If FAIL, **STOP** — nothing else runs.

---

## Section 2 — Static analysis (style + types)

```bash
make lint 2>&1 | tee /tmp/flyin_lint.log
echo "LINT_EXIT=${PIPESTATUS[0]}"
make lint-strict 2>&1 | tee /tmp/flyin_lint_strict.log
echo "STRICT_EXIT=${PIPESTATUS[0]}"
```
PASS:
- `LINT_EXIT=0` (flake8 + mypy clean).
- `STRICT_EXIT=0` (mypy --strict clean). If strict fails but normal passes,
  record FAIL on strict only and continue.

---

## Section 3 — Happy-path runs on provided maps

The repo ships maps in `data/maps/`. Run every one; all should exit `0`.

```bash
for m in data/maps/*.map; do
  echo "=== $m ==="
  timeout 30 uv run python -m src "$m" | tee "/tmp/flyin_$(basename $m).out"
  echo "EXIT=${PIPESTATUS[0]}"
done
```
PASS per map (ALL must hold):
- `EXIT=0`.
- Output ends with a `--- Stats ---` block showing `Total turns:` ≥ 1.
- No Python traceback anywhere in the output.
- The movement lines validate under Section 8 (`SIM_OK`).

Then re-run the first easy map with `--visual` and confirm it still exits 0:
```bash
run data/maps/easy_01.map --visual >/dev/null; 
```
PASS: `EXIT=0` (visual mode must not crash).

---

## Section 4 — Parser error handling (exact exit codes)

You will CREATE small bad maps in `/tmp` and assert the exit code. Do not invent
other maps; use exactly these.

```bash
mkdir -p /tmp/flymaps

# 4a missing nb_drones  -> exit 2
cat > /tmp/flymaps/no_drones.map <<'EOF'
start_hub: a 0 0
end_hub: b 1 1
connection: a-b
EOF

# 4b missing start_hub -> exit 2
cat > /tmp/flymaps/no_start.map <<'EOF'
nb_drones: 2
end_hub: b 1 1
EOF

# 4c missing end_hub -> exit 2
cat > /tmp/flymaps/no_end.map <<'EOF'
nb_drones: 2
start_hub: a 0 0
EOF

# 4d duplicate zone name -> exit 2
cat > /tmp/flymaps/dup_zone.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
hub: a 2 2
connection: a-b
EOF

# 4e duplicate connection (a-b then b-a) -> exit 2
cat > /tmp/flymaps/dup_conn.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
connection: a-b
connection: b-a
EOF

# 4f invalid zone type -> exit 2
cat > /tmp/flymaps/bad_type.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
hub: c 2 2 [zone=magical]
connection: a-c
connection: c-b
EOF

# 4g connection to undefined zone -> exit 2
cat > /tmp/flymaps/undef_zone.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
connection: a-ghost
EOF

# 4h max_drones=0 (must be positive) -> exit 2
cat > /tmp/flymaps/zero_cap.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
hub: c 2 2 [zone=normal max_drones=0]
connection: a-c
connection: c-b
EOF

# 4i unrecognised line -> exit 2
cat > /tmp/flymaps/garbage.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 1 1
this is not valid syntax
EOF
```

Now assert each one:
```bash
for f in no_drones no_start no_end dup_zone dup_conn bad_type undef_zone zero_cap garbage; do
  uv run python -m src /tmp/flymaps/$f.map >/dev/null 2>/tmp/flymaps/$f.err
  echo "$f EXIT=$? ERR=$(cat /tmp/flymaps/$f.err)"
done
```
PASS per sub-step: `EXIT=2` AND the stderr message names the line/cause (non-empty
`parse error:` text). Record each `EXIT` value.

File-not-found check (exit 1, different from parse error):
```bash
run /tmp/flymaps/does_not_exist.map      # 4j -> must be EXIT=1
```
PASS 4j: `EXIT=1`.

No-path check (valid syntax but start disconnected from end -> exit 3):
```bash
cat > /tmp/flymaps/nopath.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 9 9
hub: island 5 5
connection: a-island
EOF
run /tmp/flymaps/nopath.map              # 4k -> expect EXIT=3 (pathfinding error)
```
PASS 4k: `EXIT=3`. (If it instead exits 0 with zero turns, that's a FAIL — a map
with no route must not report success.)

---

## Section 5 — Simulation rule validation (the core)

This is where real bugs hide. Build three controlled maps with a **known correct
answer**, then check both the turn count and that no rule is violated.

```bash
# 5a single drone, straight line a-c-d-b: minimum 3 turns.
cat > /tmp/flymaps/line.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 3 0
hub: c 1 0
hub: d 2 0
connection: a-c
connection: c-d
connection: d-b
EOF

# 5b two drones, single corridor capacity 1: they must queue, not collide.
cat > /tmp/flymaps/corridor.map <<'EOF'
nb_drones: 2
start_hub: a 0 0
end_hub: b 2 0
hub: c 1 0
connection: a-c
connection: c-b
EOF

# 5c two disjoint paths: two drones should split and finish faster than queueing.
cat > /tmp/flymaps/fork.map <<'EOF'
nb_drones: 2
start_hub: a 0 0
end_hub: b 3 0
hub: up 1 1
hub: down 1 -1
connection: a-up
connection: a-down
connection: up-b
connection: down-b
EOF

# 5d restricted zone costs 2 turns to enter.
cat > /tmp/flymaps/restricted.map <<'EOF'
nb_drones: 1
start_hub: a 0 0
end_hub: b 2 0
hub: c 1 0 [zone=restricted]
connection: a-c
connection: c-b
EOF
```

Run each through the simulation validator (Section 8):
```bash
for f in line corridor fork restricted; do
  echo "=== $f ==="
  uv run python -m src /tmp/flymaps/$f.map | tee /tmp/flymaps/$f.out
  python3 /tmp/validate_flyin.py /tmp/flymaps/$f.map /tmp/flymaps/$f.out
done
```

PASS criteria per map:
- Validator prints `SIM_OK` (no capacity/adjacency/duplicate-move violations).
- `line` (5a): total movement turns for the drone = 3 (a→c→d→b).
- `corridor` (5b): the two drones never occupy `c` on the same turn (capacity 1).
  Validator enforces this; also expect total turns ≥ 4 (they queue).
- `fork` (5c): both drones reach `b`; total turns should be **less** than the
  corridor case for the same drone count (they used both paths). If `fork` takes
  as many turns as `corridor`, the scheduler isn't distributing — record FAIL.
- `restricted` (5d): entering `c` consumes 2 turns. Expect the in-flight
  connection notation (`D1-<connection>`) on the intermediate turn, then arrival.
  Total ≥ 3 turns. If `c` is treated as cost 1, FAIL.

---

## Section 6 — Determinism / idempotency

The same map must give the same result every run (no hidden randomness).

```bash
for i in 1 2 3; do uv run python -m src data/maps/medium_01.map | grep "Total turns:"; done
```
PASS: all three lines identical. If turn counts vary between runs, there is
nondeterminism in scheduling — record FAIL with the differing values.

---

## Section 7 — Stress / scale

Confirm it handles a larger drone count without crashing or hanging.

```bash
sed 's/^nb_drones:.*/nb_drones: 50/' data/maps/hard_01.map > /tmp/flymaps/many.map
timeout 60 uv run python -m src /tmp/flymaps/many.map | tail -8
echo "EXIT=${PIPESTATUS[0]}"
```
PASS: `EXIT=0`, no traceback, finishes before the 60s timeout, stats block
present. (`EXIT=124` = hang = FAIL.)

---

## Section 8 — Validator script (save once, reuse)

Save as `/tmp/validate_flyin.py`. It re-parses the map and replays the output to
check every movement obeys adjacency and capacity.

```python
import sys, re

map_path, out_path = sys.argv[1], sys.argv[2]

# --- minimal map parse: adjacency + capacities ---
adj, cap, start, end = {}, {}, None, None
default_cap = {}
for raw in open(map_path):
    line = raw.split('#', 1)[0].strip()
    if not line: continue
    if line.startswith('start_hub:'): start = line.split()[1]
    elif line.startswith('end_hub:'): end = line.split()[1]
    if line.startswith(('start_hub:', 'end_hub:', 'hub:')):
        name = line.split()[1]
        adj.setdefault(name, set())
        m = re.search(r'max_drones=(\d+)', line)
        default_cap[name] = int(m.group(1)) if m else 1
    if line.startswith('connection:'):
        body = line.split(':', 1)[1].strip().split()[0]
        if '-' in body:
            x, y = body.split('-', 1)
            adj.setdefault(x, set()).add(y)
            adj.setdefault(y, set()).add(x)

# start and end have effectively unlimited capacity
default_cap[start] = 10**9
default_cap[end]   = 10**9

# --- replay output ---
pos = {}             # drone -> current zone (None = still at start)
violations = []
turn = 0
for raw in open(out_path):
    line = raw.strip()
    if not line or line.startswith('---') or ':' in line and 'D' not in line:
        continue
    if not re.match(r'^(D\d+-\S+)(\s+D\d+-\S+)*$', line):
        continue  # skip non-movement lines (stats, "Loaded map", etc.)
    turn += 1
    moves = line.split()
    dest_count = {}
    for mv in moves:
        drone, dest = mv.split('-', 1)
        prev = pos.get(drone, start)
        # adjacency check (skip connection-name in-flight tokens we can't resolve)
        if dest in adj and prev in adj and dest not in adj.get(prev, set()) and dest != prev:
            # allow if dest reachable (restricted in-flight uses connection names)
            violations.append(f"turn {turn}: {drone} {prev}->{dest} not adjacent")
        pos[drone] = dest
        if dest in default_cap:
            dest_count[dest] = dest_count.get(dest, 0) + 1
    # capacity check for this turn's destinations
    # (approximate: count drones currently sitting in each zone)
    occ = {}
    for d, z in pos.items():
        occ[z] = occ.get(z, 0) + 1
    for z, n in occ.items():
        if z in default_cap and n > default_cap[z]:
            violations.append(f"turn {turn}: zone {z} holds {n} > cap {default_cap[z]}")

print("TOTAL_MOVE_TURNS", turn)
if violations:
    print("SIM_FAIL")
    for v in violations[:15]: print("  " + v)
else:
    print("SIM_OK")
```

> Note: this validator is intentionally conservative. It cannot resolve the
> exact connection name used during a restricted-zone in-flight turn, so it skips
> adjacency on tokens it can't map and focuses on capacity. If it prints
> `SIM_FAIL` on capacity, that is a hard bug. If adjacency warnings appear only on
> restricted maps, flag for human review rather than auto-failing.

---

## Section 9 — Report template (fill and return)

```
FLY-IN TEST REPORT
==================
Date:
Python / uv version:

S1 Setup:            PASS / FAIL
S2 Lint:             flake8+mypy ___   strict ___
S3 Provided maps:    (list each map -> EXIT, turns, SIM_OK?)
S4 Parser errors:    4a__ 4b__ 4c__ 4d__ 4e__ 4f__ 4g__ 4h__ 4i__ 4j__ 4k__
S5 Rule validation:  line(turns=__) corridor(turns=__,SIM__) fork(turns=__) restricted(turns=__)
                     fork < corridor ? ___
S6 Determinism:      3 runs equal? ___ (values: __ __ __)
S7 Stress 50 drones: EXIT__ time-ok?__
S8 (validator used)

OVERALL: PASS only if S1,S2(lint),S3(all),S4(all exit codes),S5(no SIM_FAIL),S6 pass.
Failures to escalate:
1.
2.
```

---

## Section 10 — Devil's-advocate notes (for the human)

1. **`edge_cases.txt` claims "fork distributes drones."** Section 5c is the only
   step that actually measures it (fork turns < corridor turns). If they're equal,
   the algorithm is single-path and the README's "maximize throughput" claim is
   false — a likely peer-review failure.
2. **Exit-code contract is load-bearing.** A weak parser that prints an error but
   still `exit 0` would pass a naive eyeball test; Section 4 asserts the *code*.
3. **Restricted = 2 turns** is easy to get wrong (off-by-one, or treated as cost
   1). Section 5d isolates it. The validator can't fully verify in-flight tokens,
   so the human must confirm the `D1-<connection>` line appears.
4. **Determinism (S6)** matters because peer review re-runs maps; a scheduler with
   set/dict iteration order bugs can give different turn counts per run.
```
