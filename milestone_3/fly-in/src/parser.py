"""Parser for the custom .map file format used by Fly-in."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .schemas import (
    Connection,
    ConnectionMetadata,
    MapFile,
    Zone,
    ZoneMetadata,
)


class ParserError(RuntimeError):
    """Raised when a .map file contains invalid syntax or semantics."""

    def __init__(self, line_no: int, message: str) -> None:
        super().__init__(f"Line {line_no}: {message}")
        self.line_no = line_no


_VALID_ZONE_TYPES: set[str] = {"normal", "blocked", "restricted", "priority"}


def _parse_metadata(raw: str) -> dict[str, str]:
    """Extract key=value pairs from a bracket-enclosed metadata string.

    Example: '[zone=restricted color=red max_drones=2]' ->
             {'zone': 'restricted', 'color': 'red', 'max_drones': '2'}
    """
    inner = raw.strip("[]")
    result: dict[str, str] = {}
    for part in inner.split():
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        result[key] = value
    return result


def _build_zone_metadata(raw: dict[str, str], line_no: int) -> ZoneMetadata:
    kwargs: dict[str, Any] = {}
    if "zone" in raw:
        zone_type = raw["zone"]
        if zone_type not in _VALID_ZONE_TYPES:
            raise ParserError(line_no, f"Invalid zone type: {zone_type!r}")
        kwargs["zone"] = zone_type
    if "color" in raw:
        kwargs["color"] = raw["color"]
    if "max_drones" in raw:
        try:
            val = int(raw["max_drones"])
            if val < 1:
                raise ParserError(
                    line_no,
                    f"max_drones must be a positive integer, got {val}",
                )
            kwargs["max_drones"] = val
        except ValueError:
            raise ParserError(
                line_no,
                f"max_drones must be a positive integer, "
                f"got {raw['max_drones']!r}",
            ) from None
    return ZoneMetadata(**kwargs)


def _build_conn_metadata(
    raw: dict[str, str],
    line_no: int,
) -> ConnectionMetadata:
    kwargs: dict[str, Any] = {}
    if "max_link_capacity" in raw:
        try:
            val = int(raw["max_link_capacity"])
            if val < 1:
                raise ParserError(
                    line_no,
                    "max_link_capacity must be a positive integer, "
                    f"got {val}",
                )
            kwargs["max_link_capacity"] = val
        except ValueError:
            raise ParserError(
                line_no,
                "max_link_capacity must be a positive integer, "
                f"got {raw['max_link_capacity']!r}",
            ) from None
    return ConnectionMetadata(**kwargs)


_RE_NB_DRONES = re.compile(r"^nb_drones:\s*(\d+)$")
_RE_START = re.compile(
    r"^start_hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
)
_RE_END = re.compile(
    r"^end_hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
)
_RE_HUB = re.compile(
    r"^hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
)
_RE_CONN = re.compile(
    r"^connection:\s+(\S+)-(\S+)(?:\s+\[(.+)\])?$"
)


def parse_map_file(path: Path) -> MapFile:
    """Parse a .map file and return a validated MapFile model.

    Raises ParserError on any syntax or semantic issue.
    """
    if not path.exists():
        raise ParserError(0, f"File not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()

    nb_drones: int | None = None
    start: Zone | None = None
    end: Zone | None = None
    zones: dict[str, Zone] = {}
    connections: list[Connection] = []
    conn_pairs: set[tuple[str, str]] = set()

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.split("#")[0].strip()
        if not line:
            continue

        m = _RE_NB_DRONES.match(line)
        if m:
            if nb_drones is not None:
                raise ParserError(line_no, "Duplicate nb_drones declaration")
            nb_drones = int(m.group(1))
            continue

        m = _RE_START.match(line)
        if m:
            if start is not None:
                raise ParserError(line_no, "Duplicate start_hub declaration")
            name = m.group(1)
            x, y = int(m.group(2)), int(m.group(3))
            meta_raw = _parse_metadata(m.group(4) or "")
            start = Zone(
                name=name, x=x, y=y,
                metadata=_build_zone_metadata(meta_raw, line_no)
            )
            zones[name] = start
            continue

        m = _RE_END.match(line)
        if m:
            if end is not None:
                raise ParserError(line_no, "Duplicate end_hub declaration")
            name = m.group(1)
            x, y = int(m.group(2)), int(m.group(3))
            meta_raw = _parse_metadata(m.group(4) or "")
            end = Zone(
                name=name, x=x, y=y,
                metadata=_build_zone_metadata(meta_raw, line_no)
            )
            zones[name] = end
            continue

        m = _RE_HUB.match(line)
        if m:
            name = m.group(1)
            if name in zones:
                raise ParserError(line_no, f"Duplicate zone name: {name!r}")
            x, y = int(m.group(2)), int(m.group(3))
            meta_raw = _parse_metadata(m.group(4) or "")
            zone = Zone(
                name=name, x=x, y=y,
                metadata=_build_zone_metadata(meta_raw, line_no)
            )
            zones[name] = zone
            continue

        m = _RE_CONN.match(line)
        if m:
            a, b = m.group(1), m.group(2)
            pair = (min(a, b), max(a, b))
            if pair in conn_pairs:
                raise ParserError(
                    line_no, f"Duplicate connection: {a}-{b}"
                )
            conn_pairs.add(pair)
            meta_raw = _parse_metadata(m.group(3) or "")
            conn = Connection(
                from_zone=a, to_zone=b,
                metadata=_build_conn_metadata(meta_raw, line_no)
            )
            connections.append(conn)
            continue

        raise ParserError(line_no, f"Unrecognised line: {raw_line!r}")

    # Post-parse validation
    if nb_drones is None:
        raise ParserError(0, "Missing nb_drones declaration")
    if start is None:
        raise ParserError(0, "Missing start_hub declaration")
    if end is None:
        raise ParserError(0, "Missing end_hub declaration")

    # Validate connections reference existing zones
    for conn in connections:
        if conn.from_zone not in zones:
            raise ParserError(
                0, f"Connection references unknown zone: {conn.from_zone!r}"
            )
        if conn.to_zone not in zones:
            raise ParserError(
                0, f"Connection references unknown zone: {conn.to_zone!r}"
            )

    return MapFile(
        nb_drones=nb_drones,
        start=start,
        end=end,
        zones=zones,
        connections=connections,
    )
