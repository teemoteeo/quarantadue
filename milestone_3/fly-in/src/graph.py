"""Graph data structures and adjacency operations for zone networks."""

from __future__ import annotations

from collections import defaultdict

from .schemas import MapFile, Zone, ZoneType

# Movement cost in turns for each zone type (destination-based cost).
MOVE_COST: dict[ZoneType, float] = {
    "normal": 1.0,
    "blocked": float("inf"),
    "restricted": 2.0,
    "priority": 1.0,
}

# Small epsilon: prefer priority zones when costs are tied.
PRIORITY_BONUS: float = -0.01


class ZoneGraph:
    """Adjacency-list representation of the drone zone network.

    Answers the only two questions pathfinding asks: which zones
    neighbour this one, and what it costs to enter a zone. Capacity is
    deliberately absent — it lives on the parsed :class:`MapFile` and is
    enforced by :class:`~src.simulation.SimulationEngine`, which reads it
    from there directly.
    """

    def __init__(self, map_file: MapFile) -> None:
        """Build the bidirectional adjacency list from a parsed map."""
        self._zones: dict[str, Zone] = map_file.zones
        self._adj: dict[str, list[str]] = defaultdict(list)
        for conn in map_file.connections:
            self._adj[conn.from_zone].append(conn.to_zone)
            self._adj[conn.to_zone].append(conn.from_zone)

    def neighbours(self, zone_name: str) -> list[tuple[str, float]]:
        """Return (name, cost to enter) for each reachable neighbour."""
        results: list[tuple[str, float]] = []
        for neigh in self._adj.get(zone_name, []):
            dest = self._zones[neigh]
            if dest.zone_type == "blocked":
                continue
            cost = MOVE_COST[dest.zone_type]
            if dest.zone_type == "priority":
                cost += PRIORITY_BONUS
            results.append((neigh, cost))
        return results

    def zone_type(self, name: str) -> ZoneType:
        """Return the zone type for `name`."""
        return self._zones[name].zone_type
