#!/usr/bin/env python3
"""mazegen — minimal, dependency-free maze generator.

Generate a perfect maze on a rectangular grid using iterative
randomised depth-first search. Each cell stores its closed walls as a
4-bit nibble (bit 0=N, 1=E, 2=S, 3=W). The shortest entry-to-exit
solution is computed via BFS at construction time.

Example:
    >>> from mazegen import MazeGenerator
    >>> maze = MazeGenerator(
    ...     width=10, height=10,
    ...     entry=(0, 0), exit=(9, 9),
    ...     seed=42,
    ... )
    >>> maze.grid           # 2D list[list[int]], grid[y][x]
    >>> maze.solution       # 'SESESEESSE...' (N/E/S/W letters)
    >>> maze.write_output('maze.txt')
    >>> maze.print_ascii()
"""

import random
import sys
from collections import deque

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

DIRECTIONS = [
    (0, -1, NORTH, SOUTH),
    (1,  0, EAST,  WEST),
    (0,  1, SOUTH, NORTH),
    (-1, 0, WEST,  EAST),
]


class MazeGenerator:
    """Generate a perfect maze on a rectangular grid.

    The grid is a 2D list of integers — one nibble per cell encoding
    closed walls (bit 0=N, 1=E, 2=S, 3=W). Generation runs an iterative
    randomised depth-first search seeded at ``entry``. The shortest
    path from ``entry`` to ``exit`` is computed via BFS and stored on
    the public ``solution`` attribute as a string of ``N``/``E``/``S``/
    ``W`` letters.

    Attributes:
        width: Maze width in cells.
        height: Maze height in cells.
        entry: ``(x, y)`` entry coordinates.
        exit: ``(x, y)`` exit coordinates.
        grid: 2D list ``grid[y][x]`` of cell wall nibbles.
        solution: Shortest path letters from entry to exit.
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit: tuple[int, int],
        seed: int | None = None,
    ) -> None:
        """Build the maze in place from explicit parameters.

        Args:
            width: Maze width in cells (must be > 0).
            height: Maze height in cells (must be > 0).
            entry: ``(x, y)`` entry coordinates, inside the grid.
            exit: ``(x, y)`` exit coordinates, inside the grid and
                different from ``entry``.
            seed: Optional RNG seed for reproducible generation.

        Raises:
            ValueError: If ``width``/``height`` are not positive, if
                ``entry``/``exit`` lie outside the grid or are equal,
                or if any coordinate is negative.
        """
        if width <= 0 or height <= 0:
            raise ValueError(
                f"width and height must be > 0 "
                f"(got width={width}, height={height})"
            )
        ex, ey = entry
        xx, xy = exit
        if ex < 0 or ey < 0 or xx < 0 or xy < 0:
            raise ValueError(
                f"entry/exit coordinates must be non-negative "
                f"(got entry={entry}, exit={exit})"
            )
        if ex >= width or ey >= height or xx >= width or xy >= height:
            raise ValueError(
                f"entry/exit must be inside the {width}x{height} grid "
                f"(got entry={entry}, exit={exit})"
            )
        if entry == exit:
            raise ValueError(
                f"entry and exit must differ (both = {entry})"
            )
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.grid: list[list[int]] = [
            [15] * width for _ in range(height)
        ]
        self._visited: list[list[bool]] = [
            [False] * width for _ in range(height)
        ]
        if seed is not None:
            random.seed(seed)
        self._dfs(ex, ey)
        self.solution: str = self._bfs_path()

    def _is_valid(self, x: int, y: int) -> bool:
        """Check that ``(x, y)`` lies inside the grid.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            ``True`` if the coordinates are within bounds.
        """
        return 0 <= x < self.width and 0 <= y < self.height

    def _dfs(self, x: int, y: int) -> None:
        """Carve passages with iterative randomised depth-first search.

        Mutates ``self.grid`` in place by clearing wall bits between
        visited neighbours.

        Args:
            x: Starting column.
            y: Starting row.
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
                    self._visited[ny][nx] = True
                    stack.append((nx, ny))
                    moved = True
                    break
            if not moved:
                stack.pop()

    def write_output(self, path: str) -> None:
        """Write the maze to *path* in the standard hex format.

        Format::

            <WIDTH hex digits per row>\\n   x HEIGHT rows
            \\n
            <entry_x>,<entry_y>\\n
            <exit_x>,<exit_y>\\n
            <shortest path as N/E/S/W letters>\\n

        Args:
            path: Destination file path.
        """
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
                fh.write(self.solution + "\n")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)

    def _bfs_path(self) -> str:
        """Return shortest path from entry to exit as N/E/S/W string.

        Uses a simple BFS that checks wall bits before moving.

        Returns:
            String of direction letters, or empty string if no path.
        """
        moves = [
            (0, -1, NORTH, 'N'),
            (1,  0, EAST,  'E'),
            (0,  1, SOUTH, 'S'),
            (-1, 0, WEST,  'W'),
        ]
        start = self.entry
        goal = self.exit
        visited: dict[
            tuple[int, int], tuple[tuple[int, int], str] | None
        ]
        visited = {start: None}
        queue: deque[tuple[int, int]] = deque([start])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == goal:
                break
            for dx, dy, wb, letter in moves:
                if self.grid[cy][cx] & (1 << wb):
                    continue
                nx, ny = cx + dx, cy + dy
                if (
                    0 <= nx < self.width
                    and 0 <= ny < self.height
                    and (nx, ny) not in visited
                ):
                    visited[(nx, ny)] = ((cx, cy), letter)
                    queue.append((nx, ny))

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
        """Print the maze to stdout using simple ASCII characters.

        Walls are drawn with ``+``, ``-``, ``|``. Entry and exit cells
        are marked ``E`` and ``X`` respectively.
        """
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
