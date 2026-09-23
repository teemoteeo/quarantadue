"""Strutture a grafo e adiacenze per la rete di zone."""

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
    """Rete di zone dei droni come lista di adiacenza.

    Risponde alle sole due domande che fa la ricerca dei percorsi: quali
    zone confinano con questa, e quanto costa entrare in una zona. La
    capacità manca di proposito: sta nella :class:`MapFile` letta, dove
    il pianificatore e il motore la leggono direttamente.
    """

    def __init__(self, map_file: MapFile) -> None:
        """Costruisce la lista di adiacenza bidirezionale dalla mappa."""
        self._zones: dict[str, Zone] = map_file.zones
        self._adj: dict[str, list[str]] = defaultdict(list)
        for conn in map_file.connections:
            self._adj[conn.from_zone].append(conn.to_zone)
            self._adj[conn.to_zone].append(conn.from_zone)

    def neighbours(self, zone_name: str) -> list[str]:
        """Zone vicine in cui un drone può entrare (escluse le bloccate)."""
        return [
            neigh for neigh in self._adj.get(zone_name, [])
            if self.zone_type(neigh) != "blocked"
        ]

    def cost(self, name: str) -> float:
        """Costo per entrare in `name`; le zone priority costano poco meno."""
        zone_type = self.zone_type(name)
        bonus = PRIORITY_BONUS if zone_type == "priority" else 0.0
        return MOVE_COST[zone_type] + bonus

    def zone_type(self, name: str) -> ZoneType:
        """Restituisce il tipo della zona `name`."""
        return self._zones[name].zone_type
