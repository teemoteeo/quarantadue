#!/usr/bin/env python3

import random
import sys
from collections import deque
from parser import MazeConfig, parse_input

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

DIRECTIONS = [
    (0, -1, NORTH, SOUTH),
    (1,  0, EAST,  WEST),
    (0,  1, SOUTH, NORTH),
    (-1, 0, WEST,  EAST),
]


# ── "42" pattern ──────────────────────────────────────────────────────────
# Each tuple is (dx, dy) offset from the anchor cell (top-left of pattern).
# The pattern fits in an 8-wide × 5-tall bounding box.
#
#   "4"          "2"
#   X . .        . X X
#   X . X        X . X   ← (dx 0-2 = "4", dx 4-6 = "2", gap col 3)
#   X X X        . . X
#   . . X        X X .
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

# Horizontal gap between "4" and "2" in cell units
_PATTERN_GAP = 1
# Width of each digit bounding box
_DIGIT_W = 3
# Total pattern width = 4_box + gap + 2_box
_PATTERN_W = _DIGIT_W + _PATTERN_GAP + _DIGIT_W   # 7
_PATTERN_H = 5

# Minimum maze size to embed the pattern (add margin of 2 on each side)
_PATTERN_MIN_W = _PATTERN_W + 4   # 11
_PATTERN_MIN_H = _PATTERN_H + 6   # 11


_FONT = {
    'A': ["01110", "10001", "11111", "10001", "10001"],
    '-': ["00000", "00000", "11111", "00000", "00000"],
    'M': ["10001", "11011", "10101", "10001", "10001"],
    'Z': ["11111", "00011", "00110", "01100", "11111"],
    'E': ["11111", "10000", "11110", "10000", "11111"],
    'I': ["11111", "00100", "00100", "00100", "11111"],
    'N': ["10001", "11001", "10101", "10011", "10001"],
    'G': ["01110", "10000", "10111", "10001", "01110"],
}


def print_title() -> None:
    TOP = "\033[38;5;223m\033[48;5;208m"  # light fg on orange bg
    FRONT = "\033[38;5;208m\033[48;5;130m"  # orange fg on dark bg
    RESET = "\033[0m"
    PW = 2
    GAP = PW

    title = "A-MAZE-ING"
    for font_row in range(5):
        top_line = bot_line = ""
        for ci, ch in enumerate(title):
            if ci > 0:
                top_line += " " * GAP
                bot_line += " " * GAP
            for px in _FONT.get(ch, "00000")[font_row]:
                if px == "1":
                    top_line += TOP + "▀" * PW + RESET
                    bot_line += FRONT + "▄" * PW + RESET
                else:
                    top_line += " " * PW
                    bot_line += " " * PW
        print(top_line)
        print(bot_line)
    print()


class MazeGenerator:
    def __init__(self, config: MazeConfig) -> None:
        self.width = config.width
        self.height = config.height
        self.entry = config.entry
        self.exit = config.exit
        self.grid = [[15] * self.width for _ in range(self.height)]
        self._visited = [[False] * self.width for _ in range(self.height)]
        self._pattern_cells: set[tuple[int, int]] = set()
        self._place_42_pattern_pre()
        if config.seed is not None:
            random.seed(config.seed)
        ex, ey = self.entry
        self._dfs(ex, ey)
        self._place_42_pattern_post()

    def _is_valid(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _dfs(self, x: int, y: int) -> None:
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
                    self._visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    def _build_pattern_cells(self) -> set[tuple[int, int]]:
        """Compute the set of (x, y) cells that form the '42' pattern."""
        anchor_x = (self.width - _PATTERN_W) // 2
        anchor_y = (self.height - _PATTERN_H) // 2
        cells: set[tuple[int, int]] = set()
        for dx, dy in _PATTERN_4:
            cells.add((anchor_x + dx, anchor_y + dy))
        offset = _DIGIT_W + _PATTERN_GAP
        for dx, dy in _PATTERN_2:
            cells.add((anchor_x + offset + dx, anchor_y + dy))
        return cells

    def _place_42_pattern_pre(self) -> None:
        """Phase 1 (before DFS): mark pattern cells as visited and 0xF.

        This ensures the DFS never carves through pattern cells, so
        maze connectivity is preserved.
        """
        if self.width < _PATTERN_MIN_W or self.height < _PATTERN_MIN_H:
            print(
                "Maze too small to embed '42' pattern "
                f"(need {_PATTERN_MIN_W}x{_PATTERN_MIN_H}).",
                file=sys.stderr,
            )
            return
        self._pattern_cells = self._build_pattern_cells()
        if self.entry in self._pattern_cells or (
            self.exit in self._pattern_cells
        ):
            print(
                "Cannot place '42': pattern overlaps entry/exit.",
                file=sys.stderr,
            )
            self._pattern_cells = set()
            return
        for cx, cy in self._pattern_cells:
            self.grid[cy][cx] = 0xF
            self._visited[cy][cx] = True  # DFS will skip these

    def _place_42_pattern_post(self) -> None:
        """Phase 2 (after DFS): seal neighbours facing the pattern.

        Closes the wall on each non-pattern neighbour that faces a
        pattern cell, so the pattern is fully isolated.
        """
        if not self._pattern_cells:
            return
        # (dx, dy, wall_bit_to_close_on_neighbour)
        nbr_dirs = [
            (0, -1, SOUTH),
            (1,  0, WEST),
            (0,  1, NORTH),
            (-1, 0, EAST),
        ]
        for cx, cy in self._pattern_cells:
            self.grid[cy][cx] = 0xF  # re-enforce (DFS may border it)
            for dx, dy, nbr_wall in nbr_dirs:
                nx, ny = cx + dx, cy + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and (nx, ny) not in self._pattern_cells
                ):
                    self.grid[ny][nx] |= (1 << nbr_wall)

    def write_output(self, path: str) -> None:
        """Write the maze to *path* in the format required by §IV.5.

        Format::

            <WIDTH hex digits per row>\\n   × HEIGHT rows
            \\n
            <entry_x>,<entry_y>\\n
            <exit_x>,<exit_y>\\n
            <shortest path as N/E/S/W letters>\\n

        Args:
            path: Destination file path.
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
        """Return shortest path from entry to exit as N/E/S/W string.

        Uses a simple BFS that checks wall bits before moving.

        Returns:
            String of direction letters, or empty string if no path.
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

    def print_ascii(self) -> None:
        W, H = self.width, self.height
        top = "+" + "+".join(
            "---" if self.grid[0][x] & (1 << NORTH) else "   "
            for x in range(W)
        ) + "+"
        print(top)
        for y in range(H):
            row = ""
            for x in range(W):
                row += "|" if self.grid[y][x] & (1 << WEST) else " "
                if (x, y) == self.entry:
                    row += " E "
                elif (x, y) == self.exit:
                    row += " X "
                else:
                    row += "   "
            row += "|" if self.grid[y][W - 1] & (1 << EAST) else " "
            print(row)
            print("+" + "+".join(
                "---" if self.grid[y][x] & (1 << SOUTH) else "   "
                for x in range(W)
            ) + "+")


if __name__ == "__main__":
    config = parse_input("config.txt")
    if not config.validate():
        print("config non valida")
        exit(1)
    print_title()
    maze = MazeGenerator(config)
    maze.print_ascii()
