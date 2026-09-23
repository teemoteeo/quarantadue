"""Pathfinding: static distances, and cooperative planning through time."""

from __future__ import annotations

import heapq
import math
from collections import defaultdict

from .graph import MOVE_COST, ZoneGraph
from .schemas import MapFile

# A search state: (zone, turn). A drone reaches it at the end of `turn`.
State = tuple[str, int]


class PathFinder:
    """Static, capacity-blind distances over a :class:`ZoneGraph`.

    Entering a zone costs its movement cost (blocked zones are excluded
    by the graph, priority zones are nudged cheaper so they win ties).
    """

    def __init__(self, graph: ZoneGraph) -> None:
        """Bind this pathfinder to the zone network it will search."""
        self._graph = graph

    def distances_to(self, end: str) -> dict[str, float]:
        """Cheapest cost from every zone that can reach `end`, to `end`.

        One Dijkstra run from `end` over the reversed graph: stepping
        back from `u` to a neighbour `v` costs what entering `u` costs.
        Zones missing from the result cannot reach `end` at all.
        """
        if self._graph.zone_type(end) == "blocked":
            return {}
        dist = {end: 0.0}
        pq = [(0.0, end)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v in self._graph.neighbours(u):
                new_dist = d + self._graph.cost(u)
                if new_dist < dist.get(v, math.inf):
                    dist[v] = new_dist
                    heapq.heappush(pq, (new_dist, v))
        return dist

    def path_cost(self, path: list[str]) -> float:
        """Total movement cost, in turns, of traversing `path` alone.

        Costs are charged for entering each zone after the first, so a
        one-element path costs nothing.
        """
        return sum(MOVE_COST[self._graph.zone_type(z)] for z in path[1:])


class FlightPlanner:
    """Plans every drone through time with a shared reservation table.

    Cooperative A*: drones are planned one after another, and each finds
    its earliest arrival in (zone, turn) space around what the drones
    before it reserved — zone slots per turn and connection slots per
    turn. Waiting is just another move (same zone, next turn), so
    splitting the fleet over routes, strategic waiting and conflict
    avoidance all fall out of one search instead of being separate steps.

    The A* heuristic is :meth:`PathFinder.distances_to`: the capacity-
    blind cost to the end, which never overestimates the real one.
    """

    def __init__(self, map_file: MapFile, graph: ZoneGraph) -> None:
        """Bind the planner to a map and its zone graph."""
        self._map = map_file
        self._graph = graph
        self._start = map_file.start.name
        self._end = map_file.end.name
        self._link_cap = {
            frozenset((c.from_zone, c.to_zone)): c.max_link_capacity
            for c in map_file.connections
        }
        # Drones in each zone after a turn, and on each link during one.
        self._occupied: dict[State, int] = defaultdict(int)
        self._on_link: dict[tuple[frozenset[str], int], int] = (
            defaultdict(int)
        )

    def plan(self) -> list[list[str]]:
        """Return one timeline per drone: its position after each turn.

        `timeline[t]` is a zone name, or an `origin-dest` connection name
        while in transit toward a restricted zone; `timeline[0]` is the
        start zone and the last entry is the end zone.

        Raises:
            ValueError: If no path at all leads from start to end.
        """
        heuristic = PathFinder(self._graph).distances_to(self._end)
        if self._start not in heuristic:
            raise ValueError(
                f"No path from {self._start!r} to {self._end!r}"
            )
        timelines = []
        for _ in range(self._map.nb_drones):
            states = self._search(heuristic)
            self._reserve(states)
            timelines.append(self._timeline(states))
        return timelines

    def _search(self, heuristic: dict[str, float]) -> list[State]:
        """A* over (zone, turn) from the start to the earliest arrival.

        Every path to a given state takes the same number of turns, so
        the first time a state is reached is as good as any later one.
        Waiting at the start is always allowed, so a plan always exists.
        """
        came_from: dict[State, State | None] = {(self._start, 0): None}
        pq = [(heuristic[self._start], 0, self._start)]
        while True:
            _, turn, zone = heapq.heappop(pq)
            if zone == self._end:
                break
            for nxt in self._successors(zone, turn):
                if nxt[0] in heuristic and nxt not in came_from:
                    came_from[nxt] = (zone, turn)
                    heapq.heappush(
                        pq, (nxt[1] + heuristic[nxt[0]], nxt[1], nxt[0])
                    )
        states: list[State] = []
        state: State | None = (zone, turn)
        while state is not None:
            states.append(state)
            state = came_from[state]
        return states[::-1]

    def _successors(self, zone: str, turn: int) -> list[State]:
        """States reachable next: wait, step to a zone, or start a transit.

        A restricted zone takes two turns: the drone holds the connection
        on both, and must land on the second — so the zone needs room
        then, and there is no waiting mid-flight.
        """
        result: list[State] = []
        if self._zone_free(zone, turn + 1):
            result.append((zone, turn + 1))
        for dest in self._graph.neighbours(zone):
            link = frozenset((zone, dest))
            if self._graph.zone_type(dest) == "restricted":
                if (self._link_free(link, turn + 1)
                        and self._link_free(link, turn + 2)
                        and self._zone_free(dest, turn + 2)):
                    result.append((dest, turn + 2))
            elif (self._link_free(link, turn + 1)
                    and self._zone_free(dest, turn + 1)):
                result.append((dest, turn + 1))
        return result

    def _zone_free(self, zone: str, turn: int) -> bool:
        """Whether one more drone fits in `zone` after `turn`."""
        if zone in (self._start, self._end):
            return True
        return self._occupied[(zone, turn)] < self._map.zones[zone].max_drones

    def _link_free(self, link: frozenset[str], turn: int) -> bool:
        """Whether one more drone fits on `link` during `turn`."""
        return self._on_link[(link, turn)] < self._link_cap[link]

    def _reserve(self, states: list[State]) -> None:
        """Book the zone and connection slots a planned drone uses."""
        for (a, t_a), (b, t_b) in zip(states, states[1:]):
            if a != b:
                for turn in range(t_a + 1, t_b + 1):
                    self._on_link[(frozenset((a, b)), turn)] += 1
            self._occupied[(b, t_b)] += 1

    @staticmethod
    def _timeline(states: list[State]) -> list[str]:
        """Expand the searched states into one position per turn."""
        timeline = [states[0][0]]
        for (a, t_a), (b, t_b) in zip(states, states[1:]):
            if t_b - t_a == 2:
                timeline.append(f"{a}-{b}")
            timeline.append(b)
        return timeline
