"""Pathfinding algorithms for drone routing in zone networks."""

from __future__ import annotations

import heapq
import math

from .graph import MOVE_COST, ZoneGraph


class PathFinder:
    """Computes weighted shortest paths through a zone network.

    Wraps a modified Dijkstra traversal over a :class:`ZoneGraph`, where
    the weight of entering a zone is its movement cost (blocked zones are
    excluded by the graph itself, priority zones are nudged cheaper so
    they win ties). Capacity constraints are intentionally not considered
    here — they are enforced at the simulation layer, and deciding how
    many drones take each of these routes is
    :class:`~src.simulation.RouteScheduler`'s job.
    """

    def __init__(self, graph: ZoneGraph) -> None:
        """Bind this pathfinder to the zone network it will search."""
        self._graph = graph

    def k_shortest_paths(
        self, start: str, end: str, k: int
    ) -> list[list[str]]:
        """Return up to `k` distinct simple paths via edge removal.

        The global shortest path comes first. Then come detours that
        avoid one of its edges (routes that share most of it), then
        greedily edge-disjoint routes, each avoiding every edge found so
        far (parallel corridors a single-edge detour never reaches).
        """
        result = self.shortest_path(start, end)
        if result is None:
            return []
        shortest = result[0]
        found = [shortest]
        for edge in zip(shortest, shortest[1:]):
            result = self.shortest_path(start, end, frozenset({edge}))
            if result is not None and result[0] not in found:
                found.append(result[0])
        while len(found) < k:
            used = frozenset(e for p in found for e in zip(p, p[1:]))
            result = self.shortest_path(start, end, used)
            if result is None:
                break
            found.append(result[0])
        return found[:k]

    def path_cost(self, path: list[str]) -> float:
        """Total movement cost, in turns, of traversing `path` alone.

        Costs are charged for entering each zone after the first, so a
        one-element path costs nothing.
        """
        return sum(MOVE_COST[self._graph.zone_type(z)] for z in path[1:])

    def shortest_path(
        self,
        start: str,
        end: str,
        blocked: frozenset[tuple[str, str]] = frozenset(),
    ) -> tuple[list[str], float] | None:
        """Return the cheapest (path, cost) avoiding `blocked` edges."""
        pq: list[tuple[float, str, list[str]]] = [(0.0, start, [start])]
        visited: dict[str, float] = {start: 0.0}

        while pq:
            dist, current, path = heapq.heappop(pq)

            if dist > visited.get(current, math.inf):
                continue

            if current == end:
                return path, dist

            for neighbour, weight in self._graph.neighbours(current):
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
