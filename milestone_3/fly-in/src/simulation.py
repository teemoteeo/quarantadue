"""Simulazione a turni: riproduce i voli pianificati con le regole.

Il pianificatore (:class:`~src.pathfinding.FlightPlanner`) decide
dove si trova ogni drone dopo ogni turno. Il motore riproduce queste
timeline un turno alla volta e controlla ogni regola di movimento e
capacità del subject, così un piano non valido fallisce subito
invece di stampare un log sbagliato.

Regole principali del subject:
- I droni che lasciano una zona liberano posto già nello STESSO turno.
- La capacità di una zona si controlla DOPO aver contato le partenze.
- Zona restricted: il drone occupa il collegamento e arriva al turno
  dopo.
- Nelle zone bloccate non si entra mai.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .schemas import MapFile


@dataclass(frozen=True)
class Movement:
    """Dove va un drone in un singolo turno.

    `destination` è il nome di una zona, oppure il nome di un
    collegamento `origine-destinazione` mentre il drone è in viaggio
    verso una zona restricted. Tenere l'id del drone come campo
    separato, invece di metterlo dentro una stringa, permette di
    leggerlo direttamente senza rileggere il testo stampato, che è
    ambiguo per i nomi dei collegamenti (``D3-a-b``).
    """

    drone_id: int
    destination: str

    def __str__(self) -> str:
        """Scrive il token di output `D<id>-<destination>` del subject."""
        return f"D{self.drone_id}-{self.destination}"


@dataclass
class TurnLog:
    """Tutti i movimenti dei droni avvenuti in un turno."""

    turn: int
    movements: list[Movement]


class SimulationEngine:
    """Riproduce una timeline pianificata per drone, controllando le regole.

    A ogni turno ogni drone va alla sua prossima posizione, e il turno
    viene controllato tutto insieme:

    - una mossa segue un collegamento e non entra mai in una zona
      bloccata;
    - in una zona restricted si entra solo passando dal suo
      collegamento (`D1-a-b`), e il drone atterra al turno subito dopo;
    - i droni su ogni collegamento durante il turno, e in ogni zona dopo
      il turno (tranne partenza e arrivo), non superano la capacità.

    L'occupazione si conta dopo tutte le mosse, quindi un drone che
    lascia una zona libera il posto per un altro che entra nello stesso
    turno.
    """

    def __init__(self, map_file: MapFile, timelines: list[list[str]]) -> None:
        """Collega il motore a una mappa e a una timeline per drone.

        Args:
            map_file: La mappa letta, con zone e collegamenti.
            timelines: Per ogni drone, dove si trova dopo ogni turno: una
                zona, oppure un collegamento `origine-destinazione` mentre
                è in viaggio verso una zona restricted. L'indice 0 è la zona
                di partenza.
        """
        self._map = map_file
        self._timelines = timelines
        self._adj: dict[str, set[str]] = defaultdict(set)
        self._link_cap: dict[frozenset[str], int] = {}
        for conn in map_file.connections:
            self._adj[conn.from_zone].add(conn.to_zone)
            self._adj[conn.to_zone].add(conn.from_zone)
            link = frozenset((conn.from_zone, conn.to_zone))
            self._link_cap[link] = conn.max_link_capacity

    def run(self) -> list[TurnLog]:
        """Riproduce ogni turno finché l'ultimo drone non è arrivato.

        Returns:
            Il log completo dei movimenti turno per turno.

        Raises:
            RuntimeError: Se una timeline viola una regola di movimento o
                di capacità.
        """
        start, end = self._map.start.name, self._map.end.name
        for drone_id, timeline in enumerate(self._timelines, start=1):
            if timeline[0] != start or timeline[-1] != end:
                raise RuntimeError(
                    f"D{drone_id} must fly from {start!r} to {end!r}"
                )
        last_turn = max(len(t) for t in self._timelines) - 1
        return [self._step(turn) for turn in range(1, last_turn + 1)]

    def _step(self, turn: int) -> TurnLog:
        """Muove di un turno i droni in volo e controlla il risultato."""
        movements: list[Movement] = []
        on_link: Counter[frozenset[str]] = Counter()
        in_zone: Counter[str] = Counter()
        for drone_id, timeline in enumerate(self._timelines, start=1):
            if turn >= len(timeline):
                continue  # delivered earlier: no longer tracked
            if timeline[turn] != timeline[turn - 1]:
                on_link[self._check_move(turn, drone_id, timeline)] += 1
                movements.append(Movement(drone_id, timeline[turn]))
            in_zone[timeline[turn]] += 1

        for link, count in on_link.items():
            if count > self._link_cap[link]:
                raise RuntimeError(
                    f"Turn {turn}: {count} drones on {'-'.join(sorted(link))}"
                    f" (max_link_capacity={self._link_cap[link]})"
                )
        for name, count in in_zone.items():
            zone = self._map.zones.get(name)  # None: a connection name
            if (zone is not None
                    and name not in (self._map.start.name, self._map.end.name)
                    and count > zone.max_drones):
                raise RuntimeError(
                    f"Turn {turn}: {count} drones in {name}"
                    f" (max_drones={zone.max_drones})"
                )
        return TurnLog(turn=turn, movements=movements)

    def _check_move(
        self, turn: int, drone_id: int, timeline: list[str]
    ) -> frozenset[str]:
        """Controlla la mossa di un drone nel turno; restituisce il link usato.

        I nomi delle zone non contengono mai un trattino, quindi un
        trattino indica un collegamento.
        """
        before, after = timeline[turn - 1], timeline[turn]
        if "-" in before:
            # Landing from a transit, validated when it departed.
            return frozenset(before.split("-"))
        if "-" in after:
            origin, dest = after.split("-")
            legal = (
                origin == before
                and dest in self._adj[before]
                and self._map.zones[dest].zone_type == "restricted"
                and turn + 1 < len(timeline)
                and timeline[turn + 1] == dest
            )
            link = frozenset((origin, dest))
        else:
            legal = (
                after in self._adj[before]
                and self._map.zones[after].zone_type
                not in ("blocked", "restricted")
            )
            link = frozenset((before, after))
        if not legal:
            raise RuntimeError(
                f"Turn {turn}: D{drone_id} cannot move {before} -> {after}"
            )
        return link


class SimulationFilm:
    """Trasforma un log dei turni in una foto delle posizioni per turno.

    Una posizione è il nome di una zona, oppure il nome di un
    collegamento `origine-destinazione` mentre un drone è in viaggio
    verso una zona restricted. I droni che non compaiono in una riga
    restano dove erano al turno prima.
    """

    def __init__(self, log: list[TurnLog], start: str, nb_drones: int) -> None:
        """Collega il film al log dei turni, alla partenza e ai droni."""
        self._log = log
        self._start = start
        self._nb_drones = nb_drones

    def frames(self) -> list[dict[int, str]]:
        """Fotogramma 0 (tutti alla partenza) più uno per ogni turno."""
        current = {i: self._start for i in range(1, self._nb_drones + 1)}
        frames = [dict(current)]
        for turn in self._log:
            for move in turn.movements:
                current[move.drone_id] = move.destination
            frames.append(dict(current))
        return frames
