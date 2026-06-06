#!/usr/bin/env python3

import random
import sys
from collections import deque
from maze_parser import MazeConfig

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

DIRECTIONS = [
    (0, -1, NORTH, SOUTH),
    (1,  0, EAST,  WEST),
    (0,  1, SOUTH, NORTH),
    (-1, 0, WEST,  EAST),
]

# (cx, cy, dx, dy, wall_in_current, wall_in_neighbor)
Wall = tuple[int, int, int, int, int, int]
Cell = tuple[int, int]

# Percentuale di walls abbattute per maze non perfetto
_NON_PERFECT_KNOCK_RATIO = 0.15


# ── "42" pattern ──────────────────────────────────────────────────────────
#   "4"          "2"
#   X . .        X X X
#   X . X        . . X   ← (dx 0-2 = "4", dx 4-6 = "2", gap col 3)
#   X X X        X X X
#   . . X        X . .
#   . . X        X X X
#
_PATTERN_4: frozenset[tuple[int, int]] = frozenset([
    (0, 0),
    (0, 1), (2, 1),
    (0, 2), (1, 2), (2, 2),
    (2, 3),
    (2, 4),
])

_PATTERN_2: frozenset[tuple[int, int]] = frozenset([
    (0, 0), (1, 0), (2, 0),
    (2, 1),
    (0, 2), (1, 2), (2, 2),
    (0, 3),
    (0, 4), (1, 4), (2, 4),
])

# Gap fra 4 e 2 nel pattern 42 centrale
_PATTERN_GAP = 1
# Larghezza delle cifre del pattern 42 centrale
_DIGIT_W = 3
# Larghezza totale pattern 42 = 4_box + gap + 2_box
_PATTERN_W = _DIGIT_W + _PATTERN_GAP + _DIGIT_W   # 7
_PATTERN_H = 5

# Misura minima del maze per avere pattern 42 nel mezzo
_PATTERN_MIN_W = _PATTERN_W + 4   # 11
_PATTERN_MIN_H = _PATTERN_H + 6   # 11


class MazeGenerator:
    """Genera una griglia maze partendo da una classe: `MazeConfig`.

    La griglia e' una lista 2D di int - un mezzo byte (detto nibble)
    per cella definisce lo stato della cella e quali mura sono aperte
    o chiuse (bit 0=N, 1=E, 2=S, 3=W).

    Per creare il maze e fare il cosiddetto "carving" vengono usati 3
    possibili algoritmi: DFS, Prim o Kruskal.

    Quando `config.perfect` e' False, il 15% delle mura ancora chiuse
    viene aperto per creare piu' possibili path.

    Attributi:
        width: Larghezza in celle.
        height: Altezza in celle.
        entry: ``(x, y)`` coordinate dell'entrata.
        exit: ``(x, y)`` coordinate dell'uscita.
        grid: lista 2D ``grid[y][x]`` di int che descivono lo stato
              della cella.
    """

    def __init__(self, config: MazeConfig) -> None:
        """costruisci il maze da config ``config``.

        Args:
            config: Configurazione gia' validata che descrive
                    dimensioni, entry/exit, output file, perfect
                    flag, seed opzionale, algoritmo di carving e
                    presenza 42 pattern.
        """
        self.width = config.width
        self.height = config.height
        self.algorithm = config.algorithm
        self.entry = config.entry
        self.exit = config.exit
        self.perfect = config.perfect
        self.grid = [[15] * self.width for _ in range(self.height)]
        self._visited = [[False] * self.width for _ in range(self.height)]
        self.carve_steps: list[tuple[int, int, int, int, int, int]] = []
        self.knock_steps: list[tuple[int, int, int, int, int, int]] = []
        self._pattern_cells: set[tuple[int, int]] = set()
        if getattr(config, "place_42", True):
            self._place_42_pattern()
        if config.seed is not None:
            random.seed(config.seed)

        # print("ALGORITHM USED:", config.algorithm)

        ex, ey = self.entry
        algo = config.algorithm.upper()
        if algo == "PRIM":
            self._prim(ex, ey)
        elif algo == "KRUSKAL":
            self._kruskal()
        else:
            self._dfs(ex, ey)
        if not self.perfect:
            self._knock_down_walls()

        self.trextre()

    def _is_valid(self, x: int, y: int) -> bool:
        """Ritorna ``True`` se ``(x, y)`` e' all'interno della griglia."""
        return 0 <= x < self.width and 0 <= y < self.height

    def _dfs(self, x: int, y: int) -> None:
        """Rimuove mura in base a Depth-First Search algorithm.

        Cambia ``self.grid`` abbattendo le mura tra celle adiacenti
        segnate come 'visited'.

        Args:
            x: Colonna di inizio.
            y: Riga di inizio.
        """
        stack = [(x, y)]
        while stack:
            cx, cy = stack[-1]
            if not self._visited[cy][cx]:
                self._visited[cy][cx] = True
            dirs = list(DIRECTIONS)
            random.shuffle(dirs)
            moved = False
            for dx, dy, wall_here, wall_opposite in dirs:
                nx, ny = cx + dx, cy + dy
                if self._is_valid(nx, ny) and not self._visited[ny][nx]:
                    self.grid[cy][cx] &= ~(1 << wall_here)
                    self.grid[ny][nx] &= ~(1 << wall_opposite)
                    self.carve_steps.append(
                        (cy, cx, wall_here, ny, nx, wall_opposite)
                    )
                    self._visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    def _add_frontier_walls(
        self, x: int, y: int, frontier: list[Wall]
    ) -> None:
        """Append walls of cell ``(x, y)`` whose neighbour is unvisited.

        Pattern cells are pre-marked visited so they are skipped here.

        Args:
            x: Column of the visited cell.
            y: Row of the visited cell.
            frontier: List of candidate walls to extend.
        """
        for dx, dy, wh, wo in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if (
                self._is_valid(nx, ny)
                and not self._visited[ny][nx]
            ):
                frontier.append((x, y, dx, dy, wh, wo))

    def _prim(self, x: int, y: int) -> None:
        """Carve passages with randomised Prim's algorithm.

        Maintains a frontier of walls between visited cells and
        unvisited neighbours. At each step a random wall is chosen;
        if its unvisited side is still unvisited, the wall is carved
        and the new cell's walls are added to the frontier. Pattern
        cells are pre-marked visited so they are never expanded.

        Args:
            x: Starting column (entry cell).
            y: Starting row (entry cell).
        """
        if not self._is_valid(x, y) or self._visited[y][x]:
            return
        self._visited[y][x] = True
        frontier: list[Wall] = []
        self._add_frontier_walls(x, y, frontier)
        while frontier:
            idx = random.randrange(len(frontier))
            cx, cy, dx, dy, wh, wo = frontier[idx]
            frontier[idx] = frontier[-1]
            frontier.pop()
            nx, ny = cx + dx, cy + dy
            if not self._is_valid(nx, ny):
                continue
            if self._visited[ny][nx]:
                continue
            self.grid[cy][cx] &= ~(1 << wh)
            self.grid[ny][nx] &= ~(1 << wo)
            self.carve_steps.append((cy, cx, wh, ny, nx, wo))
            self._visited[ny][nx] = True
            self._add_frontier_walls(nx, ny, frontier)

    def _find(
        self, parent: dict[Cell, Cell], c: Cell
    ) -> Cell:
        """Union-Find: return root of ``c`` with path compression.

        Args:
            parent: Map cell → parent cell.
            c: Cell to look up.

        Returns:
            The root cell of ``c``'s component.
        """
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    def _union(
        self,
        parent: dict[Cell, Cell],
        rank: dict[Cell, int],
        a: Cell,
        b: Cell,
    ) -> bool:
        """Union-Find: merge components of ``a`` and ``b``.

        Args:
            parent: Map cell → parent cell.
            rank: Map root cell → rank.
            a: First cell.
            b: Second cell.

        Returns:
            ``True`` if a merge happened (different components),
            ``False`` if already in the same component.
        """
        ra = self._find(parent, a)
        rb = self._find(parent, b)
        if ra == rb:
            return False
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1
        return True

    def _kruskal(self) -> None:
        """Carve passages with randomised Kruskal's algorithm.

        Builds the list of internal edges between adjacent non-pattern
        cells, shuffles it, and walks the list with Union-Find: each
        edge whose endpoints are in different components is carved.
        Pattern cells are excluded from the cell set entirely so they
        stay isolated.
        """
        parent: dict[Cell, Cell] = {}
        rank: dict[Cell, int] = {}
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self._pattern_cells:
                    continue
                parent[(x, y)] = (x, y)
                rank[(x, y)] = 0

        edges: list[Wall] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self._pattern_cells:
                    continue
                if (
                    x + 1 < self.width
                    and (x + 1, y) not in self._pattern_cells
                ):
                    edges.append((x, y, 1, 0, EAST, WEST))
                if (
                    y + 1 < self.height
                    and (x, y + 1) not in self._pattern_cells
                ):
                    edges.append((x, y, 0, 1, SOUTH, NORTH))
        random.shuffle(edges)
        for cx, cy, dx, dy, wh, wo in edges:
            nx, ny = cx + dx, cy + dy
            if self._union(parent, rank, (cx, cy), (nx, ny)):
                self.grid[cy][cx] &= ~(1 << wh)
                self.grid[ny][nx] &= ~(1 << wo)
                self.carve_steps.append((cy, cx, wh, ny, nx, wo))
        # Mark all non-pattern cells visited for consistency
        for (x, y) in parent:
            self._visited[y][x] = True

    def _knock_down_walls(self) -> None:
        """Rimuovi 15% delle mura ancora chiuse se maze e' non perfect.

        Skippa le mura esterne (sul bordo) e le mura adiacenti al
        pattern 42.
        """
        cands: list[Wall] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self._pattern_cells:
                    continue
                if (
                    x + 1 < self.width
                    and (x + 1, y) not in self._pattern_cells
                    and (self.grid[y][x] & (1 << EAST))
                ):
                    cands.append((x, y, 1, 0, EAST, WEST))
                if (
                    y + 1 < self.height
                    and (x, y + 1) not in self._pattern_cells
                    and (self.grid[y][x] & (1 << SOUTH))
                ):
                    cands.append((x, y, 0, 1, SOUTH, NORTH))
        n = int(len(cands) * _NON_PERFECT_KNOCK_RATIO)
        if n <= 0:
            return
        for cx, cy, dx, dy, wh, wo in random.sample(cands, n):
            nx, ny = cx + dx, cy + dy
            self.grid[cy][cx] &= ~(1 << wh)
            self.grid[ny][nx] &= ~(1 << wo)
            self.knock_steps.append((cy, cx, wh, ny, nx, wo))

    def _place_42_pattern(self) -> None:
        """ Segna le celle necessarie a creare il pattern 42 come
        gia' visited, in modo che gli algoritmi di carving le
        skippino e che il pattern rimanga intatto dopo l'esecuzione
        dell'algoritmo.
        """
        if self.width < _PATTERN_MIN_W or self.height < _PATTERN_MIN_H:
            print(
                "Maze too small to embed '42' pattern "
                f"(need {_PATTERN_MIN_W}x{_PATTERN_MIN_H}).",
                file=sys.stderr,
            )
            return
        ax = (self.width - _PATTERN_W) // 2
        ay = (self.height - _PATTERN_H) // 2
        offset = _DIGIT_W + _PATTERN_GAP
        cells = {(ax + dx, ay + dy) for dx, dy in _PATTERN_4}
        cells |= {(ax + offset + dx, ay + dy) for dx, dy in _PATTERN_2}
        if self.entry in cells or self.exit in cells:
            print(
                "Cannot place '42': pattern overlaps entry/exit.",
                file=sys.stderr,
            )
            return
        self._pattern_cells = cells
        for cx, cy in cells:
            self._visited[cy][cx] = True

    def write_output(self, path: str) -> None:
        """Scrive il file di output in maze.txt come richiesto da subject.

        Format::

            <WIDTH hex digits per row>\\n   × HEIGHT rows
            \\n
            <entry_x>,<entry_y>\\n
            <exit_x>,<exit_y>\\n
            <shortest path as N/E/S/W letters>\\n

        Args:
            path: File path di destinazione.
        """
        shortest = self._bfs_path()
        try:
            with open(path, "w") as fh:
                for row in self.grid:
                    fh.write("".join(format(cell, 'X') for cell in row))
                    fh.write("\n")
                fh.write("\n")
                ex, ey = self.entry
                fh.write(f"{ex},{ey}\n")
                xx, xy = self.exit
                fh.write(f"{xx},{xy}\n")
                fh.write(shortest + "\n")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)

    def _bfs_path(self) -> str:
        """Ritorna il path piu' breve da entrata a uscita con una
        stringa N/E/S/W o una stringa vuota se non esiste un path.

        Usa un semplice BFS che controlla i bit delle mura prima di
        muoversi.

        """
        # direction: (dx, dy, wall_bit_to_check, letter)
        moves = [
            (0, -1, NORTH, 'N'),
            (1,  0, EAST,  'E'),
            (0,  1, SOUTH, 'S'),
            (-1, 0, WEST,  'W'),
        ]
        start = self.entry
        goal = self.exit
        visited: dict[tuple[int, int], tuple[tuple[int, int], str] | None]
        visited = {start: None}  # cell → (parent_cell, direction_letter)
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == goal:
                break
            for dx, dy, wb, letter in moves:
                if self.grid[cy][cx] & (1 << wb):
                    continue   # wall closed — cannot pass
                nx, ny = cx + dx, cy + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and (nx, ny) not in visited
                ):
                    visited[(nx, ny)] = ((cx, cy), letter)
                    queue.append((nx, ny))

        # Reconstruct path
        if goal not in visited:
            return ""
        path_letters: list[str] = []
        cur: tuple[int, int] | None = goal
        while cur is not None and cur != start:
            entry_val = visited[cur]
            if entry_val is None:
                break
            parent, letter = entry_val
            path_letters.append(letter)
            cur = parent
        path_letters.reverse()
        return "".join(path_letters)

    def trextre(self) -> None:
        """Break every 3x3 fully-open area by adding one internal wall.

        Scans all 3x3 blocks. When every internal wall in the block is
        absent (6 horizontal + 6 vertical = 12 passages open) a wall is
        added between the centre cell and its south neighbour.
        The added wall is recorded in knock_steps so the animation can
        replay it correctly.
        """
        changed = True
        while changed:
            changed = False
            for y in range(self.height - 2):
                for x in range(self.width - 2):
                    open_block = True
                    # 6 horizontal passages: check EAST wall of cols 0,1 for each row
                    for row in range(y, y + 3):
                        for col in range(x, x + 2):
                            if self.grid[row][col] & (1 << EAST):
                                open_block = False
                                break
                        if not open_block:
                            break
                    if not open_block:
                        continue
                    # 6 vertical passages: check SOUTH wall of rows 0,1 for each col
                    for col in range(x, x + 3):
                        for row in range(y, y + 2):
                            if self.grid[row][col] & (1 << SOUTH):
                                open_block = False
                                break
                        if not open_block:
                            break
                    if not open_block:
                        continue
                    # add a wall between centre cell (x+1,y+1) and (x+1,y+2)
                    cx, cy = x + 1, y + 1
                    nx, ny = x + 1, y + 2
                    self.grid[cy][cx] |= (1 << SOUTH)
                    self.grid[ny][nx] |= (1 << NORTH)
                    self.knock_steps.append((cy, cx, SOUTH, ny, nx, NORTH))
                    changed = True
