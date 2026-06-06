"""Pathfinding algorithms for drone routing in zone networks."""

from __future__ import annotations

import heapq
import math
from typing import Iterator

from .graph import ZoneGraph


def compute_shortest_path(
    graph: ZoneGraph,
    start: str,
    end: str,
) -> tuple[list[str], float] | None:
    """Dijkstra from start to end. Returns (path, cost) or None."""
    pq: list[tuple[float, str, list[str]]] = [(0.0, start, [start])]
    visited: dict[str, float] = {start: 0.0}

    while pq:
        dist, current, path = heapq.heappop(pq)

        if dist > visited.get(current, math.inf):
            continue

        if current == end:
            return path, dist

        for neighbour, weight, _capacity in graph.neighbours(current):
            new_dist = dist + weight
            if new_dist < visited.get(neighbour, math.inf):
                visited[neighbour] = new_dist
                heapq.heappush(pq, (new_dist, neighbour, path + [neighbour]))

    return None


def compute_shortest_paths(
    graph: ZoneGraph,
    nb_drones: int,
) -> list[list[str]]:
    """Compute one path per drone, round-robining across distinct paths."""
    start = graph.start_name
    end = graph.end_name

    all_paths = list(compute_k_shortest_paths(graph, start, end, nb_drones))
    if not all_paths:
        raise ValueError(f"No path from {start!r} to {end!r}")

    return [list(all_paths[i % len(all_paths)]) for i in range(nb_drones)]


def compute_k_shortest_paths(
    graph: ZoneGraph,
    start: str,
    end: str,
    k: int,
) -> Iterator[list[str]]:
    """Yield up to k distinct simple paths via edge-removal heuristic."""
    result = compute_shortest_path(graph, start, end)
    if result is None:
        return
    shortest, _ = result
    yield shortest

    if k <= 1:
        return

    discovered: set[tuple[str, ...]] = {tuple(shortest)}
    for i in range(len(shortest) - 1):
        blocked = {(shortest[i], shortest[i + 1])}
        alt = _find_path_avoiding_edges(graph, start, end, blocked)
        if alt is not None:
            tup = tuple(alt)
            if tup not in discovered:
                discovered.add(tup)
                yield alt
                if len(discovered) >= k:
                    return

    for i in range(len(shortest) - 1):
        for j in range(i + 1, len(shortest) - 1):
            if len(discovered) >= k:
                return
            blocked = {
                (shortest[i], shortest[i + 1]),
                (shortest[j], shortest[j + 1]),
            }
            alt = _find_path_avoiding_edges(graph, start, end, blocked)
            if alt is not None:
                tup = tuple(alt)
                if tup not in discovered:
                    discovered.add(tup)
                    yield alt


def _find_path_avoiding_edges(
    graph: ZoneGraph,
    start: str,
    end: str,
    blocked: set[tuple[str, str]],
) -> list[str] | None:
    """Dijkstra avoiding a set of directed edges (checked both directions)."""
    pq: list[tuple[float, str, list[str]]] = [(0.0, start, [start])]
    visited: dict[str, float] = {start: 0.0}

    while pq:
        dist, current, path = heapq.heappop(pq)
        if dist > visited.get(current, math.inf):
            continue
        if current == end:
            return path
        for neighbour, weight, _capacity in graph.neighbours(current):
            if (current, neighbour) in blocked or \
               (neighbour, current) in blocked:
                continue
            new_dist = dist + weight
            if new_dist < visited.get(neighbour, math.inf):
                visited[neighbour] = new_dist
                heapq.heappush(pq, (new_dist, neighbour, path + [neighbour]))
    return None
