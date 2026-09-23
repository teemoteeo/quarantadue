*This project has been created as part of the 42 curriculum by teemoteeo.*

# Fly-in

A multi-drone routing simulation that efficiently schedules a fleet of drones from a start hub to an end hub through a graph of connected zones, minimizing total simulation turns while respecting zone capacities, movement costs, and connection constraints.

## Description

Fly-in simulates autonomous drone navigation through a network of zones. Each zone has a type — **normal** (1 turn), **restricted** (2 turns), **priority** (1 turn, preferred), or **blocked** (inaccessible) — and each connection may have a capacity limit. Multiple drones move simultaneously: a planner routes each drone through time around the others, and the simulation engine replays those plans turn by turn, enforcing every capacity and movement rule.

The goal: route all drones from `start` to `end` in the **fewest possible simulation turns**, respecting all constraints.

### Algorithm Approach

The simulation uses a **turn-based discrete-event engine** backed by a pathfinding algorithm:

1. **Graph parsing**: Reads the custom `.map` format (zones, connections, metadata)
2. **Shortest-path computation**: Weighted graph traversal respecting zone costs; priority zones are preferred despite having the same base cost as normal zones
3. **Multi-drone planning**: Plans drones one at a time in (zone, turn) space around the slots earlier drones reserved, so the fleet spreads over every useful route and waits only when it must
4. **Turn-by-turn simulation**: Replays the plans and checks capacity, connection limits, and in-flight rules each turn
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
- Strategic waiting and conflict-free scheduling by construction
- Two views over one turn log: colored movement log, animated curses TUI
- Performance scoring (total turns, average turns per drone, path cost)

### Object-Oriented Architecture

Every stage of the pipeline is a class with a single responsibility,
composed together by `FlyInApplication` (`src/__main__.py`):

| Class | File | Responsibility |
|-------|------|-----------------|
| `MapParser` | `src/parser.py` | Line-by-line grammar, metadata validation, and semantic checks (uniqueness, referential integrity) |
| `ZoneGraph` | `src/graph.py` | Adjacency list and per-zone movement cost (capacity lives on the parsed map, read directly by the engine) |
| `PathFinder` | `src/pathfinding.py` | Capacity-blind Dijkstra distances to the end (the planner's heuristic) and path costs |
| `FlightPlanner` | `src/pathfinding.py` | Cooperative A*: plans every drone through (zone, turn) space with a shared reservation table |
| `SimulationEngine` | `src/simulation.py` | Replays the plans turn by turn and enforces every movement and capacity rule |
| `TerminalVisualizer` | `src/visual.py` | Renders a turn log as colored (or plain) terminal text |
| `SimulationFilm` | `src/simulation.py` | Replays a turn log into one drone-position snapshot per turn (pure, display-free) |
| `ZoneLayout` | `src/tui.py` | Places zones on a rank-compressed character grid and fits their labels (pure, curses-free) |
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
`data/maps/hard/01_maze_nightmare.txt`, colored):

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
`3` no path from start to end, `4` simulation error (a rule broken),
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

### Costs

Entering a zone costs its movement cost: **normal** 1 turn,
**restricted** 2 turns (the drone holds the connection for both and must
land on the second), **priority** 1 turn but counted as 0.99 so it wins
ties, **blocked** can never be entered.

### Cooperative planning through time (`FlightPlanner`)

A fixed route per drone can't express "go left while the right branch
is busy, then cross over". So the planner doesn't pick routes; it plans
each drone in **(zone, turn)** space:

1. A shared **reservation table** records, for every turn, how many
   drones each zone holds after the turn and how many are on each
   connection during it.
2. Drones are planned one after another. From `(start, 0)`, a drone can
   **wait** (same zone, next turn, if the zone keeps a free slot), **step**
   into a neighbour (connection and zone both have room next turn), or
   **start a transit** into a restricted neighbour (connection free for
   two turns, zone free on landing).
3. **A\*** finds the earliest arrival at the end. The heuristic is the
   capacity-blind Dijkstra distance to the end (`PathFinder.distances_to`,
   one reverse Dijkstra for the whole map), which never overestimates,
   so the first arrival found is the earliest possible given the earlier
   drones.
4. The chosen plan's slots are reserved, and the next drone plans around
   them.

Spreading the fleet over routes, strategic waiting and avoiding
conflicts are not separate steps: they all come out of the same search.
When the short route is busy, the next drone's earliest arrival may go
through a detour, or it may wait at the start; A\* compares both on the
same turn count. Waiting at the start is always allowed, so every drone
gets a plan.

**Complexity.** Each drone's search explores at most `Z × T` states (`Z`
zones, `T` turns until it lands) with `O(deg)` successors each, and the
heuristic keeps it close to the best path. The whole fleet costs
`O(D × Z × T × log)` in the worst case, and memory is the reservation
table (`O(Z × T)`) plus one search at a time. Nothing is recomputed:
each drone is planned once. In practice, 1000 drones plan in about 0.2 s.

**Limits.** Planning order is fixed (drone 1 first) and earlier plans
never change, so this is greedy across drones. On the provided maps it
matches the lower bound set by each map's bottleneck (for example,
`maze_nightmare` funnels every drone through the capacity-1 connection
`maze_c2-bottleneck`, so 13 is the minimum).

### Execution (`SimulationEngine`)

The engine replays the plans one turn at a time and checks every rule of
the subject on each turn:

1. A move follows a connection and never enters a blocked zone.
2. A restricted zone is entered only through a transit (`D1-a-b`), and
   the drone lands on the very next turn.
3. Drones on each connection during the turn (including those landing),
   and in each zone after it (start and end excepted), stay within
   capacity. Occupancy is counted after all moves, so a drone leaving a
   zone frees its slot for another entering on the same turn.

The planner is built never to break these rules; the engine is the proof,
and it raises (exit code 4) instead of printing an invalid log.

### Performance Benchmarks

Every output below is checked by an independent rule validator (zone and
connection capacity per turn, adjacency, 2-turn restricted moves).

| Difficulty | Map | Drones | Target (turns) | Achieved |
|------------|-----|--------|----------------|----------|
| Easy | Linear path | 2 | ≤ 6 | 4 |
| Easy | Simple fork | 4 | ≤ 8 | 4 |
| Easy | Basic capacity | 4 | ≤ 6 | 4 |
| Medium | Dead end trap | 5 | ≤ 12 | 8 |
| Medium | Circular loop | 6 | ≤ 15 | 15 |
| Medium | Priority puzzle | 5 | ≤ 12 | 7 |
| Hard | Maze nightmare | 8 | ≤ 30 | 13 |
| Hard | Capacity hell | 12 | ≤ 35 | 16 |
| Hard | Ultimate challenge | 15 | ≤ 45 | 26 |
| Challenger | The Impossible Dream | 25 | 45 (record) | **43** |

## Design Decisions

### Why Turn-Based Simulation?

A turn-based discrete-event model simplifies conflict resolution: at each tick, all drone movements are evaluated simultaneously. Departures free up capacity for arrivals in the same turn, preventing phantom blocking.

### Why Plan First, Then Simulate?

The planner decides and the engine checks. Keeping them apart means the rules exist in the engine as plain checks you can read turn by turn, independent of how clever the planner is. A bug in the planner surfaces as a clear rule violation instead of an invalid log. It also replaced an earlier design, a fixed list of candidate routes plus a scheduler choosing how many drones take each one. That design could not mix route segments, and it scored 66 turns on the challenger map where the planner scores 43.

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

`TerminalUI` draws the whole network with `curses` and animates every
drone along the connections it takes. `curses` ships with CPython on
Unix, so this adds **no** runtime dependency, and it works over ssh.

Mid-turn on `capacity_hell`: the fleet spreads over the gates, the
waiting areas and the priority bypass (moving drones are highlighted
yellow on screen, full zones get a red frame):

```
      ┌start─┐
      │1 left│
      └──────┘----
             \ \--\---
              \-  \-- \---9
                \-   11--  \----
                  \      \--    \---
                 ┌gate1─┐   ┌gate2─┐\--┌gate3─┐   ┌res…1!┐   ┌res…2!┐   ┌res…3!┐   ┌conve…┐   ┌final…┐   ┌goal──┐
                 │  □   │---│  □   │---│  □   │---│  □□  │---│  □□  │---│  □□  │---│□□□□□□│-1-│ □□□  │---│ 0 in │
                 └──────┘   └──────┘   └──────┘   └──────┘   └──────┘   └──────┘---└──────┘   └──────┘   └──────┘
                     |          |          |                            /-----    /-
                     |          |          |                     /------       /--
                     10         8          6               /----3            /-
                     |          |          |         /-----                /-
                 ┌wait…1┐   ┌wait…2┐   ┌wait…3┐/-----                   /--
                 │ □□□□ │---│ □□□□ │---│ □□□□ │                       /2
                 └──────┘-  └──────┘-  └──────┘                    /--
                          \--        \--                         /-
                             \--        \--                    /-
                                7---       5---             /--
                                    \--        \--        /-
                                       ┌pri…1*┐   ┌pri…2*┐
                                       │ □□□  │-4-│ □□□  │
                                       └──────┘   └──────┘
```

- **Zones are boxes.** Each zone is a small frame with its name set in
  the top border and its drones inside, so a name never covers a route.
  Connections run between box centres and stop at the borders, and a
  third of every column is kept free between boxes so drones have room
  to travel.
- **Every drone, by number, in motion.** Playback runs on a continuous
  clock, so between two turns each moving drone slides along its
  connection from one zone to the next, drawn as its own number and
  highlighted. A transit toward a restricted zone stops halfway down the
  connection after its first turn (shown in magenta) and lands on the
  second, so the 2-turn cost is visible as motion.
- **Readable layout.** Zones keep the order of their `x y` coordinates,
  but each distinct `x` gets an equal-width column (rank compression),
  so boxes never overlap however the coordinates are spread. A name too
  long for its box is shortened but keeps its trailing digits
  (`conv_restricted7!` becomes `conv_…7!`), since the digits are what
  tell sibling zones apart. A wider terminal shows longer names.
- **Who is where.** Inside each box, the numbers of the drones in it,
  followed by a `□` per free slot. The drones that just arrived are
  yellow; a full zone gets a red frame and red numbers, so bottlenecks
  stand out.
  When the numbers don't fit the column, `3/8` is shown instead. The
  start shows how many drones are left, the end how many are in.
- **Traffic on the connections.** A connection is drawn bright yellow
  while a drone is on it this turn, normally if the plan uses it at any
  point, and dim if no drone ever takes it. A glance shows which routes
  the fleet is spread over.
- **Side panel with full names.** Fleet totals, every move of the
  current turn (`D3 slow_path1 → slow_path2`, `(2 turns)` for a
  transit), and the busy zones sorted fullest first. The panel hides
  itself when the map needs the width; `p` toggles it.
- **Controls.** Space plays or pauses (at the end, it replays). The
  arrow keys play exactly one turn forward or backward, so you can watch
  a single turn's moves as often as you like. `+`/`-` change the speed
  (150 ms to 2.5 s per turn), `r` restarts and `q` quits (not Esc: an
  arrow key starts with an Esc byte, and a slow link could split it).
  The header
  shows the turn, a delivered progress bar and the speed.
- **Any terminal size.** The size is re-read every frame, so resizing
  re-lays the map out. Below the minimum size (8 columns per zone
  column, so about 170 columns for the challenger map) the UI says how
  much room it needs instead of drawing garbage. Non-UTF-8 terminals get ASCII
  glyphs.

Layout and replay are display-free and unit-tested headlessly
(`ZoneLayout`, `SimulationFilm`), and every frame of every provided map
is rendered in tests at three terminal sizes through a fake screen. If
the terminal cannot host the UI (no tty, no `TERM`), the CLI prints a
warning and still exits 0, since the simulation itself already succeeded.

## Challenges

### Restricted Zone Transit

Drones moving to a restricted zone occupy the connection for 2 turns and **must** arrive on the next turn — they cannot wait mid-flight. This required tracking "in-flight" state separately from zone occupancy.

### Deadlock Prevention

Deadlocks cannot happen by construction: each drone's plan is built
around every slot already reserved, and waiting at the start is always
legal, so a drone never commits to a move that another drone's plan
blocks. The engine would still catch a broken plan as a rule violation.

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
- **Pathfinding tests** (`test_pathfinding.py`): reverse-Dijkstra
  distances charging the zone being entered (restricted = 2),
  unreachable zones, per-path cost.
- **Simulation tests** (`test_simulation.py`): straight-line turn count,
  capacity-1 corridor queueing without collision, fork-vs-corridor
  throughput, restricted-zone in-flight notation and timing, determinism,
  a drone in flight still occupying its connection, a restricted end zone
  taking 2 turns, and the engine rejecting hand-written illegal plans one
  rule at a time (connection and zone over capacity, non-adjacent move,
  entering a blocked zone, entering a restricted zone without transit,
  waiting mid-flight, not ending at the end), while accepting a drone
  entering a zone on the same turn another leaves it.
- **CLI tests** (`test_cli.py`): the exit-code contract (0/1/2/3) end to end.
- **Visualizer tests** (`test_visual.py`): movements painted by the
  destination zone's color, zone-type fallback, in-flight connection
  names resolved to their destination, legend markers, and plain mode
  emitting no ANSI.
- **Planner tests** (`test_planner.py`): no-path error, one start-to-end
  timeline per drone, a fork split because sharing one branch queues, a
  small fleet all queueing on the short route, a large fleet spilling
  onto the detour, 30 drones spreading evenly over three parallel
  corridors (11 turns), priority zones winning ties, and a drone waiting
  at the start rather than landing on a full restricted zone.
- **Replay and layout tests** (`test_replay.py`): frame 0 at the start
  hub, one frame per turn, in-flight positions kept as connection names,
  zones placed inside the box by coordinate rank, labels never
  overlapping on a row, long labels keeping digits and marker, and link
  glyphs matching the slope.
- **TUI tests** (`test_tui.py`): every quarter-turn of every provided
  map drawn through a fake screen at 60x16, 100x30 and 220x60 (catching
  drones mid-glide and mid-transit), a moving drone advancing along its
  connection and leaving it on landing, a transit stopping at the
  midpoint then landing, zones listing their drones by number, the right
  arrow playing exactly one turn, the delivered count, full zone names
  in the move list, the panel toggle, and the quit key.

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
- David Silver, [Cooperative Pathfinding](https://ojs.aaai.org/index.php/AIIDE/article/view/18726) (AIIDE 2005) — Cooperative A* with a space-time reservation table, the basis of `FlightPlanner`

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
  restricted-end-zone bug and the parser's lax grammar
- Replacing the route scheduler with the cooperative space-time planner
  (`FlightPlanner`), turning the engine into a rule-checking replay, and
  redesigning the curses UI (rank-compressed layout, zones as boxes,
  traffic-colored connections, side panel)
