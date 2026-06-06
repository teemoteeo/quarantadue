# A-MAZE-ING

```
 █████╗  ███╗   ███╗ █████╗ ███████╗███████╗ ██╗███╗   ██╗ ██████╗
██╔══██╗ ████╗ ████║██╔══██╗╚══███╔╝██╔════╝ ██║████╗  ██║██╔════╝
███████║ ██╔████╔██║███████║  ███╔╝ █████╗   ██║██╔██╗ ██║██║  ███╗
██╔══██║ ██║╚██╔╝██║██╔══██║ ███╔╝  ██╔══╝   ██║██║╚██╗██║██║   ██║
██║  ██║ ██║ ╚═╝ ██║██║  ██║███████╗███████╗ ██║██║ ╚████║╚██████╔╝
╚═╝  ╚═╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝
```

*Originally created as part of the 42 curriculum by tcostant & acentron.*

---

## Description

A-MAZE-ING is a terminal maze generator and visualiser written in Python. It reads a plain-text config file, generates a maze using one of three carving algorithms (DFS, Prim, or Kruskal), solves it with bidirectional BFS, and renders it in a full `curses` TUI with threaded animations.

The interface is split into three panels — a keybind menu on the left, the maze in the centre, and a live info panel on the right. All settings (algorithm, dimensions, entry/exit, seed, perfect mode, colours) are editable at runtime without restarting.

A standalone pip-installable package (`mazegen`) ships alongside the main project. It exposes a clean `MazeGenerator` class usable in any Python project without pulling in the TUI.


## Instructions

```bash
make install        # pip install -r requirements.txt
make run            # python3 a_maze_ing.py config.txt
make debug          # pdb session
make lint           # flake8 + mypy (strict)
make test           # pytest tests/
make clean          # remove __pycache__, .mypy_cache, *.pyc
make package        # build mazegen wheel + tarball
```


## Config file format

`KEY=VALUE` format. Lines starting with `#` and blank lines are ignored. `SEED` and `ALGORITHM` are optional.

```
# Example config.txt
WIDTH=20
HEIGHT=20
ENTRY=0,0
EXIT=19,19
OUTPUT_FILE=maze.txt
PERFECT=TRUE
SEED=
ALGORITHM=DFS
```

### Keys

| Key           | Type                        | Description                                                    |
|---------------|-----------------------------|----------------------------------------------------------------|
| `WIDTH`       | int > 0                     | Maze width in cells                                            |
| `HEIGHT`      | int > 0                     | Maze height in cells                                           |
| `ENTRY`       | `x,y`                       | Entry cell (zero-indexed, inside grid)                         |
| `EXIT`        | `x,y`                       | Exit cell (zero-indexed, inside grid, ≠ ENTRY)                 |
| `OUTPUT_FILE` | string                      | Path written after each generation                             |
| `PERFECT`     | `TRUE` / `FALSE`            | `TRUE` → single path; `FALSE` → ~15% extra walls removed      |
| `SEED`        | int or empty                | Optional RNG seed for reproducible mazes                       |
| `ALGORITHM`   | `DFS` / `PRIM` / `KRUSKAL` | Carving algorithm (default: `DFS`)                             |

### Validation rules

- `WIDTH` and `HEIGHT` must be > 0.
- `ENTRY` and `EXIT` must be inside the grid and must differ.
- An invalid algorithm string raises `ValueError` at parse time.
- Malformed lines (no `=`) raise `ValueError` with the line number.


## TUI layout

```
┌─ MENU (left) ──────────┬─── MAZE (centre) ───┬─── INFO (right) ──┐
│  [R] REGEN             │                      │  Algorithm: DFS   │
│  [S] SETUP             │   actual maze here   │  Perfect:   YES   │
│  [P] PATH              │                      │  Size:  20 × 20   │
│  [C] COLOR             │                      │  Seed:  —         │
│  [Q] QUIT              │                      │                   │
└────────────────────────┴──────────────────────┴───────────────────┘
```

The maze panel is centred in the available space and reflows on terminal resize.


## Keybindings

| Key              | Action                                      |
|------------------|---------------------------------------------|
| `R`              | Regenerate maze with current config         |
| `S`              | Open Setup form                             |
| `P`              | Run / toggle bidirectional BFS animation    |
| `C`              | Open Color picker                           |
| `Q` / `ESC`      | Quit                                        |
| `↑` / `k`        | Move menu selection up                      |
| `↓` / `j`        | Move menu selection down                    |
| `ENTER`          | Confirm selected menu item                  |

### Setup form (`S`)

Editable fields with keyboard navigation (`↑↓` to move, `←→` / `Space` to toggle enums/booleans, digits to type integers, `Backspace` to delete):

| Field       | Type   | Notes                                      |
|-------------|--------|--------------------------------------------|
| Algorithm   | enum   | `DFS` · `PRIM` · `KRUSKAL`                 |
| Perfect     | bool   | YES / NO                                   |
| Width       | int    | min 1                                      |
| Height      | int    | min 1                                      |
| Entry X/Y   | int    | validated against grid bounds and 42 pattern |
| Exit X/Y    | int    | same                                       |
| Seed        | int    | leave empty for random                     |

`ENTER` applies and regenerates. `ESC` cancels.

### Color picker (`C`)

Two independently configurable colour schemes — wall colour and 42-pattern colour. `↑↓` switches between sections, `←→` cycles through palettes, digit keys (`1`–`6`) jump directly. Changes are previewed live on the maze; `ENTER` keeps them, `ESC` reverts.

Available palettes: Green · Yellow · Red · Blue · White · Cyan.


## Animations

Two background threads drive animations independently of the input loop:

**Carve animation** — triggered on every regeneration. Replays `carve_steps` (wall removals during generation) followed by `knock_steps` (non-perfect extra removals) at ~32 µs per step.

**Solve animation** — triggered by `P`. Runs bidirectional BFS and streams the expanding frontiers layer by layer: cyan from entry (`A`), magenta from goal (`B`). Once the frontiers meet, the shortest path is drawn in yellow with box-drawing connectors (`─`, `│`, `╭`, `╮`, `╰`, `╯`) and a `♘` at the exit.

Both animations can be interrupted at any time (e.g. by pressing `R` to regenerate).


## Output file format

Written to `OUTPUT_FILE` after every generation.

```
<WIDTH hex digits per row>   ← HEIGHT rows
                             ← blank line
<entry_x>,<entry_y>
<exit_x>,<exit_y>
<path>
```

- **Grid rows:** one uppercase hex digit per cell, top-to-bottom.
- **Cell encoding:** 4-bit nibble. Each bit is a closed wall: `N=bit0 (1)`, `E=bit1 (2)`, `S=bit2 (4)`, `W=bit3 (8)`. `0xF` = all walls closed. `0x0` = all open.
- **Path:** consecutive `N`/`E`/`S`/`W` letters (shortest path via BFS). Empty if no path exists.

### Example — 5 × 4 maze

```
9554C
3CD45
9645C
3EDE6

0,0
4,3
EESSESS
```

`9` = `0b1001` = N + W closed (top-left corner). `6` = `0b0110` = E + S closed.


## Cell encoding reference

| Bit | Value | Wall  |
|-----|-------|-------|
|  0  |   1   | North |
|  1  |   2   | East  |
|  2  |   4   | South |
|  3  |   8   | West  |


## Maze generation algorithms

### DFS (default)

Randomised iterative depth-first search ("recursive backtracker"). Produces mazes with long winding corridors and a single pronounced solution path. The iterative stack-based implementation avoids Python's recursion limit on large grids.

### Prim

Maintains a frontier of candidate walls between visited and unvisited cells. At each step a random wall is picked; if the unvisited side is still unvisited the wall is carved. Produces bushier mazes with more branches and shorter average dead-ends.

### Kruskal

Builds the complete list of internal edges, shuffles it, then walks the list with a Union-Find structure (path compression + union by rank). An edge is carved when its two endpoints are in different components. Results in a statistically uniform spanning tree — passages distributed more evenly across the grid.

### Non-perfect mode (`PERFECT=FALSE`)

After the spanning-tree carve, ~15% of the remaining internal walls (excluding border walls and walls adjacent to the "42" pattern) are randomly removed, introducing cycles.

### "42" pattern

When the maze is at least 11 × 11 cells, a "42" silhouette is embedded at centre before carving. Pattern cells are pre-marked visited so every algorithm skips them, leaving them as solid walls. The pattern is skipped if it would overlap entry or exit, or if the maze is too small.

### `trextre` post-pass

After carving, the generator scans all 3 × 3 blocks for fully-open areas (all 12 internal passages present). Any such block has one wall re-added between the centre cell and its southern neighbour. This prevents statistically unlikely but possible large open regions that break the maze aesthetic.


## Solver

`MazeSolver` in `solver.py` exposes three methods:

- `bfs(start, goal)` — monodirectional BFS, returns `list[(x, y)]`.
- `bfs_bidir(start, goal)` — bidirectional BFS, returns `(path, steps_log)` where each log entry is `(side, cell, parent)`.
- `bfs_bidir_layers(start, goal)` — same but groups expansion steps into BFS wavefront layers, used by the solve animation.

`MazeSolver` depends only on `generator.grid`, `width`, and `height` — it works with any object exposing those three attributes.


## Reusable components

### `mazegen` standalone package

Self-contained, zero-dependency module installable as a pip package:

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

```python
from mazegen import MazeGenerator

maze = MazeGenerator(
    width=20, height=15,
    entry=(0, 0), exit=(19, 14),
    seed=42,
)
print(maze.grid)      # list[list[int]]  — grid[y][x], nibble per cell
print(maze.solution)  # 'SESESEESSE...'  — N/E/S/W letters
maze.write_output('maze.txt')
maze.print_ascii()
```

Uses only the standard library (`random`, `collections`, `sys`). DFS generation + BFS solving. Entirely independent from the main project's modules.

### `generator.MazeGenerator`

Main generator, config-driven:

```python
from maze_parser import parse_input
from generator import MazeGenerator

config = parse_input("config.txt")
maze = MazeGenerator(config)
print(maze.grid)
maze.write_output("out.txt")
```

`carve_steps` and `knock_steps` are public lists of wall-removal events replayable by any renderer.

### `solver.MazeSolver`

```python
from solver import MazeSolver

solver = MazeSolver(maze)
path = solver.bfs(maze.entry, maze.exit)           # list[(x, y)]
path, log = solver.bfs_bidir(maze.entry, maze.exit)
path, layers = solver.bfs_bidir_layers(maze.entry, maze.exit)
```

### `maze_parser.MazeConfig` + `parse_input`

`parse_input` returns a validated `MazeConfig` from any `KEY=VALUE` text file. Both can be reused to add new frontends (web API, GUI) without touching generation logic.


## Project structure

```
a_maze_ing.py      Entry point — argument parsing, wires config → Visualinho
generator.py       MazeGenerator: DFS / Prim / Kruskal + "42" pattern
                   + non-perfect mode + trextre post-pass
maze_parser.py     parse_input() + MazeConfig (config file → validated object)
solver.py          MazeSolver: BFS, bidirectional BFS, layer-grouped BFS
visual.py          Visualinho: curses TUI, threaded carve + solve animations,
                   setup form, color picker, live info panel, resize handling
user.py            Thin entry point: wires parse_input → MazeGenerator → Visualinho
mazegen.py         Standalone pip package (DFS + BFS, zero dependencies)
config.txt         Default config file
maze.txt           Last generated output (overwritten on each run)
pyproject.toml     Build metadata for the mazegen wheel
requirements.txt   Dev dependencies (flake8, mypy, pytest, build)
Makefile           Convenience targets: install / run / lint / test / package
```


## Resources

- [Maze generation algorithms — Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Recursive backtracker (DFS) — jamisbuck.org](http://weblog.jamisbuck.org/2010/12/27/maze-generation-recursive-backtracker)
- [Prim's algorithm — jamisbuck.org](http://weblog.jamisbuck.org/2011/1/10/maze-generation-prim-s-algorithm)
- [Kruskal's algorithm — jamisbuck.org](http://weblog.jamisbuck.org/2011/1/3/maze-generation-kruskal-s-algorithm)
- [Disjoint Set Union (Union-Find) — cp-algorithms.com](https://cp-algorithms.com/data_structures/disjoint_set_union.html)
- [BFS — cp-algorithms.com](https://cp-algorithms.com/graph/bfs.html)
- [ANSI escape codes — Wikipedia](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [Python packaging tutorial — packaging.python.org](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
