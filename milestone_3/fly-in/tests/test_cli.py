"""Tests for src.__main__: the exit-code contract of the fly-in CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from src.__main__ import main


class TestExitCodes:
    def test_success_exits_zero(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        assert main([str(path)]) == 0

    def test_missing_file_exits_one(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "missing.map")]) == 1

    def test_parse_error_exits_two(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map("start_hub: a 0 0\nend_hub: b 1 1\n")
        assert main([str(path)]) == 2

    def test_no_path_exits_three(self, write_map: Callable[..., Path]) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 9 9\n"
            "hub: island 5 5\n"
            "connection: a-island\n"
        )
        assert main([str(path)]) == 3

    def test_visual_flag_still_exits_zero(
        self, write_map: Callable[..., Path]
    ) -> None:
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )
        assert main([str(path), "--visual"]) == 0


class TestReport:
    def test_path_cost_charges_each_zone_entered(
        self,
        write_map: Callable[..., Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # a -> c (1) -> d, restricted (2, transit not charged) -> b (1).
        path = write_map(
            "nb_drones: 1\n"
            "start_hub: a 0 0\n"
            "end_hub: b 3 0\n"
            "hub: c 1 0\n"
            "hub: d 2 0 [zone=restricted]\n"
            "connection: a-c\n"
            "connection: c-d\n"
            "connection: d-b\n"
        )
        assert main([str(path)]) == 0
        assert "Path cost:     4.0" in capsys.readouterr().out
