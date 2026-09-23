"""Turn-based simulation: replaying planned flights under the rules.

The planner (:class:`~src.pathfinding.FlightPlanner`) decides where each
drone is after every turn. The engine replays those timelines one turn
at a time and enforces every movement and capacity rule of the subject,
so an illegal plan fails loudly instead of printing an invalid log.

Key rules from the subject:
- Drones moving out of a zone free up capacity for that SAME turn.
- Zone capacity is checked AFTER departures are accounted for.
- Restricted zone transit: drone occupies connection, must arrive next turn.
- Blocked zones are never entered.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .schemas import MapFile


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
    """Replays one planned timeline per drone, enforcing the rules.

    Each turn, every drone moves to its next planned position, and the
    turn is checked as a whole:

    - a move follows a connection and never enters a blocked zone;
    - a restricted zone is entered only through a transit on its
      connection (`D1-a-b`), and the drone lands on the very next turn;
    - drones on each connection during the turn, and in each zone after
      it (start and end excepted), stay within capacity.

    Occupancy is counted after all moves, so a drone leaving a zone frees
    its slot for another entering on the same turn.
    """

    def __init__(self, map_file: MapFile, timelines: list[list[str]]) -> None:
        """Bind the engine to a map and one timeline per drone.

        Args:
            map_file: The parsed map describing zones and connections.
            timelines: Per drone, its position after each turn: a zone,
                or an `origin-dest` connection while in transit toward a
                restricted zone. Index 0 is the start zone.
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
        """Replay every turn until the last drone is delivered.

        Returns:
            The full per-turn movement log.

        Raises:
            RuntimeError: If a timeline breaks a movement or capacity rule.
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
        """Move every drone still flying one turn, and check the result."""
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
        """Validate one drone's move this turn; return the link it uses.

        Zone names never contain a dash, so a dash marks a connection.
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
