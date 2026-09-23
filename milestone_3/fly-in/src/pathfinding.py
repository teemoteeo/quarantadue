"""Percorsi: distanze fisse e pianificazione condivisa nel tempo."""

from __future__ import annotations

import heapq
import math
from collections import defaultdict

from .graph import ZoneGraph
from .schemas import MapFile

# A search state: (zone, turn). A drone reaches it at the end of `turn`.
State = tuple[str, int]


class PathFinder:
    """Distanze fisse su una :class:`ZoneGraph`, senza capacità.

    Entrare in una zona costa il suo costo di movimento (le zone
    bloccate le esclude il grafo, le zone priority costano un po' meno
    così vincono a parità).
    """

    def __init__(self, graph: ZoneGraph) -> None:
        """Collega questo pathfinder alla rete di zone da esplorare."""
        self._graph = graph

    def distances_to(self, end: str) -> dict[str, float]:
        """Costo minimo verso `end` da ogni zona che può raggiungerla.

        Un solo Dijkstra partendo da `end` sul grafo al contrario: tornare
        da `u` a un vicino `v` costa quanto entrare in `u`. Le zone che non
        sono nel risultato non possono raggiungere `end`.
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


class FlightPlanner:
    """Pianifica ogni drone nel tempo con una tabella di prenotazioni.

    A* cooperativo: i droni vengono pianificati uno dopo l'altro, e
    ognuno cerca l'arrivo più presto nello spazio (zona, turno) evitando
    ciò che hanno prenotato i droni prima di lui: posti nelle zone per
    turno e posti sui collegamenti per turno. Aspettare è solo un'altra
    mossa (stessa zona, turno dopo), quindi dividere i droni su più
    strade, aspettare al momento giusto ed evitare conflitti escono
    tutti da un'unica ricerca invece che da passi separati.

    L'euristica di A* è :meth:`PathFinder.distances_to`: il costo fino
    alla fine senza contare la capacità, che non supera mai quello
    reale.
    """

    def __init__(self, map_file: MapFile) -> None:
        """Collega il pianificatore a una mappa e ne crea il grafo."""
        self._map = map_file
        self._graph = ZoneGraph(map_file)
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
        """Restituisce una timeline per drone: dove si trova dopo ogni turno.

        `timeline[t]` è il nome di una zona, oppure il nome di un
        collegamento `origine-destinazione` mentre il drone è in viaggio
        verso una zona restricted; `timeline[0]` è la zona di partenza e
        l'ultimo elemento è la zona finale.

        Raises:
            ValueError: Se nessun percorso porta dall'inizio alla fine.
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
        """A* su (zona, turno) dalla partenza all'arrivo più presto.

        Tutti i percorsi verso uno stesso stato durano lo stesso numero di
        turni, quindi la prima volta che lo si raggiunge va bene quanto le
        successive. Aspettare alla partenza è sempre possibile, quindi un
        piano esiste sempre.
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
        """Stati raggiungibili dopo: aspettare, entrare in una zona o partire.

        Una zona restricted richiede due turni: il drone occupa il
        collegamento in entrambi e deve atterrare al secondo, quindi la
        zona deve avere posto in quel momento e non si può aspettare a metà
        volo.
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
        """Se un altro drone ci sta in `zone` dopo `turn`."""
        if zone in (self._start, self._end):
            return True
        return self._occupied[(zone, turn)] < self._map.zones[zone].max_drones

    def _link_free(self, link: frozenset[str], turn: int) -> bool:
        """Se un altro drone ci sta su `link` durante `turn`."""
        return self._on_link[(link, turn)] < self._link_cap[link]

    def _reserve(self, states: list[State]) -> None:
        """Prenota i posti in zone e collegamenti usati da un drone."""
        for (a, t_a), (b, t_b) in zip(states, states[1:]):
            if a != b:
                for turn in range(t_a + 1, t_b + 1):
                    self._on_link[(frozenset((a, b)), turn)] += 1
            self._occupied[(b, t_b)] += 1

    @staticmethod
    def _timeline(states: list[State]) -> list[str]:
        """Trasforma gli stati trovati in una posizione per ogni turno."""
        timeline = [states[0][0]]
        for (a, t_a), (b, t_b) in zip(states, states[1:]):
            if t_b - t_a == 2:
                timeline.append(f"{a}-{b}")
            timeline.append(b)
        return timeline
