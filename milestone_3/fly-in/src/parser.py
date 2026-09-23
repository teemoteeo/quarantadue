"""Parser for the custom .map file format used by Fly-in."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast, get_args

from .schemas import Connection, MapFile, Zone, ZoneType


class ParserError(RuntimeError):
    """Raised when a .map file contains invalid syntax or semantics."""

    def __init__(self, line_no: int, message: str) -> None:
        """Prefix the message with the offending line number."""
        super().__init__(f"Line {line_no}: {message}")


class MapParser:
    """Parses a `.map` file into a validated :class:`MapFile` model.

    Encapsulates the line grammar, metadata parsing, and the post-parse
    semantic validation (uniqueness, referential integrity) described in
    the Fly-in subject. A fresh instance is stateless between calls to
    :meth:`parse`.
    """

    # Derived from the Literal so the two can never drift apart.
    _VALID_ZONE_TYPES: frozenset[str] = frozenset(get_args(ZoneType))

    _RE_NB_DRONES: re.Pattern[str] = re.compile(r"^nb_drones:\s*(\d+)$")
    _RE_ZONE: re.Pattern[str] = re.compile(
        r"^(start_hub|end_hub|hub):"
        r"\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
    )
    _RE_CONN: re.Pattern[str] = re.compile(
        r"^connection:\s+([^\s-]+)-([^\s-]+)(?:\s+\[(.+)\])?$"
    )
    _ZONE_KEYS: frozenset[str] = frozenset({"zone", "color", "max_drones"})
    _CONN_KEYS: frozenset[str] = frozenset({"max_link_capacity"})

    def __init__(self) -> None:
        """Initialise an empty parser ready to parse a map file."""
        self._reset()

    def parse(self, path: Path) -> MapFile:
        """Parse `path` and return a validated :class:`MapFile`.

        Args:
            path: Filesystem path to the `.map` file.

        Returns:
            The fully validated map representation.

        Raises:
            ParserError: If the file is missing or contains invalid
                syntax or semantics.
        """
        self._reset()
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line_no, raw_line in enumerate(handle, start=1):
                    self._parse_line(line_no, raw_line)
        except FileNotFoundError:
            raise ParserError(0, f"File not found: {path}") from None
        except OSError as exc:
            raise ParserError(0, f"Cannot read {path}: {exc}") from None
        except UnicodeDecodeError:
            raise ParserError(0, f"Not valid UTF-8 text: {path}") from None

        return self._finalize()

    def _reset(self) -> None:
        """Clear any state left over from a previous parse."""
        self._nb_drones: int | None = None
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._conn_pairs: set[tuple[str, str]] = set()

    def _parse_line(self, line_no: int, raw_line: str) -> None:
        """Dispatch a single source line to the matching grammar rule."""
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            return

        if self._try_nb_drones(line_no, line):
            return
        if self._nb_drones is None:
            raise ParserError(
                line_no, "The first line must be 'nb_drones: <number>'"
            )
        if self._try_zone(line_no, line):
            return
        if self._try_connection(line_no, line):
            return
        raise ParserError(line_no, f"Unrecognised line: {raw_line.rstrip()!r}")

    def _try_nb_drones(self, line_no: int, line: str) -> bool:
        """Parse an `nb_drones: <n>` line; False if `line` is not one.

        Raises:
            ParserError: On a second declaration or a non-positive count.
        """
        match = self._RE_NB_DRONES.match(line)
        if not match:
            return False
        if self._nb_drones is not None:
            raise ParserError(line_no, "Duplicate nb_drones declaration")
        self._nb_drones = self._positive_int(
            line_no, "nb_drones", match.group(1)
        )
        return True

    def _try_zone(self, line_no: int, line: str) -> bool:
        """Parse a start_hub/end_hub/hub line; they share one grammar."""
        match = self._RE_ZONE.match(line)
        if not match:
            return False
        kind = match.group(1)
        zone = self._build_zone(line_no, match)
        if zone.name in self._zones:
            raise ParserError(line_no, f"Duplicate zone name: {zone.name!r}")
        if kind == "start_hub":
            if self._start is not None:
                raise ParserError(line_no, "Duplicate start_hub declaration")
            self._start = zone
        elif kind == "end_hub":
            if self._end is not None:
                raise ParserError(line_no, "Duplicate end_hub declaration")
            self._end = zone
        self._zones[zone.name] = zone
        return True

    def _try_connection(self, line_no: int, line: str) -> bool:
        """Parse a `connection: a-b [...]` line; False if it is not one.

        Raises:
            ParserError: On an undefined zone, a self-connection, a
                duplicate (in either direction) or invalid metadata.
        """
        match = self._RE_CONN.match(line)
        if not match:
            return False
        a, b = match.group(1), match.group(2)
        for name in (a, b):
            if name not in self._zones:
                raise ParserError(
                    line_no, f"Connection references unknown zone: {name!r}"
                )
        if a == b:
            raise ParserError(line_no, f"Zone {a!r} connected to itself")
        pair = (min(a, b), max(a, b))
        if pair in self._conn_pairs:
            raise ParserError(line_no, f"Duplicate connection: {a}-{b}")
        self._conn_pairs.add(pair)
        raw = self._parse_metadata(
            line_no, match.group(3) or "", self._CONN_KEYS
        )
        self._connections.append(Connection(
            from_zone=a,
            to_zone=b,
            max_link_capacity=self._positive_int(
                line_no, "max_link_capacity",
                raw.get("max_link_capacity", "1"),
            ),
        ))
        return True

    def _build_zone(self, line_no: int, match: re.Match[str]) -> Zone:
        """Build a `Zone` from a start_hub/end_hub/hub regex match."""
        if "-" in match.group(2):
            raise ParserError(
                line_no, f"Zone name must not contain '-': {match.group(2)!r}"
            )
        raw = self._parse_metadata(
            line_no, match.group(5) or "", self._ZONE_KEYS
        )
        zone_type = raw.get("zone", "normal")
        if zone_type not in self._VALID_ZONE_TYPES:
            raise ParserError(line_no, f"Invalid zone type: {zone_type!r}")
        return Zone(
            name=match.group(2),
            x=int(match.group(3)),
            y=int(match.group(4)),
            zone_type=cast(ZoneType, zone_type),
            color=raw.get("color"),
            max_drones=self._positive_int(
                line_no, "max_drones", raw.get("max_drones", "1")
            ),
        )

    @staticmethod
    def _parse_metadata(
        line_no: int, raw: str, allowed: frozenset[str]
    ) -> dict[str, str]:
        """Extract key=value pairs from the text inside `[...]`.

        Example: 'zone=restricted color=red max_drones=2' ->
                 {'zone': 'restricted', 'color': 'red', 'max_drones': '2'}

        Raises:
            ParserError: On a token that is not `key=value`, a key not in
                `allowed`, or a key given twice.
        """
        result: dict[str, str] = {}
        for part in raw.split():
            key, sep, value = part.partition("=")
            if not sep or not value:
                raise ParserError(line_no, f"Invalid metadata: {part!r}")
            if key not in allowed:
                raise ParserError(line_no, f"Unknown metadata key: {key!r}")
            if key in result:
                raise ParserError(line_no, f"Duplicate metadata key: {key!r}")
            result[key] = value
        return result

    @staticmethod
    def _positive_int(line_no: int, field: str, raw_value: str) -> int:
        """Convert `raw_value` to an int of at least 1.

        Raises:
            ParserError: Naming `field` and the line, if it is not one.
        """
        try:
            value = int(raw_value)
        except ValueError:
            raise ParserError(
                line_no,
                f"{field} must be a positive integer, got {raw_value!r}",
            ) from None
        if value < 1:
            raise ParserError(
                line_no, f"{field} must be a positive integer, got {value}"
            )
        return value

    def _finalize(self) -> MapFile:
        """Run post-parse semantic checks and assemble the `MapFile`."""
        if self._nb_drones is None:
            raise ParserError(0, "Missing nb_drones declaration")
        if self._start is None:
            raise ParserError(0, "Missing start_hub declaration")
        if self._end is None:
            raise ParserError(0, "Missing end_hub declaration")
        return MapFile(
            nb_drones=self._nb_drones,
            start=self._start,
            end=self._end,
            zones=self._zones,
            connections=self._connections,
        )
