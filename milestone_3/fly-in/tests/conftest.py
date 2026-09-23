"""Shared pytest fixtures and helpers for the Fly-in test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.graph import ZoneGraph
from src.parser import MapParser
from src.pathfinding import FlightPlanner
from src.schemas import MapFile


@pytest.fixture
def write_map(tmp_path: Path) -> Callable[..., Path]:
    """Return a helper that writes `.map` text to a temp file."""

    def _write(content: str, name: str = "test.map") -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    return _write


def load_map(
    write_map: Callable[..., Path], content: str, name: str = "test.map"
) -> MapFile:
    """Write `.map` text to a temp file and parse it."""
    return MapParser().parse(write_map(content, name))


def plan_flights(map_file: MapFile) -> list[list[str]]:
    """Plan every drone's timeline the way the CLI does."""
    return FlightPlanner(map_file, ZoneGraph(map_file)).plan()
