<i>This project has been created as part of the 42 curriculum by teemoteeo.</i>

# Codexion

A concurrency and synchronization challenge: orchestrate multiple coders competing for limited USB dongles using POSIX threads, mutexes, condition variables, and a custom priority-queue scheduler (FIFO / EDF), while preventing deadlocks, starvation, and burnout.

## Description

Codexion simulates coders sitting in a circular co-working hub, sharing USB dongles to compile quantum code. Each coder needs **two dongles** (left and right) to compile. After compiling, they debug, refactor, and then try to compile again — all before their burnout deadline.

The challenge: **no coder should ever burn out**, despite:
- Limited dongles (one between each pair of coders)
- Dongle cooldown periods after release
- No communication between coders
- Two arbitration strategies: FIFO (First In, First Out) and EDF (Earliest Deadline First)

### Concurrency Problems Solved

| Problem | Solution |
|---------|----------|
| **Mutual exclusion** | Each dongle protected by its own `pthread_mutex_t` |
| **Deadlock** (Coffman: hold and wait) | Both dongles are acquired atomically, or neither is |
| **Deadlock** (Coffman: circular wait) | Both mutexes are always locked in increasing dongle index |
| **Starvation** | Per-dongle arbitration queue (FIFO / EDF) decides who goes next |
| **Race conditions** | All shared state mutex-protected; verified with ThreadSanitizer |
| **Precise burnout detection** | Dedicated monitor thread polling every millisecond |
| **Log interleaving** | Serialized output via a single log mutex |

### Architecture

```
        coder 1          coder 2          coder 3
       (thread)         (thread)         (thread)        ...
           │                │                │
   ┌───────┴───────┐┌───────┴───────┐┌───────┴───────┐
   │   dongle 0    ││   dongle 1    ││   dongle 2    │   ... (ring)
   │ ───────────── ││ ───────────── ││ ───────────── │
   │ state mutex   ││ state mutex   ││ state mutex   │
   │ FREE/HELD/CD  ││ FREE/HELD/CD  ││ FREE/HELD/CD  │
   │ ───────────── ││ ───────────── ││ ───────────── │
   │ sched queue   ││ sched queue   ││ sched queue   │
   │ mutex + cond  ││ mutex + cond  ││ mutex + cond  │
   │ FIFO / EDF    ││ FIFO / EDF    ││ FIFO / EDF    │
   └───────────────┘└───────────────┘└───────────────┘

   Coder k queues on its lower-indexed dongle, and takes BOTH its
   dongles in one atomic step — or takes nothing at all and retries.
   It may take a dongle only if nobody is ahead of it in that dongle's
   queue. Past half its burnout time it also queues on the higher
   dongle, so both of them become protected.

   ┌──────────────┐                    ┌──────────────┐
   │   monitor    │  polls every 1 ms  │  log mutex   │
   │   (thread)   │  ───────────────>  │  one write() │
   │   burnout    │                    │  per line    │
   └──────────────┘                    └──────────────┘
```

## Instructions

### Prerequisites

- GCC or Clang with C11 support
- POSIX threads library (`-pthread`)
- `make`

### Compilation

```bash
make
```

### Usage

```bash
./codexion <number_of_coders> <time_to_burnout_ms> <time_to_compile_ms> \
           <time_to_debug_ms> <time_to_refactor_ms> \
           <number_of_compiles_required> <dongle_cooldown_ms> \
           <scheduler>
```

**Arguments:**
- `number_of_coders` — Number of coders (and dongles). Must be ≥ 1.
- `time_to_burnout_ms` — Milliseconds before a coder burns out if not compiling.
- `time_to_compile_ms` — Duration of compilation (holding 2 dongles).
- `time_to_debug_ms` — Duration of debugging phase.
- `time_to_refactor_ms` — Duration of refactoring phase.
- `number_of_compiles_required` — Simulation stops when all coders compile this many times.
- `dongle_cooldown_ms` — Dongle unavailable for this long after release.
- `scheduler` — `fifo` or `edf`.

**Example:**
```bash
./codexion 4 1500 200 200 200 3 100 fifo
```

### Output Format

```
0 1 has taken a dongle
2 1 has taken a dongle
2 1 is compiling
202 1 is debugging
402 1 is refactoring
...
```

Each line: `<timestamp_ms> <coder_id> <message>`

### Clean

```bash
make fclean
```

### Rules

```bash
make        # Build the codexion binary
make all    # Same as make
make clean  # Remove object files
make fclean # Remove binary and objects
make re     # Rebuild from scratch
```

## Thread Synchronization Mechanisms

### Per-Dongle State (Mutex + Condition Variable)

Every dongle owns two independent locks:

- `dongle.mutex` — guards the dongle's own state machine (`FREE`, `HELD`, `COOLDOWN`)
  and its `cooldown_until` timestamp. Held only for the few instructions needed to
  test and flip the state, never across a sleep.
- `dongle.sched.mutex` + `dongle.sched.cond` — guard the arbitration queue of the
  coders waiting for that dongle. Waiting coders sleep on this condition variable,
  *not* on the dongle mutex, so a sleeping coder never blocks a state change.

A coder that is not at the head of the queue calls `pthread_cond_wait` and is woken by a
broadcast when the head changes or when a dongle is released. The predicate (`am I the
queue root?`) is re-tested in a `while` loop on every wake, which also absorbs spurious
wakeups.

### Custom Priority Queue

The subject forbids any standard-library priority queue, so `heap.c` implements a
min-priority queue from scratch, with the minimum kept at index 0:

- **FIFO mode**: key = the timestamp at which the coder started waiting for this cycle
- **EDF mode**: key = `last_compile_start + time_to_burnout` (earliest deadline first)
- **Tie-break**: on equal keys the lower coder ID wins, which makes both policies fully
  deterministic (the subject requires this for EDF)

The backing array is sized to the topology rather than to the coder count. The subject
fixes a ring of N coders and N dongles where dongle `k` sits between coder `k` and coder
`k+1`, so **exactly two coders can ever contend for a given dongle**. The queue therefore
never holds more than two entries, and `heap_push` maintains the min-at-0 invariant with a
single comparison — the sift-up/sift-down loops of a general binary heap would be dead
code here. `heap_remove_by_id` fills the hole with the last entry, which preserves the
invariant at this size.

### Monitor Thread

A dedicated monitor thread runs independently:
- Iterates through all coders once per millisecond
- For each coder, checks if `now - last_compile_start >= time_to_burnout`
- If burnout detected: sets the global stop flag, logs `burned out`, then broadcasts on
  every dongle's condition variable so blocked coders wake up and unwind
- It also stops the simulation once every coder has reached `number_of_compiles_required`

Measured detection latency is around 1 ms, well inside the 10 ms the subject allows.

### Log Serialization

All output goes through a single `log_mutex`. Each line is formatted into a stack buffer
and emitted with **one** `write(2)` call while the mutex is held, so two messages can never
interleave and no allocation happens on the logging path.

`log_state` additionally drops the line if the simulation has already stopped — the check
happens under the same mutex as the write. That is what guarantees `burned out` is the
last line of the run, with no state message slipping in after it.

## Blocking Cases Handled

### Deadlock Prevention

The classic deadlock scenario: Coder 1 holds dongle A and waits for B; Coder 2 holds B and
waits for A. Nobody can move.

**Solution**: a coder never holds one dongle while waiting for the other.
`dongle_try_acquire_pair` locks both dongle mutexes, tests both states, and either marks
*both* as held or leaves *both* untouched. A coder that cannot get the pair walks away
empty-handed and retries from the arbitration queue.

Coffman's four conditions:
1. ✅ **Mutual exclusion** — Required by the problem (a dongle cannot be shared)
2. ❌ **Hold and wait** — Broken: acquisition of the pair is all-or-nothing
3. ✅ **No preemption** — A dongle is never taken away from a coder that holds it
4. ❌ **Circular wait** — Broken: the two mutexes are always locked in increasing dongle index

Breaking either 2 or 4 is enough to make deadlock impossible; this implementation breaks
both. The ordering still matters, though: without it two threads running
`dongle_try_acquire_pair` on overlapping pairs could block each other on the mutexes
themselves.

### Starvation Prevention

Breaking hold-and-wait is the first half. While a coder waits it occupies nothing, so a
neighbour is never blocked by a dongle that is held but idle.

The second half is arbitration, in three layers:

**1. The queue.** Each coder registers on the arbitration queue of its **lower-indexed**
dongle and waits its turn there:

- **FIFO**: the coder that has been waiting since the earlier timestamp goes first
- **EDF**: the coder whose burnout deadline (`last_compile_start + time_to_burnout`) is
  nearest goes first, which is exactly the coder closest to dying

**2. The veto.** A dongle cannot be taken by a coder who is not at the head of that
dongle's queue. Without this, a neighbour could grab a dongle that someone else was already
queued and waiting for, because that dongle is the *higher*-indexed one for the neighbour
and it never queued there.

**3. Escalation.** In a ring of N coders, each queueing on its lower dongle, dongle `N-1`
ends up with no queue at all — it is the higher-indexed dongle for *both* of its
contenders. That gap is exploitable: two coders on either side of a third can alternate on
its two dongles so that the two are never free at the same instant, and the coder in the
middle starves without either neighbour ever doing anything wrong. So a coder that has
burned through **half** of its `time_to_burnout` without compiling also registers on its
higher dongle, and from that moment the veto protects both of its dongles.

Escalation is deliberately reserved for coders that are actually at risk. If every coder
escalated, every coder would veto both neighbours, and on a ring that collapses into a
strict one-at-a-time hand-off — measured, it drops concurrency from 2 to 1 and then
*everybody* burns out. Urgency-triggered escalation keeps the common case parallel and the
starving case protected.

Queue operations are O(1) at this size (see *Custom Priority Queue* above).

**Measured**, 3 runs per configuration, both schedulers, zero burnouts in all of them:

| Parameters | FIFO | EDF |
|---|---|---|
| `N 800 200 200 200` for N = 2, 3, 4, 5, 6, 7 | 0 burnout | 0 burnout |
| `5 700 200 100 100` | 0 burnout | 0 burnout |
| `5 650 200 100 100` | 0 burnout | 0 burnout |

Mutual exclusion was verified by replaying the logs: no two coders sharing a dongle ever
overlap. The only overlaps that appear are exactly 1 ms wide and vanish at a 1 ms
tolerance — that is the millisecond truncation of the printed timestamp, not a real
conflict.

### Cooldown Handling

After release, a dongle enters `DONGLE_COOLDOWN` and records
`cooldown_until = now + dongle_cooldown_ms`. Expiry is **lazy**: there is no timer and no
thread watching the clock. Whenever a coder tests the dongle, the state is refreshed
against the current `gettimeofday()` reading and flips back to `DONGLE_FREE` if the
cooldown has elapsed.

This is precisely why the arbitration queue uses `pthread_cond_timedwait` with a 1 ms
bound rather than a plain `pthread_cond_wait`: a cooldown expiring is a *time* event, so it
fires no broadcast and nobody would ever wake up to notice it.

## Design Decisions

### Why Two Dongles Per Coder?

The two-dongle requirement creates a classic resource-allocation problem: each coder needs two adjacent resources, forcing coordination. With N coders and N dongles in a ring, at most ⌊N/2⌋ coders can compile simultaneously.

### Why acquire both dongles atomically?

The obvious implementation — take the left dongle, then wait for the right one — is exactly
Coffman's hold-and-wait, and it does not merely risk deadlock: it actively starves
neighbours. A coder blocked for 600 ms with one dongle in hand keeps that dongle out of
circulation for 600 ms, and the neighbour who needs it burns out. Taking the pair in one
step under both mutexes removes the failure mode at the root instead of papering over it
with timeouts.

### Why escalate instead of always queueing on both dongles?

Registering on both queues from the start looks like the obvious way to be fair, and it is
fair — but on a ring it is also fatal. A coder is then allowed to move only when it
outranks both of its neighbours, and in a cycle of N totally-ordered coders there is
usually just one such coder at a time. Concurrency drops from 2 to 1, the effective period
becomes N × `time_to_compile`, and every coder misses its deadline. This was measured, not
assumed: `5 800 200 200 200` goes from zero burnouts to burning out on every run.

Escalating only when a coder is halfway to its deadline keeps the fast path parallel and
applies the strong guarantee exactly where it is needed.

### Why pthread_cond_timedwait instead of pthread_cond_wait?

Not for preemption — nothing here is preempted. A dongle coming out of cooldown is a
time-based event that emits no signal, so a coder parked in an unbounded `pthread_cond_wait`
would sleep through it. The 1 ms bound makes the waiter re-check the world periodically.
Every other wake-up path (a release, a stop) *does* broadcast.

### Why a Custom Priority Queue?

The subject explicitly forbids any standard-library priority queue. The implementation is
sized to the ring topology (at most two contenders per dongle) rather than to N, which
keeps push and remove at O(1) and the code auditable. The comparison function is the part
that actually carries the policy: swapping the key switches the whole simulation between
FIFO and EDF.

### Why a Monitor Thread?

Burnout detection must be precise (within 10ms). A separate thread polling at high frequency is simpler and more reliable than embedding detection inside each coder's cycle, which could miss a deadline if the coder is blocked on a mutex.

## Resources

- [POSIX Threads Programming](https://computing.llnl.gov/tutorials/pthreads/) — LLNL pthreads tutorial
- [pthread_mutex_lock(3)](https://man7.org/linux/man-pages/man3/pthread_mutex_lock.3.html) — Mutex man page
- [pthread_cond_wait(3)](https://man7.org/linux/man-pages/man3/pthread_cond_wait.3.html) — Condition variable man page
- [Deadlock and Coffman's Conditions](https://en.wikipedia.org/wiki/Deadlock#Coffman_conditions) — Theory of deadlock prevention
- [Earliest Deadline First Scheduling](https://en.wikipedia.org/wiki/Earliest_deadline_first_scheduling) — EDF theory
- [Priority Queue / Binary Heap](https://en.wikipedia.org/wiki/Binary_heap) — Heap data structure
- [gettimeofday(2)](https://man7.org/linux/man-pages/man2/gettimeofday.2.html) — High-resolution time

### AI Usage

AI was used for:
- Discussing the thread synchronization architecture and reviewing design trade-offs
- Reviewing the priority queue implementation and its sizing argument
- Auditing the project against the subject, which surfaced a starvation bug: coders were
  holding one dongle while waiting for the second, and a neighbour could burn out as a
  result. The fix (atomic pair acquisition, `src/dongle_pair.c`) was designed and verified
  with AI assistance and is documented in *Blocking Cases Handled* above
- Running and interpreting ThreadSanitizer / AddressSanitizer sessions
- Building the parameter matrix used to measure burnout rates across schedulers

Every design decision in this project was reviewed line by line and can be explained
without the tooling that helped find it.
