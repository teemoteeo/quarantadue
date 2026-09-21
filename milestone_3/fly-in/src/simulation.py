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
- Blocked zones are never entered (parser prevents, pathfinding excludes).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
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
    flight_connection: str = ""


@dataclass
class TurnLog:
    """The set of drone movements that occurred during one simulation turn."""

    turn: int
    movements: list[str]


class SimulationEngine:
    """Turn-based engine that replays drone paths under capacity rules.

    Given a parsed map and one path per drone, advances the simulation
    turn by turn (see :meth:`step`), enforcing zone and connection
    capacity, restricted-zone transit timing, and deadlock detection.
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
        self._start_name = map_file.start.name
        self._end_name = map_file.end.name

        self._zone_capacity: dict[str, int] = {}
        self._zone_occupancy: dict[str, int] = {}
        self._zone_type: dict[str, str] = {}

        for name, zone in map_file.zones.items():
            self._zone_capacity[name] = zone.metadata.max_drones
            self._zone_occupancy[name] = 0
            self._zone_type[name] = zone.metadata.zone

        # Start/end have unlimited capacity
        self._zone_capacity[map_file.start.name] = 99999
        self._zone_capacity[map_file.end.name] = 99999
        self._zone_type[map_file.start.name] = "normal"
        self._zone_type[map_file.end.name] = "normal"
        self._zone_occupancy[map_file.start.name] = map_file.nb_drones

        self._conn_capacity: dict[tuple[str, str], int] = {}
        for conn in map_file.connections:
            key = self._link_key(conn.from_zone, conn.to_zone)
            self._conn_capacity[key] = conn.metadata.max_link_capacity

        self._drones: dict[int, Drone] = {}
        for i in range(map_file.nb_drones):
            drone_id = i + 1
            path = drone_paths[i]
            drone = Drone(
                drone_id=drone_id,
                position=map_file.start.name,
                path=list(path),
                path_index=1,  # next zone to move to (index 0 is start)
            )
            self._drones[drone_id] = drone

        self._turn: int = 0
        self._log: list[TurnLog] = []
        self._deadlock_counter: int = 0
        self._completed: bool = False

    @staticmethod
    def _link_key(a: str, b: str) -> tuple[str, str]:
        """Return a direction-independent key identifying a connection."""
        return (min(a, b), max(a, b))

    @property
    def turn(self) -> int:
        """The number of turns simulated so far."""
        return self._turn

    @property
    def delivered_count(self) -> int:
        """How many drones have reached the end zone."""
        return sum(
            1 for d in self._drones.values()
            if d.state == DroneState.DELIVERED
        )

    def step(self) -> bool:
        """Advance one simulation turn. Returns True if simulation complete.

        Zone capacity for a restricted-zone destination is reserved the
        moment a drone departs toward it (when it becomes IN_FLIGHT), not
        when it physically arrives two turns later. Without this
        reservation, several drones could depart toward the same
        capacity-limited restricted zone on the same turn and all arrive
        together next turn, exceeding its max_drones — the reservation
        below is what prevents that.
        """
        if self._completed:
            return True

        self._turn += 1
        movements: list[str] = []

        # Track which zones drones are leaving (for capacity calculation)
        departures: dict[str, int] = defaultdict(int)
        # Track connection usage this turn
        conn_usage: dict[tuple[str, str], int] = defaultdict(int)

        # === Phase 1: IN_FLIGHT drones MUST arrive this turn ===
        # Their destination capacity was already reserved when they departed
        # (see Phase 2), and their origin zone was already freed at that
        # same time, so this phase only updates position/state — it must
        # not touch occupancy again.
        arrived_this_turn: set[int] = set()
        for drone in sorted(self._drones.values(), key=lambda d: d.drone_id):
            if drone.state != DroneState.IN_FLIGHT:
                continue

            next_pos = drone.path[drone.path_index]
            drone.position = next_pos
            drone.path_index += 1
            drone.flight_connection = ""

            if next_pos == self._end_name:
                drone.state = DroneState.DELIVERED
            else:
                drone.state = DroneState.WAITING
                arrived_this_turn.add(drone.drone_id)
            movements.append(f"D{drone.drone_id}-{next_pos}")

        # === Phase 2: WAITING drones attempt to move ===
        # Process in drone ID order for determinism
        for drone in sorted(self._drones.values(), key=lambda d: d.drone_id):
            if drone.state != DroneState.WAITING:
                continue
            if drone.drone_id in arrived_this_turn:
                continue  # just arrived, can't move again this turn
            if drone.path_index >= len(drone.path):
                continue

            next_pos = drone.path[drone.path_index]
            dest_type = self._zone_type.get(next_pos, "normal")

            # Effective occupancy = current occupancy - drones leaving
            effective_occ = (
                self._zone_occupancy.get(next_pos, 0)
                - departures.get(next_pos, 0)
            )
            max_cap = self._zone_capacity.get(next_pos, 1)

            if effective_occ >= max_cap:
                continue

            # Check connection capacity
            link_key = self._link_key(drone.position, next_pos)
            link_cap = self._conn_capacity.get(link_key, 1)
            link_used = conn_usage[link_key]
            if link_used >= link_cap:
                continue

            conn_usage[link_key] += 1
            departures[drone.position] += 1
            # Reserve the destination slot immediately so any other drone
            # evaluated later this same phase sees accurate occupancy —
            # this applies to restricted destinations too, since without
            # it multiple drones could depart toward the same
            # capacity-limited restricted zone on the same turn.
            self._zone_occupancy[next_pos] = (
                self._zone_occupancy.get(next_pos, 0) + 1
            )

            if dest_type == "restricted":
                # 2-turn move: start transit, arrive next turn.
                # `position` intentionally stays at the origin zone until
                # Phase 1 of the next turn resolves the arrival.
                drone.state = DroneState.IN_FLIGHT
                drone.flight_connection = \
                    f"{drone.position}-{next_pos}"
                movements.append(f"D{drone.drone_id}-"
                                 f"{drone.flight_connection}")
            else:
                # 1-turn move: arrive immediately
                drone.position = next_pos
                drone.path_index += 1
                if next_pos == self._end_name:
                    drone.state = DroneState.DELIVERED
                movements.append(f"D{drone.drone_id}-{next_pos}")

        # Apply remaining departures from Phase 2
        for zone_name, count in departures.items():
            prev_occ = self._zone_occupancy.get(zone_name, 0)
            new_occ = prev_occ - count
            self._zone_occupancy[zone_name] = max(0, new_occ)

        # === Phase 3: Deadlock detection ===
        active = [
            d for d in self._drones.values()
            if d.state not in (DroneState.DELIVERED,)
        ]
        if not movements and active:
            self._deadlock_counter += 1
            if self._deadlock_counter > 10:
                raise RuntimeError(
                    f"Deadlock at turn {self._turn}: "
                    f"{len(active)} active drones all blocked"
                )
        else:
            self._deadlock_counter = 0

        # === Check completion ===
        if self.delivered_count >= self._nb_drones:
            self._completed = True

        self._log.append(TurnLog(turn=self._turn, movements=movements))
        return self._completed

    def run(self) -> list[TurnLog]:
        """Step the simulation until all drones are delivered.

        Returns:
            The full per-turn movement log.

        Raises:
            RuntimeError: On a persistent deadlock, or if the simulation
                exceeds a sanity-check turn cap.
        """
        max_turns = 10000
        while not self._completed:
            self.step()
            if self._turn > max_turns:
                raise RuntimeError(
                    f"Simulation exceeded {max_turns} turns"
                )
        return self._log
