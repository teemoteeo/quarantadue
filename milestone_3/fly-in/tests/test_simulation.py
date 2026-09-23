"""Tests for src.simulation.SimulationEngine: movement, capacity, timing rules.

Planned flights must come out of the engine legal, and hand-written
illegal timelines must be rejected, one test per rule. Includes
regression tests for fixed bugs: a drone in flight not counted against
its connection's capacity, and a restricted end zone entered in one turn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.schemas import MapFile
from src.simulation import SimulationEngine, TurnLog
from tests.conftest import plan_flights, load_map


def _movements_by_zone(log: list[TurnLog]) -> dict[str, list[int]]:
    """Map each destination token to the list of turns a drone landed there."""
    landings: dict[str, list[int]] = {}
    for turn_log in log:
        for move in turn_log.movements:
            landings.setdefault(move.destination, []).append(turn_log.turn)
    return landings


def _run(map_file: MapFile) -> list[TurnLog]:
    paths = plan_flights(map_file)
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

    def test_restricted_zone_never_holds_more_than_its_capacity(
        self, write_map: Callable[..., Path]
    ) -> None:
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
        landings = _movements_by_zone(_run(map_file))
        assert len(landings["c"]) == len(set(landings["c"]))


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


_RULES_MAP = (
    "nb_drones: 2\n"
    "start_hub: s 0 0\n"
    "hub: a 1 0\n"
    "hub: r 1 1 [zone=restricted]\n"
    "hub: x 1 2 [zone=blocked]\n"
    "end_hub: e 2 0\n"
    "connection: s-a\n"
    "connection: s-r\n"
    "connection: s-x\n"
    "connection: a-e\n"
    "connection: r-e\n"
    "connection: x-e\n"
)


class TestEngineRejectsIllegalPlans:
    @pytest.mark.parametrize(
        ("timelines", "error"),
        [
            ([["s", "a", "e"], ["s", "a", "e"]], "on a-s|on s-a"),
            ([["s", "a", "e"], ["s", "s", "a", "e"]], None),
            ([["s", "e"], ["s", "a", "e"]], "cannot move s -> e"),
            ([["s", "x", "e"], ["s", "a", "e"]], "cannot move s -> x"),
            ([["s", "r", "e"], ["s", "a", "e"]], "cannot move s -> r"),
            ([["s", "s-r", "s-r", "r", "e"], ["s", "a", "e"]],
             "cannot move s -> s-r"),
            ([["s", "a"], ["s", "a", "e"]], "must fly"),
        ],
    )
    def test_rule(
        self,
        write_map: Callable[..., Path],
        timelines: list[list[str]],
        error: str | None,
    ) -> None:
        map_file = load_map(write_map, _RULES_MAP)
        engine = SimulationEngine(map_file, timelines)
        if error is None:
            assert len(engine.run()) == 3
        else:
            with pytest.raises(RuntimeError, match=error):
                engine.run()

    def test_zone_capacity_counts_after_departures(
        self, write_map: Callable[..., Path]
    ) -> None:
        """D2 enters `a` on the same turn D1 leaves it: legal."""
        map_file = load_map(write_map, _RULES_MAP)
        engine = SimulationEngine(
            map_file, [["s", "a", "e"], ["s", "s", "a", "e"]]
        )
        assert [str(m) for m in engine.run()[1].movements] == [
            "D1-e", "D2-a"
        ]

    def test_zone_over_capacity_is_rejected(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 2\nstart_hub: s 0 0\nhub: a 1 0\nend_hub: e 2 0\n"
            "connection: s-a [max_link_capacity=2]\n"
            "connection: a-e [max_link_capacity=2]\n",
        )
        engine = SimulationEngine(map_file, [["s", "a", "e"]] * 2)
        with pytest.raises(RuntimeError, match="2 drones in a"):
            engine.run()
