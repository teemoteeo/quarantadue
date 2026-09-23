"""Turn-based simulation engine for drone movement through zones.

The simulation proceeds in discrete turns. At each turn:

1. **Phase 1 — Arrivals**: IN_FLIGHT drones (in transit to restricted zones)
   MUST arrive at their destination this turn.

2. **Phase 2 — Movement**: WAITING drones attempt to move to their next zone.
   Normal/priority zones: drone arrives immediately (1-turn move).
   Restricted zones: drone enters transit and MUST arrive next turn (2-turn).
   Zone and connection capacities are checked.

Key rules from the subject:
- Drones moving out of a zone free up capacity for that SAME turn.
- Zone capacity is checked AFTER departures are accounted for.
- Restricted zone transit: drone occupies connection, must arrive next turn.
- Blocked zones are never entered (pathfinding excludes them).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import permutations

from .schemas import MapFile


class DroneState(Enum):
    """Lifecycle state of a single drone within the simulation."""

    WAITING = auto()    # at a zone, ready to move
    IN_FLIGHT = auto()  # in transit to restricted zone, arrives next turn
    DELIVERED = auto()  # reached end zone


@dataclass
class Drone:
    """Mutable runtime state for one drone as it traverses its path."""

    drone_id: int
    position: str
    state: DroneState = DroneState.WAITING
    path: list[str] = field(default_factory=list)
    path_index: int = 0


@dataclass(frozen=True)
class Movement:
    """One drone's destination on a single turn.

    `destination` is a zone name, or an `origin-dest` connection name
    while the drone is in transit toward a restricted zone. Keeping the
    drone id as a field rather than baking it into a string means
    consumers read it directly instead of re-parsing the rendered token,
    which is ambiguous for connection names (``D3-a-b``).
    """

    drone_id: int
    destination: str

    def __str__(self) -> str:
        """Render the subject's `D<id>-<destination>` output token."""
        return f"D{self.drone_id}-{self.destination}"


@dataclass
class TurnLog:
    """The set of drone movements that occurred during one simulation turn."""

    turn: int
    movements: list[Movement]


class SimulationEngine:
    """Turn-based engine that replays drone paths under capacity rules.

    Given a parsed map and one path per drone, advances the simulation
    turn by turn (see :meth:`step`), enforcing zone and connection
    capacity, restricted-zone transit timing, and deadlock detection.

    Every turn either moves a drone forward along its finite path or
    raises, so :meth:`run` always terminates.
    """

    def __init__(
        self,
        map_file: MapFile,
        drone_paths: list[list[str]],
    ) -> None:
        """Initialise per-zone capacity/occupancy state and place drones.

        Args:
            map_file: The parsed map describing zones and connections.
            drone_paths: One precomputed route per drone, each starting
                at the map's start zone.
        """
        self._nb_drones = map_file.nb_drones
        self._end_name = map_file.end.name

        zones = map_file.zones
        self._zone_capacity = {n: z.max_drones for n, z in zones.items()}
        self._zone_type = {n: z.zone_type for n, z in zones.items()}
        self._zone_occupancy = dict.fromkeys(zones, 0)

        # Start/end have unlimited capacity
        self._zone_capacity[map_file.start.name] = map_file.nb_drones
        self._zone_capacity[map_file.end.name] = map_file.nb_drones
        self._zone_occupancy[map_file.start.name] = map_file.nb_drones

        self._conn_capacity: dict[tuple[str, str], int] = {}
        for conn in map_file.connections:
            key = self._link_key(conn.from_zone, conn.to_zone)
            self._conn_capacity[key] = conn.max_link_capacity

        # Dict order is drone-id order, which keeps every turn deterministic.
        self._drones: dict[int, Drone] = {
            drone_id: Drone(
                drone_id=drone_id,
                position=map_file.start.name,
                path=list(path),
                path_index=1,  # next zone to move to (index 0 is start)
            )
            for drone_id, path in enumerate(drone_paths, start=1)
        }

        self._turn: int = 0
        self._log: list[TurnLog] = []
        self._completed: bool = False

    @staticmethod
    def _link_key(a: str, b: str) -> tuple[str, str]:
        """Return a direction-independent key identifying a connection."""
        return (min(a, b), max(a, b))

    @property
    def delivered_count(self) -> int:
        """How many drones have reached the end zone."""
        return sum(
            1 for d in self._drones.values()
            if d.state == DroneState.DELIVERED
        )

    def step(self) -> None:
        """Advance the simulation by one turn.

        Zone capacity for a restricted-zone destination is reserved the
        moment a drone departs toward it (when it becomes IN_FLIGHT), not
        when it physically arrives two turns later. Without this
        reservation, several drones could depart toward the same
        capacity-limited restricted zone on the same turn and all arrive
        together next turn, exceeding its max_drones — the reservation
        below is what prevents that.
        """
        if self._completed:
            return

        self._turn += 1
        movements: list[Movement] = []

        # Track which zones drones are leaving (for capacity calculation)
        departures: dict[str, int] = defaultdict(int)
        # Track connection usage this turn
        conn_usage: dict[tuple[str, str], int] = defaultdict(int)

        # === Phase 1: IN_FLIGHT drones MUST arrive this turn ===
        # Their destination capacity was already reserved when they departed
        # (see Phase 2), and their origin zone was already freed at that
        # same time, so this phase only updates position/state — it must
        # not touch occupancy again. They are still on the connection
        # this turn, though, so they count against its capacity.
        arrived_this_turn: set[int] = set()
        for drone in self._drones.values():
            if drone.state != DroneState.IN_FLIGHT:
                continue

            next_pos = drone.path[drone.path_index]
            conn_usage[self._link_key(drone.position, next_pos)] += 1
            drone.position = next_pos
            drone.path_index += 1

            if next_pos == self._end_name:
                drone.state = DroneState.DELIVERED
            else:
                drone.state = DroneState.WAITING
                arrived_this_turn.add(drone.drone_id)
            movements.append(Movement(drone.drone_id, next_pos))

        # === Phase 2: WAITING drones attempt to move ===
        for drone in self._drones.values():
            if drone.state != DroneState.WAITING:
                continue
            if drone.drone_id in arrived_this_turn:
                continue  # just arrived, can't move again this turn

            next_pos = drone.path[drone.path_index]

            # Effective occupancy = current occupancy - drones leaving
            effective_occ = (
                self._zone_occupancy[next_pos] - departures[next_pos]
            )
            if effective_occ >= self._zone_capacity[next_pos]:
                continue

            link_key = self._link_key(drone.position, next_pos)
            if conn_usage[link_key] >= self._conn_capacity[link_key]:
                continue

            conn_usage[link_key] += 1
            departures[drone.position] += 1
            # Reserve the destination slot immediately so any other drone
            # evaluated later this same phase sees accurate occupancy —
            # this applies to restricted destinations too, since without
            # it multiple drones could depart toward the same
            # capacity-limited restricted zone on the same turn.
            self._zone_occupancy[next_pos] += 1

            if self._zone_type[next_pos] == "restricted":
                # 2-turn move: start transit, arrive next turn.
                # `position` intentionally stays at the origin zone until
                # Phase 1 of the next turn resolves the arrival.
                drone.state = DroneState.IN_FLIGHT
                movements.append(
                    Movement(
                        drone.drone_id, f"{drone.position}-{next_pos}"
                    )
                )
            else:
                # 1-turn move: arrive immediately
                drone.position = next_pos
                drone.path_index += 1
                if next_pos == self._end_name:
                    drone.state = DroneState.DELIVERED
                movements.append(Movement(drone.drone_id, next_pos))

        for zone_name, count in departures.items():
            self._zone_occupancy[zone_name] -= count

        # === Phase 3: Deadlock detection ===
        # Nothing moved, so nothing changed: every later turn would be
        # this same empty one.
        if not movements:
            raise RuntimeError(
                f"Deadlock at turn {self._turn}: "
                f"{self._nb_drones - self.delivered_count} drones all blocked"
            )

        if self.delivered_count >= self._nb_drones:
            self._completed = True

        self._log.append(TurnLog(turn=self._turn, movements=movements))

    def run(self) -> list[TurnLog]:
        """Step the simulation until all drones are delivered.

        Returns:
            The full per-turn movement log.

        Raises:
            RuntimeError: On a deadlock.
        """
        while not self._completed:
            self.step()
        return self._log


class RouteScheduler:
    """Decides how many drones take each candidate route.

    The routes pathfinding returns are not independent — they share
    zones — so "spreading the fleet" can buy contention instead of
    parallelism, and the cheapest route is not always the wrong one to
    pile onto. Rather than estimate that with a cost model, this
    scheduler *runs* the simulation to score a candidate split: the
    engine is the only thing that knows about zone capacity, shared
    zones and restricted-zone timing, and one run is cheap enough to
    call in a loop.

    It starts with every drone on the cheapest route, then moves `step`
    drones between routes for as long as that lowers the score, halving
    `step` (from half the fleet down to one) whenever no move helps. The
    score is total turns, ties broken by the sum of every drone's
    delivery turn: draining the longest queue into an empty route only
    pays off one move later, and the tie-break is what takes that step.
    """

    def __init__(self, map_file: MapFile, routes: list[list[str]]) -> None:
        """Bind the scheduler to a map and its candidate routes.

        Raises:
            ValueError: If pathfinding found no route at all.
        """
        if not routes:
            raise ValueError(
                f"No path from {map_file.start.name!r} "
                f"to {map_file.end.name!r}"
            )
        self._map = map_file
        self._routes = routes

    def assign(self) -> list[list[str]]:
        """Return one route per drone, chosen to minimise total turns."""
        split = [self._map.nb_drones] + [0] * (len(self._routes) - 1)
        best = self._score(split)
        step = max(1, self._map.nb_drones // 2)
        while step:
            improved = False
            for source, target in permutations(range(len(self._routes)), 2):
                if split[source] < step:
                    continue
                trial = list(split)
                trial[source] -= step
                trial[target] += step
                score = self._score(trial)
                if score < best:
                    best, split, improved = score, trial, True
                    break
            if not improved:
                step //= 2
        return self._paths(split)

    def _paths(self, split: list[int]) -> list[list[str]]:
        """Expand a per-route drone count into one path per drone."""
        return [
            list(self._routes[index])
            for index, count in enumerate(split)
            for _ in range(count)
        ]

    def _score(self, split: list[int]) -> tuple[float, float]:
        """(total turns, sum of delivery turns); infinite on deadlock."""
        try:
            log = SimulationEngine(self._map, self._paths(split)).run()
        except RuntimeError:
            return math.inf, math.inf
        delivered_at = {
            move.drone_id: turn.turn
            for turn in log for move in turn.movements
        }
        return len(log), sum(delivered_at.values())


class SimulationFilm:
    """Replays a turn log into one drone-position snapshot per turn.

    A position is a zone name, or an `origin-dest` connection name while
    a drone is in transit toward a restricted zone. Drones omitted from
    a turn line keep the position they held on the previous turn.
    """

    def __init__(self, log: list[TurnLog], start: str, nb_drones: int) -> None:
        """Bind the film to a turn log, the start zone, and drone count."""
        self._log = log
        self._start = start
        self._nb_drones = nb_drones

    def frames(self) -> list[dict[int, str]]:
        """Return frame 0 (all drones at start) plus one frame per turn."""
        current = {i: self._start for i in range(1, self._nb_drones + 1)}
        frames = [dict(current)]
        for turn in self._log:
            for move in turn.movements:
                current[move.drone_id] = move.destination
            frames.append(dict(current))
        return frames
