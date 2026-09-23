"""Domain models for the Fly-in drone simulation.

Plain frozen dataclasses; :class:`~src.parser.MapParser` validates every
field before a model is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ZoneType = Literal["normal", "blocked", "restricted", "priority"]


@dataclass(frozen=True)
class Zone:
    """A zone (node) in the graph, with its optional `[...]` metadata."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = "normal"
    color: str | None = None
    max_drones: int = 1


@dataclass(frozen=True)
class Connection:
    """A bidirectional edge between two zones."""

    from_zone: str
    to_zone: str
    max_link_capacity: int = 1


@dataclass(frozen=True)
class MapFile:
    """Parsed representation of a .map input file."""

    nb_drones: int
    start: Zone
    end: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
