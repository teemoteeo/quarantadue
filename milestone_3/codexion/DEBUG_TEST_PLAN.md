# Codexion — Debug & Test Plan

> **Executor model: read this first.**
> You are running a fixed test script, not improvising. Follow steps **in order**.
> For every step: run the exact command, capture the output, compare it to the
> **PASS criteria**, and write `PASS` or `FAIL` in the report (Section 9).
> **Do NOT edit source files.** If a step fails, record it and continue to the
> next step. Only stop early if the build itself fails (Step 1).
> **Do NOT trust `edge_cases.txt`.** That file is the author's claim. Your job is
> to re-verify mechanically. A ✅ in that file means nothing until your command
> reproduces it.

Project root for all commands: the folder containing this file (`codexion/`).
`cd` into it before starting.

```bash
cd "$(dirname "$0")" 2>/dev/null || true   # or manually: cd path/to/codexion
```

Binary invocation (8 mandatory args, all integers except the last):
```
./codexion <n_coders> <burnout_ms> <compile_ms> <debug_ms> <refactor_ms> <n_compiles> <cooldown_ms> <fifo|edf>
```

---

## Section 0 — Definitions (so you can judge output)

A log line MUST look like exactly: `<timestamp_ms> <coder_id> <message>` where
`message` is one of: `has taken a dongle`, `is compiling`, `is debugging`,
`is refactoring`, `burned out`.

- `coder_id` is an integer from `1` to `n_coders`.
- `timestamp_ms` is a non-negative integer, and timestamps must be
  **non-decreasing** down the file (each line ≥ the line before).
- The first event in the whole run starts near `0` (the first taken-dongle line
  should have a small timestamp, typically `0`–`5`).
- "Success run" = the program exits and **no line contains `burned out`**.
- "Burnout run" = at least one line contains `burned out`; the program must stop
  shortly after.

Helper commands you will reuse (copy exactly):

```bash
# Run with a 10s hard timeout so a hang cannot block you:
run() { timeout 10 ./codexion "$@"; echo "EXIT=$?"; }
```

`EXIT=124` from `timeout` means the program **hung** — that is a FAIL (deadlock).

---

## Section 1 — Build (BLOCKING: stop if this fails)

```bash
make re 2>&1 | tee /tmp/codexion_build.log
```

PASS criteria (ALL must hold):
- Last lines show the binary linked, no error.
- `grep -iE "error|warning" /tmp/codexion_build.log` prints **nothing**.
- `test -x ./codexion && echo BINARY_OK` prints `BINARY_OK`.

If FAIL: record the first error line in the report and **STOP**. Nothing else
can be tested without a binary.

---

## Section 2 — Norminette (42 style gate)

```bash
norminette src/ include/ 2>&1 | tee /tmp/codexion_norm.log
grep -c "Error" /tmp/codexion_norm.log
```

PASS criteria:
- Every file line ends in `OK!`.
- The `grep -c "Error"` count is `0`.

If `norminette` is not installed, write `SKIPPED (norminette not installed)` and
continue. Do not try to install it.

---

## Section 3 — Build variants for bug detection

You will build two extra instrumented binaries. These are throwaway and live in
`/tmp`. Source is NOT modified.

```bash
# ThreadSanitizer build (detects data races):
cc -Wall -Wextra -Werror -pthread -fsanitize=thread -g -Iinclude src/*.c -o /tmp/codexion_tsan 2>&1 | tee /tmp/codexion_tsan_build.log
test -x /tmp/codexion_tsan && echo TSAN_OK

# AddressSanitizer + leak build (detects memory bugs & leaks):
cc -Wall -Wextra -Werror -pthread -fsanitize=address -g -Iinclude src/*.c -o /tmp/codexion_asan 2>&1 | tee /tmp/codexion_asan_build.log
test -x /tmp/codexion_asan && echo ASAN_OK
```

PASS criteria: both echo lines print (`TSAN_OK`, `ASAN_OK`) and the build logs
contain no `error`. If a sanitizer is unavailable on this machine, mark that
sub-step `SKIPPED` and continue; the functional tests below still run on the
normal binary.

---

## Section 4 — Argument validation (must reject bad input)

The subject says: reject negatives, non-integers, wrong arg count, and any
scheduler other than exactly `fifo` or `edf`. A rejection = **non-zero exit
code** AND no simulation log produced (or a usage/error message on stderr).

Run each command. For each, PASS = `EXIT` is non-zero (NOT 0) and the program
did not start simulating.

```bash
run 4 1500 200 200 200 3 100               # 4a: only 7 args  -> reject
run -4 1500 200 200 200 3 100 fifo         # 4b: negative coders -> reject
run 0 1500 200 200 200 3 100 fifo          # 4c: zero coders -> reject
run 4 -1 200 200 200 3 100 fifo            # 4d: negative time -> reject
run 4 1500 200 200 200 3 100 FIFO          # 4e: wrong case -> reject
run 4 1500 200 200 200 3 100 bogus         # 4f: bad scheduler -> reject
run 4 1500 abc 200 200 3 100 fifo          # 4g: non-integer -> reject
run 4 1500 200 200 200 3 100 fifo extra    # 4h: 9 args -> reject
```

Record one PASS/FAIL per sub-step (4a–4h). A sub-step FAILS if `EXIT=0` or if any
`has taken a dongle` / `is compiling` line appears.

Then one valid baseline that MUST be accepted:
```bash
run 4 1500 200 200 200 3 100 fifo          # 4i: valid -> must run & exit 0, no burnout
```
PASS for 4i: `EXIT=0` and output contains `is compiling` lines and **no**
`burned out`.

---

## Section 5 — Functional / no-burnout runs (FIFO and EDF)

These parameters give every coder enough time to never burn out. Run each one
and pipe through the validator script in Section 8.

```bash
for sched in fifo edf; do
  echo "=== n=1 $sched ===";  timeout 10 ./codexion 1 800 100 100 100 3 50 $sched  | tee /tmp/c_n1_$sched.log
  echo "=== n=2 $sched ===";  timeout 10 ./codexion 2 1200 150 150 150 3 50 $sched | tee /tmp/c_n2_$sched.log
  echo "=== n=3 $sched ===";  timeout 10 ./codexion 3 2000 200 200 200 3 50 $sched | tee /tmp/c_n3_$sched.log
  echo "=== n=4 $sched ===";  timeout 10 ./codexion 4 2500 200 200 200 3 50 $sched | tee /tmp/c_n4_$sched.log
  echo "=== n=5 $sched ===";  timeout 10 ./codexion 5 3000 200 200 200 5 50 $sched | tee /tmp/c_n5_$sched.log
done
```

For EACH log file, apply Section 8 validator. PASS criteria per run:
- Validator prints `FORMAT_OK`.
- Validator prints `MONOTONIC_OK` (timestamps non-decreasing).
- The log contains **no** `burned out` line.
- The process exited before the 10s timeout (no `EXIT=124`).

Special check for `n=1`: there is only ONE dongle. A single coder cannot compile
(compiling needs two dongles). PASS for n=1 = the program does **not** print
`is compiling` and does **not** hang — it should terminate (by burnout or by a
defined single-dongle rule). Record actual behaviour verbatim; flag for human
review rather than guessing.

---

## Section 6 — Burnout correctness (must detect, must be timely)

Pick parameters where burnout is unavoidable: burnout shorter than one compile.

```bash
timeout 10 ./codexion 3 100 500 200 200 5 50 fifo | tee /tmp/c_burn.log
echo "EXIT=$?"
```

PASS criteria:
- The log contains exactly one `burned out` line (the run stops at first burnout).
- The `burned out` line is the **last** coder-state line (nothing meaningful
  after it).
- Timeliness: the burnout timestamp should be close to `burnout_ms` (here ~100ms)
  measured from that coder's last compile/sim start. Compute with Section 8's
  burnout check; allow tolerance up to +50ms for OS scheduling. Record the
  measured value.

---

## Section 7 — Concurrency & memory instrumentation

Run the sanitizer binaries from Section 3 on a representative load.

```bash
# Data races (ThreadSanitizer):
TSAN_OPTIONS="halt_on_error=0" timeout 30 /tmp/codexion_tsan 4 2500 200 200 200 3 50 fifo > /tmp/c_tsan.out 2>/tmp/c_tsan.err
grep -c "WARNING: ThreadSanitizer" /tmp/c_tsan.err

# Memory errors + leaks (AddressSanitizer):
ASAN_OPTIONS="detect_leaks=1" timeout 30 /tmp/codexion_asan 4 2500 200 200 200 3 50 fifo > /tmp/c_asan.out 2>/tmp/c_asan.err
grep -cE "ERROR: AddressSanitizer|detected memory leaks" /tmp/c_asan.err
```

PASS criteria:
- ThreadSanitizer count is `0` (no data races).
- AddressSanitizer count is `0` (no memory errors, no leaks).

Optional (only if `valgrind` exists; otherwise SKIP):
```bash
valgrind --tool=helgrind --error-exitcode=42 ./codexion 3 2000 200 200 200 3 50 fifo > /dev/null 2>/tmp/c_helgrind.err
echo "HELGRIND_EXIT=$?"
```
PASS = `HELGRIND_EXIT` is not `42` (no lock-order / race warnings). Note: Helgrind
on correct code may still emit benign warnings about condition variables — if it
fails, copy the first warning block into the report for a human, do not judge it
yourself.

---

## Section 8 — Validator scripts (copy into files, then use)

Save this once as `/tmp/validate_codexion.py`:

```python
import sys, re
PAT = re.compile(r'^(\d+) (\d+) (has taken a dongle|is compiling|is debugging|is refactoring|burned out)$')
lines = [l.rstrip("\n") for l in open(sys.argv[1]) if l.strip()]
fmt_ok, mono_ok, last_ts = True, True, -1
bad = []
for i, l in enumerate(lines, 1):
    m = PAT.match(l)
    if not m:
        fmt_ok = False; bad.append((i, l)); continue
    ts = int(m.group(1))
    if ts < last_ts:
        mono_ok = False; bad.append((i, f"timestamp {ts} < previous {last_ts}"))
    last_ts = ts
print("FORMAT_OK" if fmt_ok else "FORMAT_FAIL")
print("MONOTONIC_OK" if mono_ok else "MONOTONIC_FAIL")
print("BURNOUT_PRESENT" if any("burned out" in l for l in lines) else "NO_BURNOUT")
for i, b in bad[:10]:
    print(f"  line {i}: {b}")
```

Use it on any run:
```bash
python3 /tmp/validate_codexion.py /tmp/c_n4_fifo.log
```

Burnout timing check (only meaningful on a burnout run):
```bash
python3 - /tmp/c_burn.log <<'PY'
import sys
lines=[l.split(None,2) for l in open(sys.argv[1]) if l.strip()]
burn=[l for l in lines if len(l)==3 and l[2].strip()=="burned out"]
print("BURN_LINES", len(burn))
if burn: print("BURN_TS_MS", burn[0][0])
PY
```
Compare `BURN_TS_MS` against the expected `burnout_ms` from the run.

---

## Section 9 — Report template (fill and return this)

```
CODEXION TEST REPORT
====================
Date:
Machine (uname -a):

S1 Build:           PASS / FAIL   notes:
S2 Norminette:      PASS / FAIL / SKIPPED   error_count:
S3 Sanitizer builds: TSAN __  ASAN __  (OK/SKIP)
S4 Arg validation:  4a__ 4b__ 4c__ 4d__ 4e__ 4f__ 4g__ 4h__ 4i__
S5 No-burnout runs:
    n1 fifo__ edf__   n2 fifo__ edf__   n3 fifo__ edf__
    n4 fifo__ edf__   n5 fifo__ edf__
    (n=1 observed behaviour: ____________________)
S6 Burnout:         PASS / FAIL   burn_ts_ms:___ expected:~100
S7 ThreadSanitizer warnings:___  ASan errors/leaks:___  Helgrind:___
S8 (validator used)

OVERALL: PASS only if S1,S2,S3,S4(all),S5(all),S6,S7 pass.
Failures to escalate to human:
1.
2.
```

---

## Section 10 — Devil's-advocate notes (for the human, not the executor)

Things the ✅ in `edge_cases.txt` does **not** prove and this plan tries to catch:

1. **Races are nondeterministic.** A single clean run proves nothing. That is why
   Section 7 uses ThreadSanitizer — it detects races that didn't happen to fire.
2. **"No deadlock" claims** are only credible under the 10s `timeout` wrapper; an
   `EXIT=124` is the real deadlock signal, not eyeballing the log.
3. **Burnout "within 10ms"** is a timing claim that varies by hardware. Section 6
   measures it instead of trusting it; treat a single machine's number as weak
   evidence.
4. **n=1 with one dongle** is a genuine logical corner (can't hold two) — the
   subject implies one dongle on the table. If the code "passes" it by some hack,
   that's worth a human look, hence the verbatim-record instruction.
```
