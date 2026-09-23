"""Parser del formato .map usato da Fly-in."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast, get_args

from .schemas import Connection, MapFile, Zone, ZoneType


class ParserError(RuntimeError):
    """Sollevata quando un file .map ha sintassi o contenuto non validi."""

    def __init__(self, line_no: int, message: str) -> None:
        """Aggiunge al messaggio il numero della riga sbagliata."""
        super().__init__(f"Line {line_no}: {message}")


class MapParser:
    """Trasforma un file `.map` in un modello :class:`MapFile` valido.

    Contiene la grammatica delle righe, la lettura dei metadati e i
    controlli finali di coerenza (nomi unici, riferimenti esistenti)
    descritti nel subject di Fly-in. Una nuova istanza non conserva
    stato tra una chiamata a :meth:`parse` e l'altra.
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
        """Crea un parser vuoto, pronto a leggere un file mappa."""
        self._reset()

    def parse(self, path: Path) -> MapFile:
        """Legge `path` e restituisce una :class:`MapFile` valida.

        Args:
            path: Percorso del file `.map`.

        Returns:
            La mappa completa e verificata.

        Raises:
            ParserError: Se il file manca o ha sintassi o contenuto non
                validi.
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
        """Cancella lo stato rimasto da un parsing precedente."""
        self._nb_drones: int | None = None
        self._start: Zone | None = None
        self._end: Zone | None = None
        self._zones: dict[str, Zone] = {}
        self._connections: list[Connection] = []
        self._conn_pairs: set[tuple[str, str]] = set()

    def _parse_line(self, line_no: int, raw_line: str) -> None:
        """Passa una riga del file alla regola di grammatica giusta."""
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
        """Legge una riga `nb_drones: <n>`; False se `line` non lo è.

        Raises:
            ParserError: Se è dichiarata due volte o il numero non è
                positivo.
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
        """Legge una riga start_hub/end_hub/hub; hanno la stessa grammatica."""
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
        """Legge una riga `connection: a-b [...]`; False se non lo è.

        Raises:
            ParserError: Se una zona non esiste, la zona è collegata a sé
                stessa, il collegamento è doppio (in qualsiasi verso) o i
                metadati non sono validi.
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
        """Crea una `Zone` da un match della regex start_hub/end_hub/hub."""
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
        """Estrae le coppie chiave=valore dal testo dentro `[...]`.

        Esempio: 'zone=restricted color=red max_drones=2' ->
                 {'zone': 'restricted', 'color': 'red', 'max_drones': '2'}

        Raises:
            ParserError: Se un pezzo non è `chiave=valore`, se una chiave
                non è in `allowed` o se una chiave compare due volte.
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
        """Converte `raw_value` in un intero maggiore o uguale a 1.

        Raises:
            ParserError: Con il nome di `field` e la riga, se non lo è.
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
        """Fa i controlli finali di coerenza e costruisce la `MapFile`."""
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
