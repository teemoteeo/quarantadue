"""Graph data structures and adjacency operations for zone networks."""

from __future__ import annotations

from collections import defaultdict

from .schemas import Connection, MapFile, Zone, ZoneType

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

    Provides neighbours lookup, movement cost queries, and capacity tracking.
    """

    def __init__(self, map_file: MapFile) -> None:
        self._map_start = map_file.start
        self._map_end = map_file.end
        self._zones: dict[str, Zone] = dict(map_file.zones)
        self._adj: dict[str, list[tuple[str, Connection]]] = (
            self._build_adjacency(map_file.connections)
        )
        self._conn_metadata: dict[tuple[str, str], Connection] = {}
        for conn in map_file.connections:
            key = (min(conn.from_zone, conn.to_zone),
                   max(conn.from_zone, conn.to_zone))
            self._conn_metadata[key] = conn

    @staticmethod
    def _build_adjacency(
        connections: list[Connection],
    ) -> dict[str, list[tuple[str, Connection]]]:
        adj: dict[str, list[tuple[str, Connection]]] = defaultdict(list)
        for conn in connections:
            adj[conn.from_zone].append((conn.to_zone, conn))
            # reverse direction (same metadata applies)
            rev = Connection(
                from_zone=conn.to_zone,
                to_zone=conn.from_zone,
                metadata=conn.metadata,
            )
            adj[conn.to_zone].append((conn.from_zone, rev))
        return adj

    @property
    def zones(self) -> dict[str, Zone]:
        return self._zones

    def neighbours(self, zone_name: str) -> list[tuple[str, float, int]]:
        """Return (name, weight, capacity) for each reachable neighbour."""
        results: list[tuple[str, float, int]] = []
        for neigh, conn in self._adj.get(zone_name, []):
            dest = self._zones.get(neigh)
            if dest is None:
                continue
            if dest.metadata.zone == "blocked":
                continue
            cost = MOVE_COST[dest.metadata.zone]
            if dest.metadata.zone == "priority":
                cost += PRIORITY_BONUS
            capacity = conn.metadata.max_link_capacity
            results.append((neigh, float(cost), capacity))
        return results

    def zone_type(self, name: str) -> ZoneType:
        zone = self._zones.get(name)
        if zone is None:
            return "normal"
        return zone.metadata.zone

    def zone_capacity(self, name: str) -> int:
        zone = self._zones.get(name)
        if zone is None:
            return 0
        return zone.metadata.max_drones

    def zone_color(self, name: str) -> str | None:
        zone = self._zones.get(name)
        if zone is None:
            return None
        return zone.metadata.color

    def connection_capacity(self, a: str, b: str) -> int:
        key = (min(a, b), max(a, b))
        conn = self._conn_metadata.get(key)
        if conn is None:
            return 1
        return conn.metadata.max_link_capacity

    @property
    def start_name(self) -> str:
        return self._map_start.name

    @property
    def end_name(self) -> str:
        return self._map_end.name
