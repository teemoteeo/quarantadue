#!/usr/bin/env bash
# Codexion defense test harness.
# Deps: coreutils, grep, awk, valgrind. No bash arrays of cleverness, just checks.
# Args order: nb_coders burnout compile debug refactor compiles_required cooldown scheduler

BIN=./codexion
PASS=0
FAIL=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }

ok()   { PASS=$((PASS+1)); printf '[%s] %s\n' "$(green PASS)" "$1"; }
ko()   { FAIL=$((FAIL+1)); printf '[%s] %s\n' "$(red FAIL)" "$1";
         [ -n "$2" ] && printf '       %s\n' "$2"; }

section() { printf '\n=== %s ===\n' "$1"; }

# ---------------------------------------------------------------------------
section "BUILD"
make re >/tmp/cx_build.log 2>&1
if [ $? -eq 0 ] && [ -x "$BIN" ]; then ok "make re"; else
  ko "make re" "$(tail -3 /tmp/cx_build.log)"; echo "cannot continue"; exit 1
fi

# ===========================================================================
# 1. ARGUMENT VALIDATION  -> expect non-zero exit, usage on stderr, no crash
# ===========================================================================
section "ARGUMENT VALIDATION (expect non-zero exit + stderr usage, no crash)"

check_reject() {
  desc="$1"; shift
  err=$(timeout 3 "$BIN" "$@" 2>&1 >/dev/null)
  code=$?
  if [ $code -eq 124 ]; then ko "$desc" "hung (timeout)"; return; fi
  if [ $code -eq 139 ] || [ $code -eq 134 ]; then ko "$desc" "crash (sig $code)"; return; fi
  if [ $code -eq 0 ]; then ko "$desc" "accepted, exit 0"; return; fi
  if [ -z "$err" ]; then ko "$desc" "non-zero exit but nothing on stderr"; return; fi
  ok "$desc (exit $code)"
}

check_reject "too few args"            1 2 3
check_reject "too many args"           4 800 200 200 200 5 100 fifo extra
check_reject "negative nb_coders"      -4 800 200 200 200 5 100 fifo
check_reject "negative burnout"        4 -800 200 200 200 5 100 fifo
check_reject "non-numeric abc"         abc 800 200 200 200 5 100 fifo
check_reject "float 1.5"               1.5 800 200 200 200 5 100 fifo
check_reject "zero nb_coders"          0 800 200 200 200 5 100 fifo
check_reject "zero compile"            4 800 0 200 200 5 100 fifo
check_reject "zero compiles_required"  4 800 200 200 200 0 100 fifo
check_reject "scheduler FIFO (caps)"   4 800 200 200 200 5 100 FIFO
check_reject "scheduler random"        4 800 200 200 200 5 100 random
check_reject "scheduler empty"         4 800 200 200 200 5 100 ""
check_reject "nb_coders 100000 (>MAX)" 100000 800 200 200 200 5 100 fifo

# ===========================================================================
# 2. N=1  -> exactly one "has taken a dongle" then "burned out", must exit
# ===========================================================================
section "N=1 SINGLE DONGLE BURNOUT"

out=$(timeout 3 "$BIN" 1 200 100 100 100 5 50 fifo 2>&1); code=$?
if [ $code -eq 124 ]; then
  ko "N=1 burns out and exits" "hung"
else
  taken=$(echo "$out" | grep -c "has taken a dongle")
  comp=$(echo "$out" | grep -c "is compiling")
  last=$(echo "$out" | tail -1)
  if [ "$taken" -eq 1 ] && [ "$comp" -eq 0 ] && echo "$last" | grep -q "burned out"; then
    ok "N=1: 1 taken, 0 compiling, ends burned out"
  else
    ko "N=1 single-dongle" "taken=$taken compiling=$comp last='$last'"
  fi
fi

# ===========================================================================
# 3. FEASIBLE: no burnout (fifo + edf), run ~5s, assert NO "burned out"
# ===========================================================================
section "FEASIBLE (no coder should burn out)"

no_burnout() {
  desc="$1"; shift
  timeout 5 "$BIN" "$@" >/tmp/cx_feas.log 2>&1   # timeout-guard; 124 expected (long run)
  if grep -q "burned out" /tmp/cx_feas.log; then
    ko "$desc" "$(grep 'burned out' /tmp/cx_feas.log | head -1)"
  else
    ok "$desc (no burnout in 5s)"
  fi
}
no_burnout "feasible fifo" 4 1500 200 200 200 1000 100 fifo
no_burnout "feasible edf"  4 1500 200 200 200 1000 100 edf

# ===========================================================================
# 4. FORCED BURNOUT: last line is "burned out", nothing after. Repeat 40x.
# ===========================================================================
section "FORCED BURNOUT ORDERING (40x)"

bad=0; hang=0
for i in $(seq 1 40); do
  out=$(timeout 3 "$BIN" 4 250 200 300 300 100 100 fifo 2>&1)
  [ $? -eq 124 ] && hang=$((hang+1))
  last=$(echo "$out" | tail -1)
  echo "$last" | grep -q "burned out" || { bad=$((bad+1)); badline="$last"; }
done
if [ $hang -ne 0 ]; then ko "burnout ordering 40x" "$hang/40 hung"
elif [ $bad -eq 0 ]; then ok "burnout ordering 40x: burned out always last"
else ko "burnout ordering 40x" "$bad/40 had trailing line e.g. '$badline'"; fi

# ===========================================================================
# 5. BURNOUT PRECISION: timestamp within [burnout, burnout+10] ms
# ===========================================================================
section "BURNOUT PRECISION"

BO=300; tol_hi=$((BO+10))
prec_bad=0
for i in 1 2 3 4 5; do
  ts=$(timeout 3 "$BIN" 1 $BO 100 100 100 9 50 fifo 2>&1 | grep "burned out" | head -1 | awk '{print $1}')
  if [ -z "$ts" ]; then prec_bad=$((prec_bad+1)); continue; fi
  if [ "$ts" -lt "$BO" ] || [ "$ts" -gt "$tol_hi" ]; then
    prec_bad=$((prec_bad+1)); last_ts=$ts
  fi
done
if [ $prec_bad -eq 0 ]; then ok "burnout logged within [$BO,$tol_hi]ms (5 runs)"
else ko "burnout precision" "$prec_bad/5 outside window (e.g. ${last_ts}ms)"; fi

# ===========================================================================
# 6. COMPLETION: feasible small required ends on its own, exit 0, no burnout
# ===========================================================================
section "COMPLETION"

timeout 6 "$BIN" 3 2000 100 100 100 2 50 fifo >/tmp/cx_done.log 2>&1; code=$?
if [ $code -eq 124 ]; then ko "completion ends on its own" "hung"
elif [ $code -ne 0 ]; then ko "completion exit 0" "exit=$code"
elif grep -q "burned out" /tmp/cx_done.log; then ko "completion no burnout" "burned out appeared"
else ok "completion: exit 0, no burnout"; fi

# ===========================================================================
# 7. LOG FORMAT: every line matches grammar; each "is compiling" has two
#    "has taken a dongle" (per id) before it (one for N=1).
# ===========================================================================
section "LOG FORMAT"

timeout 5 "$BIN" 4 1500 150 150 150 3 80 fifo >/tmp/cx_fmt.log 2>&1
re='^[0-9]+ [0-9]+ (has taken a dongle|is compiling|is debugging|is refactoring|burned out)$'
badfmt=$(grep -vE "$re" /tmp/cx_fmt.log)
if [ -n "$badfmt" ]; then
  ko "line grammar" "$(echo "$badfmt" | head -1)"
else
  ok "every line matches grammar"
fi

# Per-id: walking each coder's own subsequence, every "is compiling" must be
# preceded by 2 "has taken a dongle" since that coder's previous compile.
awk '
{
  id=$2; msg=substr($0, index($0,$3))
  if (msg=="has taken a dongle") taken[id]++
  else if (msg=="is compiling") {
    if (taken[id] < 2) { print "id "id" compiled with only "taken[id]" dongle(s)"; bad=1 }
    taken[id]=0
  }
}
END { exit bad }
' /tmp/cx_fmt.log >/tmp/cx_fmt_err.log
if [ $? -eq 0 ]; then ok "each compile preceded by two taken (per id)"
else ko "two-taken-per-compile" "$(head -1 /tmp/cx_fmt_err.log)"; fi

# N=1 variant: one taken before (no compile expected, but assert no compile
# ever fires without its single taken)
timeout 3 "$BIN" 1 400 100 100 100 9 50 fifo >/tmp/cx_fmt1.log 2>&1
c1=$(grep -c "is compiling" /tmp/cx_fmt1.log)
if [ "$c1" -eq 0 ]; then ok "N=1 never compiles (1 dongle)"
else ko "N=1 never compiles" "saw $c1 compiling lines"; fi

# ===========================================================================
# 8. VALGRIND LEAK CHECK: burnout run + completion run, expect exit 0
# ===========================================================================
section "VALGRIND LEAK CHECK"

valgrind --leak-check=full --error-exitcode=42 -q \
  timeout 3 "$BIN" 4 250 200 300 300 100 100 fifo >/dev/null 2>/tmp/cx_vg1.log
[ $? -eq 0 ] && ok "valgrind burnout run: no leaks" \
            || ko "valgrind burnout run" "$(grep -E 'lost|ERROR SUMMARY' /tmp/cx_vg1.log | head -2)"

valgrind --leak-check=full --error-exitcode=42 -q \
  timeout 6 "$BIN" 3 2000 100 100 100 2 50 fifo >/dev/null 2>/tmp/cx_vg2.log
[ $? -eq 0 ] && ok "valgrind completion run: no leaks" \
            || ko "valgrind completion run" "$(grep -E 'lost|ERROR SUMMARY' /tmp/cx_vg2.log | head -2)"

# ===========================================================================
# 9. HELGRIND: real "Possible data race" = FAIL; dubious cond = benign/info
# ===========================================================================
section "HELGRIND DATA RACE (informational)"

valgrind --tool=helgrind -q \
  timeout 6 "$BIN" 3 400 100 150 150 3 80 fifo >/dev/null 2>/tmp/cx_hg.log
races=$(grep -c "Possible data race" /tmp/cx_hg.log)
if [ "$races" -eq 0 ]; then ok "helgrind: 0 data races"
else ko "helgrind: $races data race(s)" "$(grep -A2 'Possible data race' /tmp/cx_hg.log | head -4)"; fi

# ===========================================================================
# 10. STRESS / DEADLOCK: varied N, generous guard (slow != deadlock).
#     Force burnout so a healthy run terminates fast; a hang = deadlock.
# ===========================================================================
section "STRESS / DEADLOCK (forced-stop, hang = FAIL)"

for n in 2 5 50 200; do
  # tiny burnout guarantees the sim stops quickly if scheduling is live
  timeout 8 "$BIN" "$n" 120 40 40 40 1000 30 edf >/dev/null 2>&1; code=$?
  if [ $code -eq 124 ]; then ko "stress N=$n edf" "hung (possible deadlock)"
  else ok "stress N=$n edf (exit $code)"; fi
done
for n in 2 5 50 200; do
  timeout 8 "$BIN" "$n" 120 40 40 40 1000 30 fifo >/dev/null 2>&1; code=$?
  if [ $code -eq 124 ]; then ko "stress N=$n fifo" "hung (possible deadlock)"
  else ok "stress N=$n fifo (exit $code)"; fi
done

# ===========================================================================
section "SUMMARY"
printf 'TOTAL: %s passed, %s failed\n' "$(green $PASS)" "$([ $FAIL -eq 0 ] && green 0 || red $FAIL)"
[ $FAIL -eq 0 ] && exit 0 || exit 1
