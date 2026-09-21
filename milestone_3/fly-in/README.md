*This project has been created as part of the 42 curriculum by tcostant.*

# Fly-in

A multi-drone routing simulation that efficiently schedules a fleet of drones from a start hub to an end hub through a graph of connected zones, minimizing total simulation turns while respecting zone capacities, movement costs, and connection constraints.

## Description

Fly-in simulates autonomous drone navigation through a network of zones. Each zone has a type — **normal** (1 turn), **restricted** (2 turns), **priority** (1 turn, preferred), or **blocked** (inaccessible) — and each connection may have a capacity limit. Multiple drones move simultaneously, and the simulation engine resolves conflicts (capacity, collisions, deadlocks) on a turn-by-turn basis.

The goal: route all drones from `start` to `end` in the **fewest possible simulation turns**, respecting all constraints.

### Algorithm Approach

The simulation uses a **turn-based discrete-event engine** backed by a pathfinding algorithm:

1. **Graph parsing**: Reads the custom `.map` format (zones, connections, metadata)
2. **Shortest-path computation**: Weighted graph traversal respecting zone costs; priority zones are preferred despite having the same base cost as normal zones
3. **Multi-drone scheduling**: Distributes drones across disjoint or minimally-overlapping paths to maximize throughput
4. **Turn-by-turn simulation**: Evaluates capacity, connection limits, and in-flight status each tick
5. **Visual representation**: Colored terminal output showing drone positions and zone states

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
- Colored terminal visualization
- Performance scoring (total turns, average turns per drone, path cost)

### Object-Oriented Architecture

Every stage of the pipeline is a class with a single responsibility,
composed together by `FlyInApplication` (`src/__main__.py`):

| Class | File | Responsibility |
|-------|------|-----------------|
| `MapParser` | `src/parser.py` | Line-by-line grammar, metadata validation, and semantic checks (uniqueness, referential integrity) |
| `ZoneGraph` | `src/graph.py` | Adjacency list, per-zone movement cost, and capacity lookups |
| `PathFinder` | `src/pathfinding.py` | Weighted Dijkstra and k-distinct-path search over a `ZoneGraph` |
| `SimulationEngine` | `src/simulation.py` | Turn-by-turn movement, capacity enforcement, and deadlock detection |
| `TerminalVisualizer` | `src/visual.py` | Renders a turn log as colored (or plain) terminal text |
| `SimulationReport` | `src/__main__.py` | Computes the secondary scoring metrics (path cost, avg turns/drone) |
| `FlyInApplication` | `src/__main__.py` | Orchestrates the above and maps failures to the documented exit codes |

`ParserError` is a small custom exception carrying the offending line
number, and `Drone`/`TurnLog` (in `src/simulation.py`) are dataclasses
holding per-drone and per-turn state. No module-level business logic
lives outside a class — the only free functions are the CLI's
`main()`/`_parse_args()`, the conventional thin entry point for a
Python script.

## Instructions

### Prerequisites

- Python 3.10 or later
- `uv` package manager (`pip install uv`)

### Installation

```bash
make install
# or
uv sync
```

### Usage

Run the simulation with a map file:

```bash
make run MAP=maps/easy/01_linear_path.txt
# or
uv run python -m src maps/easy/01_linear_path.txt
```

Run with visual output (colored terminal):

```bash
make run MAP=maps/easy/01_linear_path.txt VISUAL=true
```

### Debug Mode

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

### Linting

```bash
make lint       # flake8 + mypy (standard)
make lint-strict # flake8 + mypy --strict
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

### Multi-Drone Scheduling

Paths are computed independently for each drone in priority order, with the simulation engine resolving conflicts at each turn:

1. Compute shortest paths for all drones
2. At each turn, evaluate which drones can move given:
   - Zone capacity (incoming zone must have room after departures)
   - Connection capacity (link can't exceed `max_link_capacity`)
   - In-flight status (restricted zone transit must complete next turn)
3. Drones that cannot move wait in place
4. Simulation ends when all drones reach the end zone

### Performance Benchmarks

Measured on the maps shipped with the subject, in `maps/`. Every run
exits 0 and every turn log passes an independent adjacency/capacity
replay check.

| Difficulty | Map | Drones | Target (turns) | Result |
|------------|-----|--------|----------------|--------|
| Easy | Linear path | 2 | ≤ 6 | **4** |
| Easy | Simple fork | 4 | ≤ 8 | **4** |
| Easy | Basic capacity | 4 | ≤ 6 | **4** |
| Medium | Dead end trap | 5 | ≤ 12 | **8** |
| Medium | Circular loop | 6 | ≤ 15 | **15** |
| Medium | Priority puzzle | 5 | ≤ 12 | **7** |
| Hard | Maze nightmare | 8 | ≤ 30 | **13** |
| Hard | Capacity hell | 12 | ≤ 35 | **16** |
| Hard | Ultimate challenge | 15 | ≤ 45 | **27** |
| Challenger | The Impossible Dream | 25 | record 45 | **45** |

All nine graded maps meet or beat their target. The optional Challenger
map is solved in 45 turns, which **ties** the reference record rather
than beating it.

## Design Decisions

### Why Turn-Based Simulation?

A turn-based discrete-event model simplifies conflict resolution: at each tick, all drone movements are evaluated simultaneously. Departures free up capacity for arrivals in the same turn, preventing phantom blocking.

### Why Separate Pathfinding from Scheduling?

Shortest paths are computed once per drone (or cached and re-evaluated on capacity changes). The simulation engine handles runtime conflicts — this separation keeps the pathfinding algorithm simple and the scheduling logic focused.

### Why No External Graph Libraries?

The subject explicitly forbids `networkx`, `graphlib`, etc. The entire graph representation and traversal is implemented from scratch using adjacency lists and priority queues, ensuring full control and understanding.

## Visual Representation

`TerminalVisualizer` (`src/visual.py`) renders the turn log produced by
`SimulationEngine` as ANSI-colored terminal text when `--visual` (or
`make run VISUAL=true`) is passed, and as identical but uncolored text
otherwise — the same rendering path is used either way, so `--visual`
never changes *what* is shown, only whether it's colorized.

- Each `D<id>-<destination>` movement token is highlighted in bold blue,
  making it easy to visually track a single drone's progress down a
  turn-by-turn log without reading every token.
- Headers (`=== Fly-in Simulation ===`, the final `Total turns:` line)
  are bolded to separate the simulation trace from the stats block that
  follows it.
- Turns with no drone movement print `(no movement)` instead of an
  empty line, so a reader scanning the log can immediately tell "the
  simulation is waiting on capacity" apart from "a turn was skipped".

This keeps the enhancement lightweight (no extra dependency, works in
any ANSI-capable terminal) while directly answering the subject's ask
for visual feedback of drone positions and zone states over time.

## Challenges

### Restricted Zone Transit

Drones moving to a restricted zone occupy the connection for 2 turns and **must** arrive on the next turn — they cannot wait mid-flight. This required tracking "in-flight" state separately from zone occupancy.

### Deadlock Prevention

When multiple drones converge on a bottleneck (single-capacity zone), they can deadlock. The scheduler detects cycles where all drones are waiting for each other and introduces strategic delays.

### Capacity-Aware Pathfinding

Recomputing paths when capacity fills up adds complexity. The implementation may use path caching with invalidation on capacity changes or dynamic re-routing.

## Testing Strategy

Testing is command-driven rather than a committed test suite — the
subject states test programs are neither submitted nor graded.

**Happy path.** Run every shipped map and check the turn count against
the benchmark table above:

```bash
for m in maps/*/*.txt; do
    echo "$m: $(uv run python -m src "$m" | grep -m1 '^Total turns:')"
done
```

**Rule compliance.** The turn log is independently replayable: re-parse
the map, walk each `D<id>-<zone>` token, and assert every move is between
adjacent zones and that no zone ever holds more than its `max_drones`.
All ten maps pass this replay.

**Error paths.** Each is reproduced by running the binary against a
hand-written malformed map and reading `echo $?`:

| Exit | Meaning | Example trigger |
|------|---------|-----------------|
| 0 | Success | any valid map |
| 1 | Map file not found or not a regular file | missing path, a directory |
| 2 | Parse error or bad CLI usage | see below |
| 3 | No path from start to end | disconnected or fully blocked graph |
| 4 | Simulation could not finish | deadlock, turn cap exceeded |

Parse errors (exit 2), each reported with the offending line number and
cause: missing / duplicate `nb_drones`, `start_hub` or `end_hub`;
`nb_drones` not a positive integer; duplicate zone name; dash in a zone
name; duplicate connection (`a-b` and `b-a`); connection referencing an
undefined zone; invalid zone type; malformed, unknown or duplicated
metadata key; non-positive `max_drones` / `max_link_capacity`;
unrecognised line syntax; unreadable or non-UTF-8 file.

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
- Enumerating and exercising the parser edge cases listed under Testing
  Strategy (error paths, graph costs, pathfinding, simulation turn
  mechanics, CLI exit codes), which surfaced several unhandled inputs
- Generating example map files for testing
- Reviewing code for PEP 8 compliance and mypy type safety
- Structuring the project and README documentation
