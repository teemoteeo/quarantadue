"""Pydantic schemas for the Fly-in drone simulation domain."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ZoneType = Literal["normal", "blocked", "restricted", "priority"]


class ZoneMetadata(BaseModel):
    """Optional metadata for a zone node."""

    model_config = ConfigDict(extra="forbid")

    zone: ZoneType = Field(default="normal")
    color: str | None = Field(default=None)
    max_drones: int = Field(default=1, ge=1)


class ConnectionMetadata(BaseModel):
    """Optional metadata for a connection edge."""

    model_config = ConfigDict(extra="forbid")

    max_link_capacity: int = Field(default=1, ge=1)


class Zone(BaseModel):
    """A zone (node) in the graph with optional metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    x: int
    y: int
    metadata: ZoneMetadata = Field(default_factory=ZoneMetadata)


class Connection(BaseModel):
    """A bidirectional edge between two zones."""

    model_config = ConfigDict(extra="forbid")

    from_zone: str = Field(..., min_length=1)
    to_zone: str = Field(..., min_length=1)
    metadata: ConnectionMetadata = Field(default_factory=ConnectionMetadata)


class MapFile(BaseModel):
    """Parsed representation of a .map input file."""

    model_config = ConfigDict(extra="forbid")

    nb_drones: int = Field(..., ge=1)
    start: Zone
    end: Zone
    zones: dict[str, Zone]
    connections: list[Connection]
