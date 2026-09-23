"""Modelli di dati per la simulazione di droni Fly-in.

Semplici dataclass immutabili; :class:`~src.parser.MapParser`
controlla ogni campo prima di creare un modello.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ZoneType = Literal["normal", "blocked", "restricted", "priority"]


@dataclass(frozen=True)
class Zone:
    """Una zona (nodo) del grafo, con i suoi metadati `[...]` opzionali."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = "normal"
    color: str | None = None
    max_drones: int = 1


@dataclass(frozen=True)
class Connection:
    """Un collegamento bidirezionale tra due zone."""

    from_zone: str
    to_zone: str
    max_link_capacity: int = 1


@dataclass(frozen=True)
class MapFile:
    """Contenuto letto da un file .map."""

    nb_drones: int
    start: Zone
    end: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
