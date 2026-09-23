"""Tests for src.simulation.SimulationEngine: movement, capacity, timing rules.

Includes regression tests for fixed bugs: a restricted zone's capacity
not reserved on departure, a drone in flight not counted against its
connection's capacity, and a restricted end zone entered in one turn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.schemas import MapFile
from src.simulation import SimulationEngine, TurnLog
from tests.conftest import assign_routes, load_map


def _movements_by_zone(log: list[TurnLog]) -> dict[str, list[int]]:
    """Map each destination token to the list of turns a drone landed there."""
    landings: dict[str, list[int]] = {}
    for turn_log in log:
        for move in turn_log.movements:
            landings.setdefault(move.destination, []).append(turn_log.turn)
    return landings


def _run(map_file: MapFile) -> list[TurnLog]:
    paths = assign_routes(map_file)
    return SimulationEngine(map_file, paths).run()


class TestBasicMovement:
    def test_single_drone_straight_line_takes_three_turns(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 3 0\n"
            "hub: c 1 0\n"
            "hub: d 2 0\n"
            "connection: a-c\n"
            "connection: c-d\n"
            "connection: d-b\n",
        )
        log = _run(map_file)
        assert len(log) == 3
        assert [str(m) for m in log[-1].movements] == ["D1-b"]

    def test_two_drones_share_capacity_one_corridor_without_collision(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: b 2 0\n"
            "hub: c 1 0\n"
            "connection: a-c\n"
            "connection: c-b\n",
        )
        log = _run(map_file)
        landings = _movements_by_zone(log)
        # capacity 1: the two drones must never land on c on the same turn
        assert len(landings["c"]) == len(set(landings["c"]))
        # a departure frees capacity the same turn, so the second drone
        # can enter c the instant the first leaves for b: 3 turns total
        assert len(log) == 3

    def test_fork_distributes_drones_faster_than_single_corridor(
        self, write_map: Callable[..., Path]
    ) -> None:
        corridor = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: b 2 0\n"
            "hub: c 1 0\n"
            "connection: a-c\n"
            "connection: c-b\n",
            "corridor.map",
        )
        fork = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: b 3 0\n"
            "hub: up 1 1\n"
            "hub: down 1 -1\n"
            "connection: a-up\n"
            "connection: a-down\n"
            "connection: up-b\n"
            "connection: down-b\n",
            "fork.map",
        )
        corridor_turns = len(_run(corridor))
        fork_turns = len(_run(fork))
        assert fork_turns < corridor_turns


class TestRestrictedZoneTiming:
    def test_restricted_zone_entry_shows_connection_then_arrival(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 2 0\n"
            "hub: c 1 0 [zone=restricted]\n"
            "connection: a-c\n"
            "connection: c-b\n",
        )
        log = _run(map_file)
        all_moves = [str(m) for turn in log for m in turn.movements]
        assert "D1-a-c" in all_moves
        assert "D1-c" in all_moves
        # the connection token must appear strictly before the zone arrival
        assert all_moves.index("D1-a-c") < all_moves.index("D1-c")
        assert len(log) >= 3

    def test_restricted_zone_capacity_is_reserved_on_departure(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Regression test: two drones must not both occupy a capacity-1
        restricted zone even though they depart toward it on the same turn.
        """
        map_file = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: z 5 0\n"
            "hub: c 2 0 [zone=restricted max_drones=1]\n"
            "hub: p1 1 0\n"
            "hub: p2 1 1\n"
            "hub: q 3 0\n"
            "connection: a-p1\n"
            "connection: a-p2\n"
            "connection: p1-c\n"
            "connection: p2-c\n"
            "connection: c-q\n"
            "connection: q-z\n",
        )
        log = _run(map_file)
        landings = _movements_by_zone(log)
        assert len(landings["c"]) == len(set(landings["c"])), (
            "both drones landed on the capacity-1 restricted zone "
            "on the same turn"
        )


class TestDeterminism:
    def test_same_map_gives_same_turn_count_every_run(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 4\n"
            "start_hub: a 0 0\n"
            "end_hub: b 3 0\n"
            "hub: up 1 1\n"
            "hub: down 1 -1\n"
            "connection: a-up\n"
            "connection: a-down\n"
            "connection: up-b\n"
            "connection: down-b\n",
        )
        turn_counts = {len(_run(map_file)) for _ in range(3)}
        assert len(turn_counts) == 1


class TestTransitRules:
    def test_drone_in_flight_still_occupies_its_connection(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Nobody may start down a capacity-1 link while a drone is on it."""
        map_file = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: s 0 0\n"
            "hub: r 1 0 [zone=restricted max_drones=2]\n"
            "end_hub: e 2 0\n"
            "connection: s-r\n"
            "connection: r-e\n",
        )
        for turn in _run(map_file):
            tokens = {str(m) for m in turn.movements}
            assert not {"D1-r", "D2-s-r"} <= tokens

    def test_restricted_end_zone_takes_two_turns(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 1\n"
            "start_hub: s 0 0\n"
            "end_hub: e 1 0 [zone=restricted]\n"
            "connection: s-e\n",
        )
        log = _run(map_file)
        assert [[str(m) for m in t.movements] for t in log] == [
            ["D1-s-e"], ["D1-e"]
        ]


class TestDeadlock:
    def test_head_on_drones_raise_instead_of_spinning(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 2\n"
            "start_hub: s 0 0\n"
            "hub: a 1 0\n"
            "hub: b 1 1\n"
            "end_hub: e 2 0\n"
            "connection: s-a\n"
            "connection: s-b\n"
            "connection: a-b\n"
            "connection: a-e\n"
            "connection: b-e\n",
        )
        engine = SimulationEngine(
            map_file, [["s", "a", "b", "e"], ["s", "b", "a", "e"]]
        )
        with pytest.raises(RuntimeError, match="Deadlock at turn 2"):
            engine.run()
