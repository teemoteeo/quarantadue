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
| **Mutual exclusion** | Each dongle protected by `pthread_mutex_t` |
| **Deadlock** (Coffman: circular wait) | Ordered dongle acquisition; timeout with EDF |
| **Starvation** | EDF guarantees bounded waiting for feasible parameters |
| **Race conditions** | All shared state (dongles, logs) mutex-protected |
| **Precise burnout detection** | Dedicated monitor thread with `pthread_cond_timedwait` |
| **Log interleaving** | Serialized output via global log mutex |

### Architecture

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Coder 1  │  │ Coder 2  │  │ Coder 3  │  ...
│ (thread) │  │ (thread) │  │ (thread) │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │dongle0      │dongle1      │dongle2
  ┌──┴──────────┬──┴──────────┬──┴──────┐
  │   Dongle    │   Dongle    │ Dongle  │ ... (circular)
  │  (mutex)    │  (mutex)    │ (mutex) │
  └─────────────┴─────────────┴─────────┘
                      │
              ┌───────┴────────┐
              │  Scheduler     │
              │  (FIFO / EDF)  │
              │  priority q    │
              └───────┬────────┘
                      │
              ┌───────┴────────┐
              │  Monitor       │
              │  (burnout)     │
              └────────────────┘
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

Each dongle is protected by:
- `pthread_mutex_t` — guards the dongle's state (available, cooldown, held-by)
- `pthread_cond_t` — coders wait here when the dongle is unavailable

When a coder requests a dongle:
1. Lock the dongle mutex
2. If available → take it, signal waiting coders
3. If in cooldown or held → `pthread_cond_wait`
4. On wake → try to acquire again (spurious wakeup guard)

### Custom Priority Queue

Neither FIFO nor EDF scheduling can use a standard library. A binary min-heap is implemented:
- **FIFO mode**: key = arrival timestamp
- **EDF mode**: key = `last_compile_start + time_to_burnout` (earliest deadline first)

On equal deadlines (EDF), lower coder ID wins.

### Monitor Thread

A dedicated monitor thread runs independently:
- Iterates through all coders at high frequency
- For each coder, checks if `now - last_compile_start >= time_to_burnout`
- If burnout detected: logs within 10ms, sets global stop flag, broadcasts to all condition variables

### Log Serialization

All output lines go through a single `pthread_mutex_t log_mutex`. The `printf` call is protected so no two messages interleave.

## Blocking Cases Handled

### Deadlock Prevention

The classic deadlock scenario: Coder 1 holds dongle A, waits for B; Coder 2 holds B, waits for A.

**Solution**: Coders always try to acquire dongles in a consistent order (lower index first). For EDF mode, a timeout (`pthread_cond_timedwait`) prevents indefinite waiting.

Coffman's four conditions:
1. ✅ **Mutual exclusion** — Required (dongles are exclusive)
2. ✅ **Hold and wait** — Coders hold one dongle while waiting for the second
3. ❌ **No preemption** — Broken: EDF can preempt via timeout
4. ❌ **Circular wait** — Broken: ordered acquisition (lower index first)

### Starvation Prevention

- **FIFO**: Fair by definition — longest-waiting coder gets the dongle
- **EDF**: Serves earliest deadline first; with feasible parameters, no coder starves. The priority queue ensures O(log n) insertion and extraction.

### Cooldown Handling

After release, a dongle enters a cooldown state for `dongle_cooldown_ms`. During cooldown, the dongle reports as unavailable. The monitor tracks cooldown expiry using wall-clock time via `gettimeofday()`.

## Design Decisions

### Why Two Dongles Per Coder?

The two-dongle requirement creates a classic resource-allocation problem: each coder needs two adjacent resources, forcing coordination. With N coders and N dongles in a ring, at most ⌊N/2⌋ coders can compile simultaneously.

### Why pthread_cond_timedwait for EDF?

EDF scheduling requires the ability to time out a waiting coder if a higher-priority coder arrives. `pthread_cond_timedwait` allows a bounded wait, after which the coder re-evaluates its position.

### Why a Custom Priority Queue?

The subject explicitly requires implementing the priority queue (heap) without using any standard library equivalent. This ensures understanding of the underlying data structure.

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
- Designing the thread synchronization architecture
- Implementing the priority queue (heap) data structure
- Debugging race conditions and deadlock scenarios
- Writing the monitor thread's burnout detection logic
- Structuring the Makefile and project layout
- Documenting concurrency patterns and edge cases
