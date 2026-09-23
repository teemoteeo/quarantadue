"""Tests for src.parser.MapParser: grammar, metadata, and semantic checks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.parser import MapParser, ParserError
from src.schemas import MapFile


def _parse(path: Path) -> MapFile:
    return MapParser().parse(path)


class TestValidMaps:
    def test_minimal_valid_map_parses(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        result = _parse(path)
        assert result.nb_drones == 1
        assert result.start.name == "a"
        assert result.end.name == "b"
        assert len(result.connections) == 1

    def test_comments_and_blank_lines_are_ignored(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "# a full-line comment\n"
            "\n"
            "nb_drones: 2  # inline comment\n"
            "\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        result = _parse(path)
        assert result.nb_drones == 2

    def test_metadata_tags_in_any_order(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "hub: c 2 2 [max_drones=3 zone=priority color=green]\n"
            "connection: a-c\n"
            "connection: c-b\n"
        )
        result = _parse(path)
        zone_c = result.zones["c"]
        assert zone_c.zone_type == "priority"
        assert zone_c.color == "green"
        assert zone_c.max_drones == 3

    def test_negative_coordinates_are_accepted(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a -3 -4\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        result = _parse(path)
        assert result.start.x == -3
        assert result.start.y == -4


class TestParserErrors:
    def test_missing_nb_drones(self, write_map: Callable[..., Path]) -> None:
        path = write_map("start_hub: a 0 0\nend_hub: b 1 1\nconnection: a-b\n")
        with pytest.raises(ParserError, match="nb_drones"):
            _parse(path)

    def test_missing_start_hub(self, write_map: Callable[..., Path]) -> None:
        path = write_map("nb_drones: 2\nend_hub: b 1 1\n")
        with pytest.raises(ParserError, match="start_hub"):
            _parse(path)

    def test_missing_end_hub(self, write_map: Callable[..., Path]) -> None:
        path = write_map("nb_drones: 2\nstart_hub: a 0 0\n")
        with pytest.raises(ParserError, match="end_hub"):
            _parse(path)

    def test_duplicate_zone_name(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "hub: a 2 2\n"
            "connection: a-b\n"
        )
        with pytest.raises(ParserError, match="Duplicate zone name"):
            _parse(path)

    def test_duplicate_connection_reversed(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
            "connection: b-a\n"
        )
        with pytest.raises(ParserError, match="Duplicate connection"):
            _parse(path)

    def test_invalid_zone_type(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "hub: c 2 2 [zone=magical]\n"
            "connection: a-c\n"
            "connection: c-b\n"
        )
        with pytest.raises(ParserError, match="Invalid zone type"):
            _parse(path)

    def test_connection_to_undefined_zone(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 1 1\n"
            "connection: a-ghost\n"
        )
        with pytest.raises(ParserError, match="unknown zone"):
            _parse(path)

    def test_zero_max_drones_rejected(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "hub: c 2 2 [max_drones=0]\n"
            "connection: a-c\n"
            "connection: c-b\n"
        )
        with pytest.raises(ParserError, match="positive integer"):
            _parse(path)

    def test_unrecognised_line(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "this is not valid syntax\n"
        )
        with pytest.raises(ParserError, match="Unrecognised line"):
            _parse(path)

    @pytest.mark.parametrize(
        ("body", "error"),
        [
            ("hub: c-d 1 1\n", "must not contain '-'"),
            ("hub: a 2 2\n", "Duplicate zone name"),
            ("end_hub: a 2 2\n", "Duplicate zone name"),
            ("connection: a-a\n", "connected to itself"),
            ("hub: c 1 1 [zone=normal bogus]\n", "Invalid metadata"),
            ("hub: c 1 1 [capacity=2]\n", "Unknown metadata key"),
            ("hub: c 1 1 [zone=normal zone=blocked]\n", "Duplicate metadata"),
            ("connection: a-b [max_drones=2]\n", "Unknown metadata key"),
            ("connection: a-ghost\n", "Line 4: .*unknown zone"),
        ],
    )
    def test_strict_grammar(
        self, write_map: Callable[..., Path], body: str, error: str
    ) -> None:
        path = write_map(
            "nb_drones: 1\nstart_hub: a 0 0\nend_hub: b 1 1\n" + body
        )
        with pytest.raises(ParserError, match=error):
            _parse(path)

    def test_start_hub_cannot_reuse_a_hub_name(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\nhub: a 1 1\nstart_hub: a 0 0\nend_hub: b 2 2\n"
        )
        with pytest.raises(ParserError, match="Duplicate zone name"):
            _parse(path)

    def test_nb_drones_must_come_first(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "# comments are fine\nstart_hub: a 0 0\nnb_drones: 1\n"
        )
        with pytest.raises(ParserError, match="Line 2: The first line"):
            _parse(path)

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ParserError, match="File not found"):
            _parse(tmp_path / "does_not_exist.map")


class TestNeverRaisesRawExceptions:
    """Every bad input must surface as ParserError, never a traceback.

    The subject treats an unhandled exception during review as a
    non-functional project, so these guard the paths where a non-
    ParserError used to escape: pydantic validation, a directory passed
    as a map, and a non-text file.
    """

    def test_zero_drones(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 0\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        with pytest.raises(ParserError, match="nb_drones must be a positive"):
            _parse(path)

    def test_directory_instead_of_file(self, tmp_path: Path) -> None:
        with pytest.raises(ParserError, match="Cannot read"):
            _parse(tmp_path)

    def test_non_utf8_file(self, tmp_path: Path) -> None:
        path = tmp_path / "binary.map"
        path.write_bytes(b"\xff\xfe\x00binary")
        with pytest.raises(ParserError, match="Not valid UTF-8"):
            _parse(path)
