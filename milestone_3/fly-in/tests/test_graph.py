"""Tests for src.graph.ZoneGraph: adjacency and movement costs."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.graph import ZoneGraph
from src.parser import MapParser

_MAP = (
    "nb_drones: 1\n"
    "start_hub: a 0 0\n"
    "end_hub: z 4 0\n"
    "hub: n 1 0 [zone=normal]\n"
    "hub: r 1 1 [zone=restricted]\n"
    "hub: p 1 2 [zone=priority]\n"
    "hub: blk 1 3 [zone=blocked]\n"
    "connection: a-n\n"
    "connection: a-r\n"
    "connection: a-p\n"
    "connection: a-blk [max_link_capacity=3]\n"
    "connection: n-z\n"
    "connection: r-z\n"
    "connection: p-z\n"
)


def _build_graph(write_map: Callable[..., Path]) -> ZoneGraph:
    path = write_map(_MAP)
    map_file = MapParser().parse(path)
    return ZoneGraph(map_file)


class TestZoneGraph:
    def test_normal_zone_cost_is_one(
        self, write_map: Callable[..., Path]
    ) -> None:
        graph = _build_graph(write_map)
        assert graph.cost("n") == 1.0

    def test_restricted_zone_cost_is_two(
        self, write_map: Callable[..., Path]
    ) -> None:
        graph = _build_graph(write_map)
        assert graph.cost("r") == 2.0

    def test_priority_zone_is_cheaper_than_normal(
        self, write_map: Callable[..., Path]
    ) -> None:
        graph = _build_graph(write_map)
        assert graph.cost("p") < graph.cost("n")

    def test_blocked_zone_excluded_from_neighbours(
        self, write_map: Callable[..., Path]
    ) -> None:
        graph = _build_graph(write_map)
        assert set(graph.neighbours("a")) == {"n", "r", "p"}

    def test_zone_type_lookup(self, write_map: Callable[..., Path]) -> None:
        graph = _build_graph(write_map)
        assert graph.zone_type("r") == "restricted"
        assert graph.zone_type("n") == "normal"
