#!/usr/bin/env python3

from collections import deque
from typing import Any, Optional

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

MOVES = [
    (0, -1, NORTH),
    (1,  0, EAST),
    (0,  1, SOUTH),
    (-1, 0, WEST),
]


class MazeSolver:
    def __init__(self, generator: Any) -> None:
        self.grid = generator.grid
        self.w = generator.width
        self.h = generator.height

    def _neighbours(
        self, cx: int, cy: int
    ) -> list[tuple[int, int]]:
        result = []
        for dx, dy, wall in MOVES:
            if self.grid[cy][cx] & (1 << wall):
                continue
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < self.w and 0 <= ny < self.h:
                result.append((nx, ny))
        return result

    def bfs(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Shortest path (monodirectional). Returns list of (x,y) or []."""
        queue: deque[tuple[int, int]] = deque([start])
        visited: dict[
            tuple[int, int], Optional[tuple[int, int]]
        ] = {start: None}

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) == goal:
                break
            for nx, ny in self._neighbours(cx, cy):
                if (nx, ny) not in visited:
                    visited[(nx, ny)] = (cx, cy)
                    queue.append((nx, ny))

        if goal not in visited:
            return []
        path: list[tuple[int, int]] = []
        cur: Optional[tuple[int, int]] = goal
        while cur is not None:
            path.append(cur)
            cur = visited[cur]
        path.reverse()
        return path

    def bfs_bidir(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> tuple[
        list[tuple[int, int]],
        list[tuple[str, tuple[int, int], Optional[tuple[int, int]]]],
    ]:
        """Bidirectional BFS.

        Returns (path, steps_log).
        steps_log entries: (side, cell, parent) in expansion order.
        parent is None for the start/goal seed cells.
        'a' expands from start, 'b' from goal.
        path is the optimal shortest route.
        """
        if start == goal:
            return [start], []

        parent_a: dict[
            tuple[int, int], Optional[tuple[int, int]]
        ] = {start: None}
        parent_b: dict[
            tuple[int, int], Optional[tuple[int, int]]
        ] = {goal: None}

        queue_a: deque[tuple[int, int]] = deque([start])
        queue_b: deque[tuple[int, int]] = deque([goal])

        steps_log: list[
            tuple[str, tuple[int, int], Optional[tuple[int, int]]]
        ] = []

        meeting: Optional[tuple[int, int]] = None

        def _expand(
            queue: deque[tuple[int, int]],
            mine: dict[
                tuple[int, int], Optional[tuple[int, int]]
            ],
            other: dict[
                tuple[int, int], Optional[tuple[int, int]]
            ],
            side: str,
        ) -> Optional[tuple[int, int]]:
            for _ in range(len(queue)):
                cx, cy = queue.popleft()
                steps_log.append((side, (cx, cy), mine.get((cx, cy))))
                if (cx, cy) in other:
                    return (cx, cy)
                for nx, ny in self._neighbours(cx, cy):
                    if (nx, ny) not in mine:
                        mine[(nx, ny)] = (cx, cy)
                        queue.append((nx, ny))
                        if (nx, ny) in other:
                            steps_log.append(
                                (side, (nx, ny), (cx, cy))
                            )
                            return (nx, ny)
            return None

        while queue_a and queue_b:
            meeting = _expand(queue_a, parent_a, parent_b, 'a')
            if meeting:
                break
            meeting = _expand(queue_b, parent_b, parent_a, 'b')
            if meeting:
                break

        if meeting is None:
            return [], steps_log

        # reconstruct optimal path through meeting point
        path_a: list[tuple[int, int]] = []
        cur: Optional[tuple[int, int]] = meeting
        while cur is not None:
            path_a.append(cur)
            cur = parent_a[cur]
        path_a.reverse()

        path_b: list[tuple[int, int]] = []
        nxt = parent_b.get(meeting)
        while nxt is not None:
            path_b.append(nxt)
            nxt = parent_b[nxt]

        return path_a + path_b, steps_log

    def bfs_bidir_layers(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> tuple[
        list[tuple[int, int]],
        list[
            tuple[
                str,
                list[
                    tuple[tuple[int, int], Optional[tuple[int, int]]]
                ],
            ]
        ],
    ]:
        """Bidirectional BFS, layer-grouped output.

        Returns (path, layers).
        layers: list of (side, cells) where cells is the full BFS wavefront
        popped during one expansion step (one layer). cells items are
        (cell, parent). 'a' expands from start, 'b' from goal.
        path is the optimal shortest route.
        """
        if start == goal:
            return [start], []

        parent_a: dict[
            tuple[int, int], Optional[tuple[int, int]]
        ] = {start: None}
        parent_b: dict[
            tuple[int, int], Optional[tuple[int, int]]
        ] = {goal: None}

        queue_a: deque[tuple[int, int]] = deque([start])
        queue_b: deque[tuple[int, int]] = deque([goal])

        layers: list[
            tuple[
                str,
                list[
                    tuple[tuple[int, int], Optional[tuple[int, int]]]
                ],
            ]
        ] = []

        meeting: Optional[tuple[int, int]] = None

        def _expand(
            queue: deque[tuple[int, int]],
            mine: dict[
                tuple[int, int], Optional[tuple[int, int]]
            ],
            other: dict[
                tuple[int, int], Optional[tuple[int, int]]
            ],
            side: str,
        ) -> Optional[tuple[int, int]]:
            layer: list[
                tuple[tuple[int, int], Optional[tuple[int, int]]]
            ] = []
            for _ in range(len(queue)):
                cx, cy = queue.popleft()
                layer.append(((cx, cy), mine.get((cx, cy))))
                if (cx, cy) in other:
                    layers.append((side, layer))
                    return (cx, cy)
                for nx, ny in self._neighbours(cx, cy):
                    if (nx, ny) not in mine:
                        mine[(nx, ny)] = (cx, cy)
                        queue.append((nx, ny))
                        if (nx, ny) in other:
                            layer.append(((nx, ny), (cx, cy)))
                            layers.append((side, layer))
                            return (nx, ny)
            layers.append((side, layer))
            return None

        while queue_a and queue_b:
            meeting = _expand(queue_a, parent_a, parent_b, 'a')
            if meeting:
                break
            meeting = _expand(queue_b, parent_b, parent_a, 'b')
            if meeting:
                break

        if meeting is None:
            return [], layers

        path_a: list[tuple[int, int]] = []
        cur: Optional[tuple[int, int]] = meeting
        while cur is not None:
            path_a.append(cur)
            cur = parent_a[cur]
        path_a.reverse()

        path_b: list[tuple[int, int]] = []
        nxt = parent_b.get(meeting)
        while nxt is not None:
            path_b.append(nxt)
            nxt = parent_b[nxt]

        return path_a + path_b, layers
