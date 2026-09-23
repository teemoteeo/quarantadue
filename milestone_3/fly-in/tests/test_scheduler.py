"""Tests for src.simulation.RouteScheduler: splitting the fleet over routes."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.graph import ZoneGraph
from src.pathfinding import PathFinder
from src.simulation import RouteScheduler, SimulationEngine
from tests.conftest import assign_routes, load_map

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


_SHORT_ROUTE = ["a", "short", "b"]
_LONG_ROUTE = ["a"] + [f"d{i}" for i in range(1, 11)] + ["b"]

_DISCONNECTED_MAP = (
    "nb_drones: 1\n"
    "start_hub: a 0 0\n"
    "end_hub: b 9 9\n"
    "hub: island 5 5\n"
    "connection: a-island\n"
)


def _assign(write_map: Callable[..., Path], text: str) -> list[list[str]]:
    return assign_routes(load_map(write_map, text))


class TestAssignment:
    def test_no_route_at_all_raises(
        self, write_map: Callable[..., Path]
    ) -> None:
        with pytest.raises(ValueError, match="No path"):
            RouteScheduler(load_map(write_map, _DISCONNECTED_MAP), [])

    def test_one_path_per_drone(
        self, write_map: Callable[..., Path]
    ) -> None:
        assert len(_assign(write_map, _lopsided(7))) == 7

    def test_fork_is_split_because_sharing_one_branch_queues(
        self, write_map: Callable[..., Path]
    ) -> None:
        paths = _assign(write_map, _FORK_MAP)
        assert paths[0] != paths[1]

    def test_small_fleet_all_takes_the_short_route(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Queueing on the 2-turn route beats the 11-turn detour."""
        assert _assign(write_map, _lopsided(4)) == [_SHORT_ROUTE] * 4

    def test_large_fleet_spills_onto_the_long_route(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Once the short route's queue outlasts the detour, it wins."""
        paths = _assign(write_map, _lopsided(20))
        short, long = paths.count(_SHORT_ROUTE), paths.count(_LONG_ROUTE)
        assert short + long == 20
        assert long > 0, "detour never used, so the queue is not being scored"
        assert short > long, "detour used more than the route twice as cheap"

    def test_never_worse_than_piling_onto_the_cheapest_route(
        self, write_map: Callable[..., Path]
    ) -> None:
        """The hill climb only ever moves a drone if the turn count drops.

        This is the regression guard for the cost model it replaced,
        which sent drones down a second route whenever its queue looked
        cheaper — ignoring that the routes share zones, which cost
        hard_01.map two extra turns.
        """
        map_file = load_map(write_map, _lopsided(4))
        finder = PathFinder(ZoneGraph(map_file))
        routes = list(finder.k_shortest_paths("a", "b", 4))
        naive = [list(routes[0])] * 4
        chosen = RouteScheduler(map_file, routes).assign()
        assert len(SimulationEngine(map_file, chosen).run()) <= len(
            SimulationEngine(map_file, naive).run()
        )

    def test_fleet_spreads_evenly_over_parallel_corridors(
        self, write_map: Callable[..., Path]
    ) -> None:
        """30 drones, 3 capacity-1 corridors: 10 per corridor, 11 turns.

        Moving one drone at a time never lowers the longest queue here;
        the delivery-turn tie-break is what gets past [15, 15, 0].
        """
        map_file = load_map(
            write_map,
            "nb_drones: 30\nstart_hub: s 0 0\nend_hub: e 2 0\n"
            + "".join(
                f"hub: {z} 1 {i}\nconnection: s-{z}\nconnection: {z}-e\n"
                for i, z in enumerate("abc")
            ),
        )
        paths = assign_routes(map_file)
        assert len(SimulationEngine(map_file, paths).run()) == 11
