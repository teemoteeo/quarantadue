"""Tests for src.pathfinding.FlightPlanner: routing the fleet through time."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.pathfinding import FlightPlanner
from src.simulation import SimulationEngine
from tests.conftest import load_map, plan_flights

_FORK_MAP = (
    "nb_drones: 2\n"
    "start_hub: a 0 0\n"
    "end_hub: b 3 0\n"
    "hub: up 1 1\n"
    "hub: down 1 -1\n"
    "connection: a-up\n"
    "connection: a-down\n"
    "connection: up-b\n"
    "connection: down-b\n"
)

# The short route costs 2 turns and carries one drone per turn; the
# detour costs 11 but is otherwise empty.


def _lopsided(nb_drones: int) -> str:
    return (
        f"nb_drones: {nb_drones}\n"
        "start_hub: a 0 0\n"
        "end_hub: b 9 0\n"
        "hub: short 1 0\n"
        + "".join(f"hub: d{i} {i} 1\n" for i in range(1, 11))
        + "connection: a-short\n"
        "connection: short-b\n"
        "connection: a-d1\n"
        + "".join(f"connection: d{i}-d{i + 1}\n" for i in range(1, 10))
        + "connection: d10-b\n"
    )


def _route(timeline: list[str]) -> list[str]:
    """The zones a timeline passes through, without waits or transits."""
    return [
        pos for i, pos in enumerate(timeline)
        if "-" not in pos and (i == 0 or pos != timeline[i - 1])
    ]


def _plan(write_map: Callable[..., Path], text: str) -> list[list[str]]:
    return plan_flights(load_map(write_map, text))


class TestPlanner:
    def test_no_path_at_all_raises(
        self, write_map: Callable[..., Path]
    ) -> None:
        map_file = load_map(
            write_map,
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 9 9\n"
            "hub: island 5 5\nconnection: a-island\n",
        )
        with pytest.raises(ValueError, match="No path"):
            FlightPlanner(map_file).plan()

    def test_one_timeline_per_drone_from_start_to_end(
        self, write_map: Callable[..., Path]
    ) -> None:
        timelines = _plan(write_map, _lopsided(7))
        assert len(timelines) == 7
        assert all(t[0] == "a" and t[-1] == "b" for t in timelines)

    def test_fork_is_split_because_sharing_one_branch_queues(
        self, write_map: Callable[..., Path]
    ) -> None:
        first, second = _plan(write_map, _FORK_MAP)
        assert _route(first) != _route(second)

    def test_small_fleet_all_takes_the_short_route(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Queueing on the 2-turn route beats the 11-turn detour."""
        routes = [_route(t) for t in _plan(write_map, _lopsided(4))]
        assert routes == [["a", "short", "b"]] * 4

    def test_large_fleet_spills_onto_the_long_route(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Once the short route's queue outlasts the detour, it wins."""
        routes = [_route(t) for t in _plan(write_map, _lopsided(20))]
        short = routes.count(["a", "short", "b"])
        assert 0 < 20 - short < short

    def test_fleet_spreads_evenly_over_parallel_corridors(
        self, write_map: Callable[..., Path]
    ) -> None:
        """30 drones, 3 capacity-1 corridors: 10 per corridor, 11 turns."""
        map_file = load_map(
            write_map,
            "nb_drones: 30\nstart_hub: s 0 0\nend_hub: e 2 0\n"
            + "".join(
                f"hub: {z} 1 {i}\nconnection: s-{z}\nconnection: {z}-e\n"
                for i, z in enumerate("abc")
            ),
        )
        log = SimulationEngine(map_file, plan_flights(map_file)).run()
        assert len(log) == 11

    def test_priority_zone_wins_a_tie(
        self, write_map: Callable[..., Path]
    ) -> None:
        timelines = _plan(
            write_map,
            "nb_drones: 1\nstart_hub: s 0 0\nend_hub: e 2 0\n"
            "hub: plain 1 0\nhub: fast 1 1 [zone=priority]\n"
            "connection: s-plain\nconnection: plain-e\n"
            "connection: s-fast\nconnection: fast-e\n",
        )
        assert timelines == [["s", "fast", "e"]]

    def test_waits_instead_of_colliding_in_a_restricted_zone(
        self, write_map: Callable[..., Path]
    ) -> None:
        """The second drone waits at the start rather than landing on a
        full restricted zone: it cannot wait mid-flight."""
        timelines = _plan(
            write_map,
            "nb_drones: 2\nstart_hub: s 0 0\nend_hub: e 2 0\n"
            "hub: r 1 0 [zone=restricted]\n"
            "connection: s-r [max_link_capacity=2]\nconnection: r-e\n",
        )
        assert timelines == [
            ["s", "s-r", "r", "e"],
            ["s", "s", "s-r", "r", "e"],
        ]
