"""Tests for src.pathfinding.PathFinder."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.graph import ZoneGraph
from src.parser import MapParser
from src.pathfinding import PathFinder

_LINE_MAP = (
    "nb_drones: 1\n"
    "start_hub: a 0 0\n"
    "end_hub: b 3 0\n"
    "hub: c 1 0\n"
    "hub: d 2 0\n"
    "connection: a-c\n"
    "connection: c-d\n"
    "connection: d-b\n"
)

_DISCONNECTED_MAP = (
    "nb_drones: 1\n"
    "start_hub: a 0 0\n"
    "end_hub: b 9 9\n"
    "hub: island 5 5\n"
    "connection: a-island\n"
)

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


def _finder(write_map: Callable[..., Path], content: str) -> PathFinder:
    path = write_map(content)
    map_file = MapParser().parse(path)
    return PathFinder(ZoneGraph(map_file))


class TestPathFinder:
    def test_shortest_path_on_a_line(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _LINE_MAP)
        result = finder.shortest_path("a", "b")
        assert result is not None
        path, cost = result
        assert path == ["a", "c", "d", "b"]
        assert cost == 3.0

    def test_no_path_returns_none(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _DISCONNECTED_MAP)
        assert finder.shortest_path("a", "b") is None

    def test_k_shortest_paths_yields_nothing_on_no_path(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _DISCONNECTED_MAP)
        assert list(finder.k_shortest_paths("a", "b", 4)) == []

    def test_k_shortest_paths_finds_both_fork_branches(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _FORK_MAP)
        paths = list(finder.k_shortest_paths("a", "b", 2))
        assert len(paths) == 2
        assert {tuple(p) for p in paths} == {
            ("a", "up", "b"),
            ("a", "down", "b"),
        }

    def test_k_shortest_paths_finds_every_parallel_corridor(
        self, write_map: Callable[..., Path]
    ) -> None:
        """Single-edge detours alone only ever found two of these three."""
        finder = _finder(
            write_map,
            "nb_drones: 3\nstart_hub: s 0 0\nend_hub: e 2 0\n"
            + "".join(
                f"hub: {z} 1 {i}\nconnection: s-{z}\nconnection: {z}-e\n"
                for i, z in enumerate("abc")
            ),
        )
        assert len(finder.k_shortest_paths("s", "e", 3)) == 3


class TestPathCost:
    def test_path_cost_charges_per_zone_entered(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _LINE_MAP)
        assert finder.path_cost(["a", "c", "d", "b"]) == 3.0
        assert finder.path_cost(["a", "c"]) == 1.0
        assert finder.path_cost(["a"]) == 0.0
