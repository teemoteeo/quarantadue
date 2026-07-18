#!/usr/bin/env bash
# Script di test per la difesa di Codexion.
# Dipendenze: coreutils, grep, awk, valgrind. Niente magie con gli array bash, solo controlli.
# Ordine argomenti: nb_coders burnout compile debug refactor compiles_required cooldown scheduler

BIN=./codexion
PASS=0
FAIL=0
trap 'rm -f /tmp/cx_*.log /tmp/cx_fmt_err.log' EXIT

# GNU coreutils include `timeout`; su macOS si chiama `gtimeout` (brew install coreutils).
if command -v timeout >/dev/null 2>&1; then timeout() { command timeout "$@"; }
elif command -v gtimeout >/dev/null 2>&1; then timeout() { command gtimeout "$@"; }
else echo "error: need 'timeout' (Linux) or 'gtimeout' (brew install coreutils)"; exit 1; fi

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }

ok()   { PASS=$((PASS+1)); printf '[%s] %s\n' "$(green PASS)" "$1"; }
ko()   { FAIL=$((FAIL+1)); printf '[%s] %s\n' "$(red FAIL)" "$1";
         [ -n "$2" ] && printf '       %s\n' "$2"; }

section() { printf '\n=== %s ===\n' "$1"; }
skip() { printf '[%s] %s\n' "SKIP" "$1"; [ -n "$2" ] && printf '       %s\n' "$2"; }

# valgrind non gira su Apple Silicon; se manca, saltiamo i controlli su memoria/race.
HAVE_VALGRIND=0
command -v valgrind >/dev/null 2>&1 && HAVE_VALGRIND=1

# ---------------------------------------------------------------------------
section "BUILD"
make re >/tmp/cx_build.log 2>&1
if [ $? -eq 0 ] && [ -x "$BIN" ]; then ok "make re"; else
  ko "make re" "$(tail -3 /tmp/cx_build.log)"; echo "cannot continue"; exit 1
fi

# ===========================================================================
# 1. VALIDAZIONE ARGOMENTI -> ci si aspetta exit non zero, usage su stderr, no crash
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
check_reject "negative compile"        4 800 -200 200 200 5 100 fifo
check_reject "negative debug"          4 800 200 -200 200 5 100 fifo
check_reject "negative refactor"       4 800 200 200 -200 5 100 fifo
check_reject "negative cooldown"       4 800 200 200 200 5 -100 fifo
check_reject "one arg short (7)"       4 800 200 200 200 5 100
check_reject "zero args"

# ===========================================================================
# 2. N=1  -> esattamente un "has taken a dongle" e poi "burned out", deve uscire
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
# 3. FATTIBILE: nessun burnout (fifo + edf), girare ~5s, verificare che NON esca "burned out"
# ===========================================================================
section "FEASIBLE (no coder should burn out)"

no_burnout() {
  desc="$1"; shift
  timeout 5 "$BIN" "$@" >/tmp/cx_feas.log 2>&1   # guardia col timeout; 124 è atteso (run lungo)
  if grep -q "burned out" /tmp/cx_feas.log; then
    ko "$desc" "$(grep 'burned out' /tmp/cx_feas.log | head -1)"
  else
    ok "$desc (no burnout in 5s)"
  fi
}
no_burnout "feasible fifo" 4 1500 200 200 200 1000 100 fifo
no_burnout "feasible edf"  4 1500 200 200 200 1000 100 edf

# ===========================================================================
# 3b. LIMITE DI CONCORRENZA: al massimo floor(N/2) coder in compilazione nello
#     stesso istante (N dongle in cerchio, ne servono 2 per compilare -> tetto rigido).
# ===========================================================================
section "CONCURRENCY BOUND (max floor(N/2) simultaneous compiles)"

conc_check() {
  desc="$1"; n="$2"; shift 2
  timeout 5 "$BIN" "$n" "$@" >/tmp/cx_conc.log 2>&1
  cap=$((n/2))
  awk -v cap="$cap" '
  {
    ts=$1; msg=substr($0, index($0,$3))
    if (msg=="is compiling") ev[ts]++
    else if (msg=="is debugging") ev[ts]--
  }
  END {
    n=0
    for (t in ev) order[++n]=t+0
    for (i=1;i<=n;i++) for (j=i+1;j<=n;j++) if (order[j]<order[i]) { tmp=order[i]; order[i]=order[j]; order[j]=tmp }
    cur=0; maxc=0
    for (i=1;i<=n;i++) { cur+=ev[order[i]]; if (cur>maxc) maxc=cur }
    if (maxc>cap) { print "max concurrent="maxc" cap="cap; exit 1 }
    exit 0
  }' /tmp/cx_conc.log
  if [ $? -eq 0 ]; then ok "$desc (<= floor($n/2)=$cap concurrent)"
  else ko "$desc" "$(awk -v cap="$cap" '{ts=$1; msg=substr($0,index($0,$3)); if(msg=="is compiling")ev[ts]++; else if(msg=="is debugging")ev[ts]--} END{n=0; for(t in ev) o[++n]=t+0; for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)if(o[j]<o[i]){tmp=o[i];o[i]=o[j];o[j]=tmp} cur=0;maxc=0; for(i=1;i<=n;i++){cur+=ev[o[i]]; if(cur>maxc)maxc=cur} print "max concurrent="maxc" cap="cap}' /tmp/cx_conc.log)"
  fi
}
conc_check "concurrency fifo" 6 1500 200 200 200 20 100 fifo
conc_check "concurrency edf"  6 1500 200 200 200 20 100 edf

# ===========================================================================
# 4. BURNOUT FORZATO: l'ultima riga deve essere "burned out", nient'altro dopo. Ripetuto 40 volte.
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
# 5. PRECISIONE DEL BURNOUT: timestamp compreso in [burnout, burnout+10] ms
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
# 6. COMPLETAMENTO: con un target basso e fattibile termina da solo, exit 0, no burnout
# ===========================================================================
section "COMPLETION"

timeout 6 "$BIN" 3 2000 100 100 100 2 50 fifo >/tmp/cx_done.log 2>&1; code=$?
if [ $code -eq 124 ]; then ko "completion ends on its own" "hung"
elif [ $code -ne 0 ]; then ko "completion exit 0" "exit=$code"
elif grep -q "burned out" /tmp/cx_done.log; then ko "completion no burnout" "burned out appeared"
else
  ok "completion: exit 0, no burnout"
  short=$(awk '{c[$2]++} END{for(id in c) if(c[id]<2) print id" saw only "c[id]}' <(grep "is compiling" /tmp/cx_done.log))
  if [ -z "$short" ]; then ok "completion: every coder reached 2 compiles"
  else ko "completion: per-coder compile count" "$short"; fi
fi

# ===========================================================================
# 7. FORMATO DEL LOG: ogni riga rispetta la grammatica; ogni "is compiling" ha
#    due "has taken a dongle" (per id) prima di sé (uno solo per N=1).
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

# Monotonia globale dei timestamp: intercetta bug di interleaving su log_mutex.
nonmono=$(awk '{if ($1+0 < prev) { print NR": "$1" after "prev; exit } prev=$1+0}' /tmp/cx_fmt.log)
if [ -z "$nonmono" ]; then ok "timestamps non-decreasing across log"
else ko "timestamp monotonicity" "$nonmono"; fi

# Per singolo id: scorrendo la sottosequenza di ogni coder, ogni "is compiling"
# deve essere preceduto da 2 "has taken a dongle" dall'ultima sua compilazione.
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

# Variante N=1: un solo taken prima (nessuna compilazione attesa, ma verifichiamo
# che non parta mai senza il suo unico taken)
timeout 3 "$BIN" 1 400 100 100 100 9 50 fifo >/tmp/cx_fmt1.log 2>&1
c1=$(grep -c "is compiling" /tmp/cx_fmt1.log)
if [ "$c1" -eq 0 ]; then ok "N=1 never compiles (1 dongle)"
else ko "N=1 never compiles" "saw $c1 compiling lines"; fi

# ===========================================================================
# 8. CONTROLLO LEAK CON VALGRIND: run di burnout + run di completamento, exit 0 atteso
# ===========================================================================
section "VALGRIND LEAK CHECK"

if [ "$HAVE_VALGRIND" -eq 0 ]; then
  skip "valgrind leak checks" "valgrind unavailable (no Apple Silicon support); run on Linux"
else
  valgrind --leak-check=full --error-exitcode=42 -q \
    timeout 3 "$BIN" 4 250 200 300 300 100 100 fifo >/dev/null 2>/tmp/cx_vg1.log
  [ $? -eq 0 ] && ok "valgrind burnout run: no leaks" \
              || ko "valgrind burnout run" "$(grep -E 'lost|ERROR SUMMARY' /tmp/cx_vg1.log | head -2)"

  valgrind --leak-check=full --error-exitcode=42 -q \
    timeout 6 "$BIN" 3 2000 100 100 100 2 50 fifo >/dev/null 2>/tmp/cx_vg2.log
  [ $? -eq 0 ] && ok "valgrind completion run: no leaks" \
              || ko "valgrind completion run" "$(grep -E 'lost|ERROR SUMMARY' /tmp/cx_vg2.log | head -2)"
fi

# ===========================================================================
# 9. HELGRIND: un vero "Possible data race" = FAIL; condizioni dubbie = info/innocuo
# ===========================================================================
section "HELGRIND DATA RACE (informational)"

if [ "$HAVE_VALGRIND" -eq 0 ]; then
  skip "helgrind data race" "valgrind unavailable (no Apple Silicon support); run on Linux"
else
  valgrind --tool=helgrind -q \
    timeout 6 "$BIN" 3 400 100 150 150 3 80 fifo >/dev/null 2>/tmp/cx_hg.log
  races=$(grep -c "Possible data race" /tmp/cx_hg.log)
  if [ "$races" -eq 0 ]; then ok "helgrind: 0 data races"
  else ko "helgrind: $races data race(s)" "$(grep -A2 'Possible data race' /tmp/cx_hg.log | head -4)"; fi
fi

# ===========================================================================
# 10. STRESS / DEADLOCK: N variabile, guardia generosa (lento != deadlock).
#     Forziamo il burnout così un run sano termina in fretta; un hang = deadlock.
# ===========================================================================
section "STRESS / DEADLOCK (forced-stop, hang = FAIL)"

for n in 2 5 50 200; do
  # un burnout minuscolo garantisce che la sim si fermi in fretta se lo scheduling funziona
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
