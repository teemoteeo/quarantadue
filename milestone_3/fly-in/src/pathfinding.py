"""Pathfinding algorithms for drone routing in zone networks."""

from __future__ import annotations

import heapq
import math
from typing import Iterator

from .graph import ZoneGraph


class PathFinder:
    """Computes weighted shortest paths and per-drone routing plans.

    Wraps a modified Dijkstra traversal over a :class:`ZoneGraph`, where
    the weight of entering a zone is its movement cost (blocked zones are
    excluded by the graph itself, priority zones are nudged cheaper so
    they win ties). Capacity constraints are intentionally not considered
    here — they are enforced at the simulation layer.
    """

    def __init__(self, graph: ZoneGraph) -> None:
        """Bind this pathfinder to the zone network it will search."""
        self._graph = graph

    def shortest_path(
        self, start: str, end: str
    ) -> tuple[list[str], float] | None:
        """Return the cheapest (path, cost) from `start` to `end`, or None."""
        return self._dijkstra(start, end, frozenset())

    def k_shortest_paths(
        self, start: str, end: str, k: int
    ) -> Iterator[list[str]]:
        """Yield up to `k` distinct simple paths via an edge-removal heuristic.

        The global shortest path is yielded first, then alternatives are
        found by re-running Dijkstra with one or two edges of the
        shortest path removed, keeping only newly discovered routes.
        """
        result = self.shortest_path(start, end)
        if result is None:
            return
        shortest, _ = result
        yield shortest

        if k <= 1:
            return

        discovered: set[tuple[str, ...]] = {tuple(shortest)}

        for i in range(len(shortest) - 1):
            if len(discovered) >= k:
                return
            blocked = {(shortest[i], shortest[i + 1])}
            found = self._yield_new(start, end, blocked, discovered)
            if found is not None:
                yield found

        for i in range(len(shortest) - 1):
            for j in range(i + 1, len(shortest) - 1):
                if len(discovered) >= k:
                    return
                blocked = {
                    (shortest[i], shortest[i + 1]),
                    (shortest[j], shortest[j + 1]),
                }
                found = self._yield_new(start, end, blocked, discovered)
                if found is not None:
                    yield found

    def compute_drone_paths(self, nb_drones: int) -> list[list[str]]:
        """Assign each drone a path, round-robining across distinct routes.

        Raises:
            ValueError: If no path exists between the map's start and end.
        """
        start = self._graph.start_name
        end = self._graph.end_name

        all_paths = list(self.k_shortest_paths(start, end, nb_drones))
        if not all_paths:
            raise ValueError(f"No path from {start!r} to {end!r}")

        return [list(all_paths[i % len(all_paths)]) for i in range(nb_drones)]

    def _yield_new(
        self,
        start: str,
        end: str,
        blocked: set[tuple[str, str]],
        discovered: set[tuple[str, ...]],
    ) -> list[str] | None:
        """Search avoiding `blocked` edges; record and return if novel."""
        result = self._dijkstra(start, end, frozenset(blocked))
        if result is None:
            return None
        path, _ = result
        tup = tuple(path)
        if tup in discovered:
            return None
        discovered.add(tup)
        return path

    def _dijkstra(
        self,
        start: str,
        end: str,
        blocked: frozenset[tuple[str, str]],
    ) -> tuple[list[str], float] | None:
        """Dijkstra from `start` to `end`, skipping edges in `blocked`."""
        pq: list[tuple[float, str, list[str]]] = [(0.0, start, [start])]
        visited: dict[str, float] = {start: 0.0}

        while pq:
            dist, current, path = heapq.heappop(pq)

            if dist > visited.get(current, math.inf):
                continue

            if current == end:
                return path, dist

            for neighbour, weight, _cap in self._graph.neighbours(current):
                if (current, neighbour) in blocked or \
                   (neighbour, current) in blocked:
                    continue
                new_dist = dist + weight
                if new_dist < visited.get(neighbour, math.inf):
                    visited[neighbour] = new_dist
                    heapq.heappush(
                        pq, (new_dist, neighbour, path + [neighbour])
                    )

        return None
