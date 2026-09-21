"""Parser for the custom .map file format used by Fly-in."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Pattern

from pydantic import ValidationError

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
        """Store the offending line number alongside the error message."""
        super().__init__(f"Line {line_no}: {message}")
        self.line_no = line_no


class MapParser:
    """Parses a `.map` file into a validated :class:`MapFile` model.

    Encapsulates the line grammar, metadata parsing, and the post-parse
    semantic validation (uniqueness, referential integrity) described in
    the Fly-in subject. A fresh instance is stateless between calls to
    :meth:`parse`.
    """

    _VALID_ZONE_TYPES: set[str] = {
        "normal", "blocked", "restricted", "priority"
    }

    _ZONE_META_KEYS: set[str] = {"zone", "color", "max_drones"}
    _CONN_META_KEYS: set[str] = {"max_link_capacity"}

    _RE_NB_DRONES: Pattern[str] = re.compile(r"^nb_drones:\s*(\d+)$")
    _RE_START: Pattern[str] = re.compile(
        r"^start_hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
    )
    _RE_END: Pattern[str] = re.compile(
        r"^end_hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
    )
    _RE_HUB: Pattern[str] = re.compile(
        r"^hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.+)\])?$"
    )
    _RE_CONN: Pattern[str] = re.compile(
        r"^connection:\s+(\S+)-(\S+)(?:\s+\[(.+)\])?$"
    )

    def __init__(self) -> None:
        """Initialise an empty parser ready to parse a map file."""
        self._nb_drones: int | None = None
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._conn_pairs: set[tuple[str, str]] = set()

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
        if not path.is_file():
            raise ParserError(0, f"File not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as handle:
                for line_no, raw_line in enumerate(handle, start=1):
                    self._parse_line(line_no, raw_line)
        except OSError as exc:
            raise ParserError(0, f"Cannot read {path}: {exc.strerror}")
        except UnicodeDecodeError:
            raise ParserError(0, f"{path} is not valid UTF-8 text")

        return self._finalize()

    def _reset(self) -> None:
        """Clear any state left over from a previous parse."""
        self._nb_drones = None
        self._start = None
        self._end = None
        self._zones = {}
        self._connections = []
        self._conn_pairs = set()

    def _parse_line(self, line_no: int, raw_line: str) -> None:
        """Dispatch a single source line to the matching grammar rule."""
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            return

        if self._try_nb_drones(line_no, line):
            return
        if self._try_start(line_no, line):
            return
        if self._try_end(line_no, line):
            return
        if self._try_hub(line_no, line):
            return
        if self._try_connection(line_no, line):
            return
        raise ParserError(line_no, f"Unrecognised line: {raw_line.rstrip()!r}")

    def _try_nb_drones(self, line_no: int, line: str) -> bool:
        match = self._RE_NB_DRONES.match(line)
        if not match:
            return False
        if self._nb_drones is not None:
            raise ParserError(line_no, "Duplicate nb_drones declaration")
        count = int(match.group(1))
        if count < 1:
            raise ParserError(
                line_no,
                f"nb_drones must be a positive integer, got {count}",
            )
        self._nb_drones = count
        return True

    def _try_start(self, line_no: int, line: str) -> bool:
        match = self._RE_START.match(line)
        if not match:
            return False
        if self._start is not None:
            raise ParserError(line_no, "Duplicate start_hub declaration")
        zone = self._build_zone(line_no, match)
        self._start = zone
        self._zones[zone.name] = zone
        return True

    def _try_end(self, line_no: int, line: str) -> bool:
        match = self._RE_END.match(line)
        if not match:
            return False
        if self._end is not None:
            raise ParserError(line_no, "Duplicate end_hub declaration")
        zone = self._build_zone(line_no, match)
        self._end = zone
        self._zones[zone.name] = zone
        return True

    def _try_hub(self, line_no: int, line: str) -> bool:
        match = self._RE_HUB.match(line)
        if not match:
            return False
        name = match.group(1)
        if name in self._zones:
            raise ParserError(line_no, f"Duplicate zone name: {name!r}")
        zone = self._build_zone(line_no, match)
        self._zones[zone.name] = zone
        return True

    def _try_connection(self, line_no: int, line: str) -> bool:
        match = self._RE_CONN.match(line)
        if not match:
            return False
        a, b = match.group(1), match.group(2)
        pair = (min(a, b), max(a, b))
        if pair in self._conn_pairs:
            raise ParserError(line_no, f"Duplicate connection: {a}-{b}")
        self._conn_pairs.add(pair)
        meta_raw = self._parse_metadata(
            line_no, match.group(3) or "", self._CONN_META_KEYS
        )
        conn = Connection(
            from_zone=a,
            to_zone=b,
            metadata=self._build_conn_metadata(meta_raw, line_no),
        )
        self._connections.append(conn)
        return True

    def _build_zone(self, line_no: int, match: "re.Match[str]") -> Zone:
        """Build a `Zone` from a start_hub/end_hub/hub regex match."""
        name = match.group(1)
        if "-" in name:
            # The connection syntax is `<zone1>-<zone2>`, so a dash in a
            # zone name would make connection lines ambiguous.
            raise ParserError(
                line_no, f"Zone name may not contain a dash: {name!r}"
            )
        x, y = int(match.group(2)), int(match.group(3))
        meta_raw = self._parse_metadata(
            line_no, match.group(4) or "", self._ZONE_META_KEYS
        )
        return Zone(
            name=name,
            x=x,
            y=y,
            metadata=self._build_zone_metadata(meta_raw, line_no),
        )

    @staticmethod
    def _parse_metadata(
        line_no: int, raw: str, allowed: set[str]
    ) -> dict[str, str]:
        """Extract key=value pairs from a bracket-enclosed metadata string.

        Example: '[zone=restricted color=red max_drones=2]' ->
                 {'zone': 'restricted', 'color': 'red', 'max_drones': '2'}

        Raises:
            ParserError: On a token that is not `key=value`, an unknown
                key, or a repeated key. The subject requires metadata
                blocks to be syntactically valid, so an unrecognised tag
                is an error rather than something to ignore.
        """
        inner = raw.strip("[]")
        result: dict[str, str] = {}
        for part in inner.split():
            key, sep, value = part.partition("=")
            if not sep or not key or not value:
                raise ParserError(
                    line_no, f"Malformed metadata tag: {part!r}"
                )
            if key not in allowed:
                raise ParserError(
                    line_no,
                    f"Unknown metadata key: {key!r} "
                    f"(expected one of {', '.join(sorted(allowed))})",
                )
            if key in result:
                raise ParserError(
                    line_no, f"Duplicate metadata key: {key!r}"
                )
            result[key] = value
        return result

    def _build_zone_metadata(
        self, raw: dict[str, str], line_no: int
    ) -> ZoneMetadata:
        kwargs: dict[str, Any] = {}
        if "zone" in raw:
            zone_type = raw["zone"]
            if zone_type not in self._VALID_ZONE_TYPES:
                raise ParserError(line_no, f"Invalid zone type: {zone_type!r}")
            kwargs["zone"] = zone_type
        if "color" in raw:
            kwargs["color"] = raw["color"]
        if "max_drones" in raw:
            kwargs["max_drones"] = self._positive_int(
                line_no, "max_drones", raw["max_drones"]
            )
        return ZoneMetadata(**kwargs)

    def _build_conn_metadata(
        self, raw: dict[str, str], line_no: int
    ) -> ConnectionMetadata:
        kwargs: dict[str, Any] = {}
        if "max_link_capacity" in raw:
            kwargs["max_link_capacity"] = self._positive_int(
                line_no, "max_link_capacity", raw["max_link_capacity"]
            )
        return ConnectionMetadata(**kwargs)

    @staticmethod
    def _positive_int(line_no: int, field: str, raw_value: str) -> int:
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

        for conn in self._connections:
            if conn.from_zone not in self._zones:
                raise ParserError(
                    0,
                    f"Connection references unknown zone: {conn.from_zone!r}",
                )
            if conn.to_zone not in self._zones:
                raise ParserError(
                    0,
                    f"Connection references unknown zone: {conn.to_zone!r}",
                )

        try:
            return MapFile(
                nb_drones=self._nb_drones,
                start=self._start,
                end=self._end,
                zones=self._zones,
                connections=self._connections,
            )
        except ValidationError as exc:
            # Every field is checked above with a line number attached, so
            # reaching here means a schema rule the line grammar doesn't
            # cover. Report it as a parse error rather than a traceback.
            raise ParserError(0, f"Invalid map: {exc.errors()[0]['msg']}")
