# Call Me Maybe — Debug & Test Plan

> **Executor model: read this first.**
> You are running a fixed test script, not improvising. Follow steps **in order**.
> For every step: run the exact command, capture output, compare to the **PASS
> criteria**, write `PASS`/`FAIL` in the report (Section 9).
> **Do NOT edit source files.** If a step fails, record it and continue.
> The single most important property here is: **every output must be valid JSON
> that exactly matches the schema** in `functions_definition.json`. Accuracy is
> secondary to validity, but both are tested.

Project root for all commands: the folder containing this file (`call me maybe/`).
`cd` into it first. Note the space in the folder name — always quote paths.

Invocation:
```
uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json
```

**Exit codes** (from `src/__main__.py`):

| Exit | Meaning                              |
|------|--------------------------------------|
| 0    | success                              |
| 2    | loader error (bad/missing input)     |
| 3    | output write error (OSError)         |

Helper:
```bash
run() { uv run python -m src "$@"; echo "EXIT=$?"; }
```

---

## Section 1 — Setup (BLOCKING)

```bash
make install 2>&1 | tee /tmp/cmm_install.log
uv run python -c "import src, llm_sdk; print('IMPORT_OK')"
```
PASS: install finishes with no error and `IMPORT_OK` prints. The model weights
(Qwen3-0.6B) may download on first import — allow up to a few minutes. If FAIL,
**STOP**.

---

## Section 2 — Static analysis

```bash
make lint 2>&1 | tee /tmp/cmm_lint.log
echo "LINT_EXIT=${PIPESTATUS[0]}"
make lint-strict 2>&1 | tee /tmp/cmm_lint_strict.log
echo "STRICT_EXIT=${PIPESTATUS[0]}"
```
PASS: `LINT_EXIT=0`. Record `STRICT_EXIT`; if strict fails but normal passes,
FAIL strict only and continue.

---

## Section 3 — Baseline run + timing

```bash
rm -f data/output/function_calling_results.json
/usr/bin/time -p uv run python -m src \
  --functions_definition data/input/functions_definition.json \
  --input data/input/function_calling_tests.json \
  --output data/output/function_calling_results.json 2>/tmp/cmm_time.log
echo "EXIT=$?"
cat /tmp/cmm_time.log
```
PASS (ALL):
- `EXIT=0`.
- `data/output/function_calling_results.json` now exists.
- `real` time (from `/tmp/cmm_time.log`) is **under 300 seconds** (subject: <5 min).
- No Python traceback in output.

---

## Section 4 — Output validity & schema compliance (the core test)

Run the validator from Section 8 against the produced output. This is the
subject's hard requirement: 100% valid JSON, exact schema, no extra keys.

```bash
python3 /tmp/validate_cmm.py \
  data/input/functions_definition.json \
  data/input/function_calling_tests.json \
  data/output/function_calling_results.json
```
PASS (ALL must print):
- `JSON_PARSE_OK` — file parses as JSON (no trailing commas/comments).
- `COUNT_OK` — one result object per input prompt, same order.
- `KEYS_OK` — every object has exactly `prompt`, `name`, `parameters` and nothing
  else.
- `NAME_OK` — every `name` is one of the names in `functions_definition.json`.
- `PARAMS_OK` — for each object, `parameters` keys exactly match the chosen
  function's declared parameters, and each value's type matches (`number`→
  int/float, `string`→str, `boolean`→bool).

ANY of these printing the `_FAIL` variant = FAIL. The validator lists the first
offending objects — copy them into the report.

---

## Section 5 — Accuracy spot-check (90%+ target)

The subject wants 90%+ correct function selection + argument extraction. You
cannot judge "correct" by reading; use this fixed expectation table built from the
shipped inputs. Compare the produced `name` (and obvious args) against it.

```bash
python3 - <<'PY'
import json
out = json.load(open("data/output/function_calling_results.json"))
# expected function name keyed by a substring of the prompt:
rules = [
    ("sum of",        "fn_add_numbers"),
    ("Greet",         "fn_greet"),
    ("Reverse",       "fn_reverse_string"),
    ("square root",   "fn_get_square_root"),
    ("Replace",       "fn_substitute_string_with_regex"),
    ("Sub",           "fn_substitute_string_with_regex"),
]
def expected(p):
    for sub, fn in rules:
        if sub.lower() in p.lower():
            return fn
    return None
ok = tot = 0
misses = []
for o in out:
    e = expected(o.get("prompt",""))
    if e is None:        # prompt we have no rule for -> skip from denominator
        continue
    tot += 1
    if o.get("name") == e: ok += 1
    else: misses.append((o.get("prompt"), o.get("name"), e))
print(f"ACCURACY {ok}/{tot}" + (f" = {100*ok/tot:.0f}%" if tot else ""))
for m in misses[:10]:
    print("  MISS:", m)
PY
```
PASS: accuracy ≥ 90% on the scored prompts. List every MISS in the report.
(Prompts with no rule are skipped — that's fine, this is a spot-check, not a
full grader.)

---

## Section 6 — Argument-type correctness

Numbers must be JSON numbers (not strings), strings must be strings. Quick assert:

```bash
python3 - <<'PY'
import json
defs = {f["name"]: f["parameters"] for f in json.load(open("data/input/functions_definition.json"))}
out = json.load(open("data/output/function_calling_results.json"))
bad = []
for o in out:
    params = defs.get(o.get("name"), {})
    for k, spec in params.items():
        if k not in o.get("parameters", {}):
            bad.append((o["prompt"], f"missing arg {k}")); continue
        v = o["parameters"][k]; t = spec["type"]
        if t == "number" and not isinstance(v, (int, float)): bad.append((o["prompt"], f"{k} not number: {v!r}"))
        if t == "string" and not isinstance(v, str):          bad.append((o["prompt"], f"{k} not string: {v!r}"))
        if t == "boolean" and not isinstance(v, bool):        bad.append((o["prompt"], f"{k} not bool: {v!r}"))
print("TYPES_OK" if not bad else "TYPES_FAIL")
for b in bad[:15]: print("  ", b)
PY
```
PASS: prints `TYPES_OK`.

---

## Section 7 — Error handling (must fail gracefully, not crash)

The subject: handle malformed JSON, missing files, edge inputs. Build broken
inputs and assert a clean non-zero exit (exit 2), NOT a traceback.

```bash
mkdir -p /tmp/cmm

# 7a malformed functions JSON (trailing comma) -> exit 2, no traceback
printf '[{"name":"x",}]' > /tmp/cmm/bad_funcs.json
uv run python -m src --functions_definition /tmp/cmm/bad_funcs.json \
  --input data/input/function_calling_tests.json --output /tmp/cmm/o1.json 2>/tmp/cmm/e1.log
echo "7a EXIT=$?"; grep -c "Traceback" /tmp/cmm/e1.log

# 7b missing functions file -> exit 2
uv run python -m src --functions_definition /tmp/cmm/nope.json \
  --input data/input/function_calling_tests.json --output /tmp/cmm/o2.json 2>/tmp/cmm/e2.log
echo "7b EXIT=$?"; grep -c "Traceback" /tmp/cmm/e2.log

# 7c malformed input tests JSON -> exit 2
printf '[{"prompt": }]' > /tmp/cmm/bad_tests.json
uv run python -m src --functions_definition data/input/functions_definition.json \
  --input /tmp/cmm/bad_tests.json --output /tmp/cmm/o3.json 2>/tmp/cmm/e3.log
echo "7c EXIT=$?"; grep -c "Traceback" /tmp/cmm/e3.log

# 7d empty prompt list -> should exit 0 with an empty [] output (no crash)
printf '[]' > /tmp/cmm/empty.json
uv run python -m src --functions_definition data/input/functions_definition.json \
  --input /tmp/cmm/empty.json --output /tmp/cmm/o4.json 2>/tmp/cmm/e4.log
echo "7d EXIT=$?"; cat /tmp/cmm/o4.json
```
PASS criteria:
- 7a, 7b, 7c: `EXIT=2` AND the `grep -c "Traceback"` count is `0` (graceful, not a
  crash). If exit is 0 or a traceback prints, FAIL.
- 7d: `EXIT=0` AND `/tmp/cmm/o4.json` contains `[]` (or an empty array). A crash
  on empty input is FAIL.

---

## Section 8 — Validator script (save once, reuse)

Save as `/tmp/validate_cmm.py`:

```python
import sys, json

defs_path, in_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    funcs = json.load(open(defs_path))
    prompts = json.load(open(in_path))
    raw = open(out_path).read()
    out = json.loads(raw)
    print("JSON_PARSE_OK")
except Exception as e:
    print("JSON_PARSE_FAIL", e); sys.exit(0)

fn_params = {f["name"]: set(f.get("parameters", {}).keys()) for f in funcs}
fn_types  = {f["name"]: {k: v["type"] for k, v in f.get("parameters", {}).items()} for f in funcs}
valid_names = set(fn_params)

# count / order
if len(out) == len(prompts):
    print("COUNT_OK")
else:
    print(f"COUNT_FAIL out={len(out)} prompts={len(prompts)}")

ALLOWED = {"prompt", "name", "parameters"}
keys_ok = names_ok = params_ok = True
key_bad, name_bad, param_bad = [], [], []

for i, o in enumerate(out):
    if not isinstance(o, dict) or set(o.keys()) != ALLOWED:
        keys_ok = False; key_bad.append((i, list(o.keys()) if isinstance(o, dict) else type(o).__name__))
        continue
    name = o["name"]
    if name not in valid_names:
        names_ok = False; name_bad.append((i, name)); continue
    got = set(o["parameters"].keys()) if isinstance(o["parameters"], dict) else None
    if got != fn_params[name]:
        params_ok = False; param_bad.append((i, name, got, fn_params[name])); continue
    for k, v in o["parameters"].items():
        t = fn_types[name][k]
        if t == "number" and not isinstance(v, (int, float)): params_ok = False; param_bad.append((i, name, f"{k} not number {v!r}"))
        if t == "string" and not isinstance(v, str):          params_ok = False; param_bad.append((i, name, f"{k} not string {v!r}"))
        if t == "boolean" and not isinstance(v, bool):        params_ok = False; param_bad.append((i, name, f"{k} not bool {v!r}"))

print("KEYS_OK"   if keys_ok   else "KEYS_FAIL");   [print("  obj", *b) for b in key_bad[:8]]
print("NAME_OK"   if names_ok  else "NAME_FAIL");   [print("  obj", *b) for b in name_bad[:8]]
print("PARAMS_OK" if params_ok else "PARAMS_FAIL"); [print("  obj", *b) for b in param_bad[:8]]
```

---

## Section 9 — Report template (fill and return)

```
CALL ME MAYBE TEST REPORT
=========================
Date:
Model download cached? (Y/N):

S1 Setup:            PASS / FAIL
S2 Lint:             flake8+mypy ___   strict ___
S3 Baseline run:     EXIT__  output-exists__  real_time_s__ (<300?)
S4 Schema validity:  JSON__ COUNT__ KEYS__ NAME__ PARAMS__
S5 Accuracy:         __/__ = __%   (>=90%?)   misses listed below
S6 Arg types:        TYPES_OK / TYPES_FAIL
S7 Error handling:   7a EXIT__ tb__  7b EXIT__ tb__  7c EXIT__ tb__  7d EXIT__ empty__
S8 (validator used)

OVERALL: PASS only if S1,S2(lint),S3,S4(all OK),S5(>=90%),S6,S7(all) pass.
Failures / misses to escalate:
1.
2.
```

---

## Section 10 — Devil's-advocate notes (for the human)

1. **README claims "100% valid JSON by construction."** Section 4 is the only
   thing that proves it on *this* output. The claim is only as good as the last
   run; the subject warns inputs change at review, so don't treat one green run
   as a guarantee — re-run with a different `functions_definition.json` before
   submission.
2. **Accuracy vs validity are different failures.** Constrained decoding can emit
   perfectly valid JSON that calls the *wrong* function (e.g. picks `fn_greet` for
   a math prompt). Section 5 catches that; Section 4 would not. Both matter.
3. **The spot-check in S5 is not the real grader.** It only scores prompts it has
   a keyword rule for. A high score here is necessary, not sufficient — flag for a
   human to run the full provided test set.
4. **Type coercion traps.** `"a": "40"` (string) vs `"a": 40` (number) both
   "look" right but the second is correct per schema. S6 isolates this; it's a
   common silent bug in constrained decoders that emit numbers as quoted strings.
5. **Edge inputs the plan does not fully cover** (subject explicitly lists them):
   empty strings, very large numbers, special characters, ambiguous prompts. If
   time allows, the human should add a few such prompts to a copy of the input
   file and re-run Section 4 — the executor model should not invent these itself.
```
