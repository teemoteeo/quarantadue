"""Tests for src.pathfinding.PathFinder: static distances and costs."""

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
    "hub: d 2 0 [zone=restricted]\n"
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


def _finder(write_map: Callable[..., Path], content: str) -> PathFinder:
    path = write_map(content)
    map_file = MapParser().parse(path)
    return PathFinder(ZoneGraph(map_file))


class TestDistances:
    def test_distance_charges_the_zone_being_entered(
        self, write_map: Callable[..., Path]
    ) -> None:
        dist = _finder(write_map, _LINE_MAP).distances_to("b")
        # d is restricted: entering it from c costs 2.
        assert dist == {"b": 0.0, "d": 1.0, "c": 3.0, "a": 4.0}

    def test_unreachable_zones_are_absent(
        self, write_map: Callable[..., Path]
    ) -> None:
        dist = _finder(write_map, _DISCONNECTED_MAP).distances_to("b")
        assert dist == {"b": 0.0}


class TestPathCost:
    def test_path_cost_charges_per_zone_entered(
        self, write_map: Callable[..., Path]
    ) -> None:
        finder = _finder(write_map, _LINE_MAP)
        assert finder.path_cost(["a", "c", "d", "b"]) == 4.0
        assert finder.path_cost(["a", "c"]) == 1.0
        assert finder.path_cost(["a"]) == 0.0
