"""Headless rendering of the curses UI: every frame, several sizes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph import ZoneGraph
from src.parser import MapParser
from src.pathfinding import FlightPlanner
from src.simulation import SimulationEngine
from src.tui import TerminalUI

MAPS = sorted(Path("data/maps").glob("*/*.txt"))


class FakeScreen:
    """Just enough of a curses window to capture what gets drawn."""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self.grid = [[" "] * cols for _ in range(rows)]

    def erase(self) -> None:
        self.grid = [[" "] * self.cols for _ in range(self.rows)]

    def getmaxyx(self) -> tuple[int, int]:
        return self.rows, self.cols

    def refresh(self) -> None:
        pass

    def addnstr(self, row: int, col: int, text: str, n: int, _: int) -> None:
        for i, char in enumerate(text[:n]):
            self.grid[row][col + i] = char

    def text(self) -> str:
        return "\n".join("".join(row) for row in self.grid)


def _ui(path: Path) -> TerminalUI:
    map_file = MapParser().parse(path)
    timelines = FlightPlanner(map_file, ZoneGraph(map_file)).plan()
    log = SimulationEngine(map_file, timelines).run()
    return TerminalUI(map_file, log, title=path.name)


@pytest.mark.parametrize("path", MAPS, ids=lambda p: p.stem)
@pytest.mark.parametrize("size", [(60, 16), (100, 30), (220, 60)])
def test_every_frame_draws_without_error(
    path: Path, size: tuple[int, int]
) -> None:
    ui = _ui(path)
    screen = FakeScreen(*size)
    for _ in range(len(ui._frames)):
        ui.draw(screen)  # type: ignore[arg-type]
        ui.handle(261)  # KEY_RIGHT
    assert "FLY-IN" in screen.text() or "too small" in screen.text()


def test_last_frame_shows_every_drone_delivered() -> None:
    ui = _ui(Path("data/maps/easy/02_simple_fork.txt"))
    screen = FakeScreen(140, 30)
    ui._index = len(ui._frames) - 1
    ui.draw(screen)  # type: ignore[arg-type]
    assert "4/4 delivered" in screen.text()


def test_panel_spells_out_moves_with_full_names() -> None:
    ui = _ui(Path("data/maps/medium/02_circular_loop.txt"))
    screen = FakeScreen(140, 30)
    ui._index = 3  # D1 departs toward the restricted exit_point
    ui.draw(screen)  # type: ignore[arg-type]
    assert "loop_b → exit_point (2 turns)" in screen.text()


def test_quit_key_stops_the_loop() -> None:
    ui = _ui(Path("data/maps/easy/01_linear_path.txt"))
    assert ui.handle(ord("q")) is False
    assert ui.handle(ord(" ")) is True


def test_panel_toggle_overrides_the_automatic_choice() -> None:
    ui = _ui(Path("data/maps/challenger/01_the_impossible_dream.txt"))
    screen = FakeScreen(140, 40)
    ui.draw(screen)  # type: ignore[arg-type]
    assert "FLEET" not in screen.text()  # 21 zone columns: map needs room
    ui.handle(ord("p"))
    ui.draw(screen)  # type: ignore[arg-type]
    assert "FLEET" in screen.text()
