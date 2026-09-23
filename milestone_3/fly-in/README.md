*This project has been created as part of the 42 curriculum by teemoteeo.*

# Fly-in

A multi-drone routing simulation that efficiently schedules a fleet of drones from a start hub to an end hub through a graph of connected zones, minimizing total simulation turns while respecting zone capacities, movement costs, and connection constraints.

## Description

Fly-in simulates autonomous drone navigation through a network of zones. Each zone has a type — **normal** (1 turn), **restricted** (2 turns), **priority** (1 turn, preferred), or **blocked** (inaccessible) — and each connection may have a capacity limit. Multiple drones move simultaneously, and the simulation engine resolves conflicts (capacity, collisions, deadlocks) on a turn-by-turn basis.

The goal: route all drones from `start` to `end` in the **fewest possible simulation turns**, respecting all constraints.

### Algorithm Approach

The simulation uses a **turn-based discrete-event engine** backed by a pathfinding algorithm:

1. **Graph parsing**: Reads the custom `.map` format (zones, connections, metadata)
2. **Shortest-path computation**: Weighted graph traversal respecting zone costs; priority zones are preferred despite having the same base cost as normal zones
3. **Multi-drone scheduling**: Splits the fleet over several candidate routes, scoring each split by actually running the simulation
4. **Turn-by-turn simulation**: Evaluates capacity, connection limits, and in-flight status each tick
5. **Visual representation**: Colored terminal output and an animated terminal UI, both driven by the same turn log

### Zone Types

| Type | Movement Cost | Default Capacity | Notes |
|------|-------------|-----------------|-------|
| `normal` | 1 turn | 1 drone | Default zone type |
| `restricted` | 2 turns | 1 drone | Drone occupies connection during transit; cannot wait mid-flight |
| `priority` | 1 turn | 1 drone | Preferred in pathfinding; same cost as normal |
| `blocked` | ∞ | 0 drones | Inaccessible — paths through it are invalid |

### Key Features

- Custom `.map` file parser with full error reporting (line numbers, cause)
- Weighted shortest-path algorithm (no external graph libraries)
- Multi-drone simultaneous movement with capacity-aware scheduling
- Deadlock detection and strategic waiting
- Two views over one turn log: colored movement log, animated curses TUI
- Performance scoring (total turns, average turns per drone, path cost)

### Object-Oriented Architecture

Every stage of the pipeline is a class with a single responsibility,
composed together by `FlyInApplication` (`src/__main__.py`):

| Class | File | Responsibility |
|-------|------|-----------------|
| `MapParser` | `src/parser.py` | Line-by-line grammar, metadata validation, and semantic checks (uniqueness, referential integrity) |
| `ZoneGraph` | `src/graph.py` | Adjacency list and per-zone movement cost (capacity lives on the parsed map, read directly by the engine) |
| `PathFinder` | `src/pathfinding.py` | Weighted Dijkstra and k-distinct-path search over a `ZoneGraph` |
| `RouteScheduler` | `src/simulation.py` | Decides how many drones take each candidate route, scoring a split by running the engine |
| `SimulationEngine` | `src/simulation.py` | Turn-by-turn movement, capacity enforcement, and deadlock detection |
| `TerminalVisualizer` | `src/visual.py` | Renders a turn log as colored (or plain) terminal text |
| `SimulationFilm` | `src/simulation.py` | Replays a turn log into one drone-position snapshot per turn (pure, display-free) |
| `ZoneLayout` | `src/tui.py` | Places zones and connection glyphs on a character grid (pure, curses-free) |
| `TerminalUI` | `src/tui.py` | Animates the film over that grid with curses |
| `SimulationReport` | `src/__main__.py` | Computes the secondary scoring metrics (path cost, avg turns/drone) |
| `FlyInApplication` | `src/__main__.py` | Orchestrates the above and maps failures to the documented exit codes |

`ParserError` is a small custom exception carrying the offending line
number, and `Drone`/`Movement`/`TurnLog` (in `src/simulation.py`) plus the
models in `src/schemas.py` are stdlib dataclasses holding per-drone,
per-turn and parsed-map state. No module-level business logic lives
outside a class — the only free functions are the CLI's
`main()`/`_parse_args()`, the conventional thin entry point for a
Python script.

The project has no runtime dependencies: the domain models are stdlib
dataclasses, validated by the parser's own grammar rather than by a
validation library re-checking what the grammar already guarantees.

## Instructions

### Prerequisites

- Python 3.10 or later
- `uv` package manager (`pip install uv`)

### Installation

```bash
make install
# or
uv sync --frozen
```

`uv.lock` is committed and `--frozen` refuses to re-resolve it, so every
clone installs the exact same dev toolchain (the project itself has no
runtime dependencies).

### Usage

Run the simulation with a map file (`make run` defaults to
`data/maps/hard/03_ultimate_challenge.txt`, colored):

```bash
make run MAP=data/maps/easy/01_linear_path.txt
# or, uncolored
uv run python -m src data/maps/easy/01_linear_path.txt
```

Colored output is on by default in `make run`; pass `VISUAL_FLAG=` for
plain text, or `--visual` when calling the module directly.

Replay it as an animated terminal UI (curses, works over ssh):

```bash
make tui MAP=data/maps/hard/01_maze_nightmare.txt
# or
uv run python -m src data/maps/hard/01_maze_nightmare.txt --tui
```

Exit codes: `0` success, `1` map file not found, `2` parse error,
`3` no path from start to end, `4` simulation error (deadlock),
`130` interrupted with Ctrl-C.

### Debug Mode

```bash
make debug MAP=data/maps/easy/01_linear_path.txt
```

### Linting

```bash
make lint          # flake8 . + mypy with the subject's flags
make lint-strict   # flake8 . + mypy --strict
```

### Testing

```bash
make test
# or
uv run pytest tests/ -v
```

### Clean

```bash
make clean
```

## Map File Format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: corridorB 2 2 [zone=normal max_drones=1]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-goal [max_link_capacity=2]
```

## Algorithm Details

### Pathfinding Strategy

The core algorithm computes weighted shortest paths using a modified Dijkstra/BFS approach:

- **Normal zones**: cost = 1
- **Restricted zones**: cost = 2 (the drone occupies the connection for 2 turns)
- **Priority zones**: cost = 1 but weighted lower in tie-breaking (preference factor)
- **Blocked zones**: infinite cost (excluded from graph)
- **Capacity constraints**: accounted for at the simulation layer, not the pathfinding layer

### Candidate Routes

`PathFinder.k_shortest_paths` collects up to `nb_drones` distinct routes:

1. the cheapest route (Dijkstra, priority zones nudged 0.01 cheaper so
   they win ties);
2. for each edge of that route, the cheapest route avoiding just that
   edge — detours that share most of the main route;
3. then, repeatedly, the cheapest route avoiding *every* edge found so
   far — edge-disjoint parallel corridors that a one-edge detour never
   reaches.

### Multi-Drone Scheduling

`RouteScheduler` decides how many drones take each route. It does not
*estimate* the cost of a split — it **runs the simulation** to score it.
The engine is the only thing that knows about zone capacity, shared
zones and restricted-zone timing, and a run is cheap.

It starts with every drone on the cheapest route, then moves `step`
drones from one route to another whenever that lowers the score,
halving `step` (from half the fleet down to one) when no move helps.
The score is the total turn count, ties broken by the sum of every
drone's delivery turn. The tie-break matters: with three equal
corridors and the split at `[15, 15, 0]`, moving one drone never lowers
the longest queue, but it does lower the total, and that step is what
leads on to `[10, 10, 10]`.

Starting with big steps keeps it fast: 1000 drones over two routes are
scheduled in under 2 seconds, where moving one drone at a time took 80.

**Execution.**

1. At each turn, drones in flight toward a restricted zone arrive (they
   still count against their connection's capacity that turn).
2. Every other drone tries its next zone, in drone-id order:
   - the zone must have room after this turn's departures;
   - the connection must have room, counting drones still on it;
   - a restricted destination reserves its slot on departure, so the
     drone is guaranteed to land next turn.
3. Drones that cannot move wait in place.
4. A turn in which nothing moves is a deadlock: the state cannot change
   any more, so the engine raises instead of spinning.

### Performance Benchmarks

Every output below is checked by an independent rule validator (zone and
connection capacity per turn, adjacency, 2-turn restricted moves).

| Difficulty | Map | Drones | Target (turns) | Achieved |
|------------|-----|--------|----------------|----------|
| Easy | Linear path | 2 | ≤ 6 | 4 |
| Easy | Simple fork | 4 | ≤ 8 | 5 |
| Easy | Basic capacity | 4 | ≤ 6 | 4 |
| Medium | Dead end trap | 5 | ≤ 12 | 8 |
| Medium | Circular loop | 6 | ≤ 15 | 15 |
| Medium | Priority puzzle | 5 | ≤ 12 | 7 |
| Hard | Maze nightmare | 8 | ≤ 30 | 13 |
| Hard | Capacity hell | 12 | ≤ 35 | 16 |
| Hard | Ultimate challenge | 15 | ≤ 45 | 26 |
| Challenger | The Impossible Dream | 25 | 45 (record) | 66 |

## Design Decisions

### Why Turn-Based Simulation?

A turn-based discrete-event model simplifies conflict resolution: at each tick, all drone movements are evaluated simultaneously. Departures free up capacity for arrivals in the same turn, preventing phantom blocking.

### Why Separate Pathfinding from Scheduling?

Routes are computed once, before the simulation starts, and never recomputed: each drone follows a fixed path and simply waits when its next zone or connection is full. Pathfinding only knows about costs; capacity is handled by the engine and, through it, by the scheduler's scoring. That keeps Dijkstra plain and puts every capacity rule in one place.

### Why No External Graph Libraries?

The subject explicitly forbids `networkx`, `graphlib`, etc. The entire graph representation and traversal is implemented from scratch using adjacency lists and priority queues, ensuring full control and understanding.

## Visual Representation

The subject asks for visual feedback through colored terminal output or a
graphical interface. This project ships two terminal views — a colored
movement log and an animated full-screen UI — both driven by the **same**
`TurnLog` the engine produces, so they can never disagree about what
happened. Staying in the terminal is deliberate: it works over ssh and on
a machine with no Tk installed, which is where this gets demonstrated.

### Terminal (`src/visual.py`, `--visual`)

`TerminalVisualizer` renders the turn log as ANSI-colored text when
`--visual` is passed, and as identical but uncolored text otherwise —
the same rendering path is used either way, so `--visual` never changes
*what* is shown, only whether it's colorized. After a header and a
legend, each turn is one line in exactly the subject's format
(`D1-roof1 D2-corridorA`), followed by a `--- Stats ---` block.

- Each `D<id>-<destination>` token is painted with its **destination
  zone's `color=` metadata**, falling back to a per-zone-type color
  (priority green, restricted red, blocked gray, normal blue) when a
  zone declares none. A turn line therefore shows both who moved and
  what kind of zone they entered, rather than a uniform highlight.
- A legend line names every zone in its own color with a state marker
  (`*` priority, `!` restricted, `x` blocked), so the map's topology is
  readable without opening the `.map` file.

### Terminal UI (`src/tui.py`, `--tui`)

`TerminalUI` draws the whole network on a character grid with `curses` —
zones placed at their `x y` coordinates, connections drawn as stepped
`-`, `|`, `/`, `\` runs between them (the glyph comes from each step,
so a shallow link reads as dashes with a drop rather than a blob of
backslashes) — and animates the drones over it. `curses`
ships with CPython on Unix, so this adds **no** runtime dependency and,
unlike a window, it works over ssh and on a machine with no Tk
installed.

```
                       /--m12--------m13[2]
                 /-----    4         3 \-
  hub-----m1[2]----m10-----m11-----m8!------m9*[2]-\goal
  6 7 8-  5                        |                1 2
            \-m2-------m3!     m6[2]---m7
                       |       |
                       m4------m5*
* priority  ! restricted  x blocked  [N] capacity
Turn 5/11   delivered 2/8   [space] pause  [<-/->] step  [r] replay  [q] quit
```

- Zone labels carry their state marker (`*` priority, `!` restricted,
  `x` blocked) and their `[max_drones]` capacity; start and end hubs are
  drawn in reverse video; each zone takes its `color=`, falling back to
  its zone-type color.
- The drone ids parked in a zone are printed directly beneath it, so a
  queue building at a bottleneck is visible as a growing row of numbers
  rather than something to infer from a log. At the right margin the row
  shifts left to stay on screen — the end hub is the last column and
  collects the whole fleet, so a queue there is wider than the label it
  sits under.
- A drone in transit toward a restricted zone is printed at the midpoint
  of the connection it occupies — the 2-turn cost becomes a position on
  screen instead of a `D3-a-b` token to decode.
- Space pauses, the arrow keys step a turn at a time, `r` replays, `q`
  quits. Stepping *backwards* is what makes a capacity stall
  inspectable. The status bar shows `Turn n/N` and the delivered count.
- Below 60x14 the UI says so instead of drawing garbage; it re-reads the
  terminal size every frame, so resizing mid-replay re-lays-out, and it
  drops the key hints rather than chopping them when the window is too
  narrow for the whole status line.

The shared logic is display-free and therefore unit-tested headlessly:
`SimulationFilm` turns the log into one drone-position snapshot per
turn, and `ZoneLayout` does the coordinate scaling and line-glyph
choice, leaving `TerminalUI` as pure drawing. If the terminal cannot
host the UI (no tty, no `TERM`), the CLI prints a warning and still
exits 0 — the simulation itself already succeeded.

## Challenges

### Restricted Zone Transit

Drones moving to a restricted zone occupy the connection for 2 turns and **must** arrive on the next turn — they cannot wait mid-flight. This required tracking "in-flight" state separately from zone occupancy.

### Deadlock Prevention

Drones never reroute, so if two drones need each other's zone, nothing
can ever move again. The engine detects this on the first turn with no
movement and raises; the scheduler treats a deadlocking split as
infinitely bad and never picks it, so a deadlock only reaches the user
if every candidate split deadlocks.

### Connections in Transit

A drone flying toward a restricted zone occupies its connection until it
lands. Counting it only on the turn it departed let a second drone start
down a capacity-1 connection on the turn the first one landed; the
engine now counts in-flight drones in the arrival turn too.

## Testing Strategy

`tests/` (run via `make test`) covers:

- **Parser tests** (`test_parser.py`): valid maps, all zone types, every
  documented error path (missing declarations, duplicate zones/connections,
  invalid zone type, undefined zone reference, non-positive capacities,
  unrecognised syntax, missing file) and the strict-grammar cases: dashes
  in zone names, a start/end hub reusing a zone name, self-connections,
  unknown/duplicate/malformed metadata, `nb_drones` not first, and the
  line number on a connection to an undefined zone.
- **Graph tests** (`test_graph.py`): per-type movement cost, blocked-zone
  exclusion, priority tie-break.
- **Pathfinding tests** (`test_pathfinding.py`): shortest path on a known
  line graph, no-path detection, k-distinct-path search on a fork, and all
  three of three parallel corridors being found.
- **Simulation tests** (`test_simulation.py`): straight-line turn count,
  capacity-1 corridor queueing without collision, fork-vs-corridor
  throughput, restricted-zone in-flight notation and timing, determinism
  across repeated runs, and a regression test for a fixed bug where a
  restricted zone's capacity wasn't reserved until arrival (letting two
  drones land on a capacity-1 zone on the same turn), a drone in flight
  still occupying its connection, a restricted end zone taking 2 turns,
  and a head-on deadlock raising on the first empty turn.
- **CLI tests** (`test_cli.py`): the exit-code contract (0/1/2/3) end to end.
- **Visualizer tests** (`test_visual.py`): movements painted by the
  destination zone's color, zone-type fallback, in-flight connection
  names resolved to their destination, legend markers, and plain mode
  emitting no ANSI.
- **Scheduler tests** (`test_scheduler.py`): one path per drone, a fork
  split because sharing one branch queues, a small fleet all queueing on
  the short route, a large fleet spilling onto the detour once that queue
  outlasts it, and a guard that the chosen split is never worse than
  piling every drone onto the cheapest route, and 30 drones spreading
  evenly over three parallel corridors (11 turns).
- **Replay tests** (`test_replay.py`): the display-free half of both
  renderers — frame 0 at the start hub, one frame per turn, still drones
  keeping their position, in-flight positions kept as connection names,
  plus zone placement staying inside the screen and clear of the status
  bar, single-row maps not dividing by zero, and the link glyph matching
  the slope.

Beyond the suite, each release is checked against the 10 provided maps
with an independent rule validator (turn counts in the benchmark table
above), a 1000-drone stress run, and the crash-safety inputs the parser
has to survive: a directory, a binary file, an empty file,
`nb_drones: 0`, and a start hub sharing its name with the end hub.

## Resources

- [Dijkstra's Algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm) — Core shortest-path algorithm
- [A* Search Algorithm](https://en.wikipedia.org/wiki/A*_search_algorithm) — Heuristic variant for larger graphs
- [Discrete-Event Simulation](https://en.wikipedia.org/wiki/Discrete-event_simulation) — Turn-based simulation model
- [Graph Theory Fundamentals](https://en.wikipedia.org/wiki/Graph_theory) — Adjacency lists, weighted edges
- [Multi-Agent Pathfinding](https://en.wikipedia.org/wiki/Multi-agent_pathfinding) — Academic research on MAPF problems

### AI Usage

AI was used for:
- Designing the graph data structures and pathfinding algorithm architecture
- Debugging simulation turn mechanics and capacity constraint logic, including
  finding and fixing a real bug where a restricted zone's capacity was only
  reserved on arrival instead of on departure, letting two drones land on a
  capacity-1 restricted zone on the same turn
- Refactoring the parser, pathfinding, and CLI entry point from free functions
  into single-responsibility classes (`MapParser`, `PathFinder`,
  `FlyInApplication`, `SimulationReport`) to satisfy the subject's
  fully-object-oriented requirement
- Writing the `tests/` pytest suite (parser, graph, pathfinding, simulation,
  CLI exit codes) covering the edge cases called out in the subject
- Generating example map files for testing
- Reviewing code for PEP 8 compliance and mypy type safety
- Structuring the project and README documentation
- Auditing the project against the subject: an independent output
  validator that found the in-flight connection-capacity bug, the
  restricted-end-zone bug and the parser's lax grammar, plus the
  scheduler's step-halving search and delivery-turn tie-break
