"""Headless rendering of the curses UI: every frame, several sizes."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph import ZoneGraph
from src.parser import MapParser
from src.pathfinding import FlightPlanner
from src.simulation import SimulationEngine
from src.tui import FREE, TerminalUI

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
    """Quarter-turn steps catch drones mid-glide and mid-transit too."""
    ui = _ui(path)
    screen = FakeScreen(*size)
    for quarter in range(4 * ui._last + 1):
        ui._t = quarter / 4
        ui.draw(screen)  # type: ignore[arg-type]
        assert "FLY-IN" in screen.text() or "too small" in screen.text()


def test_last_frame_shows_every_drone_delivered() -> None:
    ui = _ui(Path("data/maps/easy/02_simple_fork.txt"))
    screen = FakeScreen(140, 30)
    ui._t = float(ui._last)
    ui.draw(screen)  # type: ignore[arg-type]
    assert "4/4 delivered" in screen.text()


def test_panel_spells_out_moves_with_full_names() -> None:
    ui = _ui(Path("data/maps/medium/02_circular_loop.txt"))
    screen = FakeScreen(140, 30)
    ui._t = 3.0  # D1 departs toward the restricted exit_point
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


def _paths(ui: TerminalUI) -> dict[tuple[str, str], list[tuple[int, int]]]:
    return ui.geometry(2, 1, 26, 136)[3]


def test_a_moving_drone_glides_between_the_two_zones() -> None:
    ui = _ui(Path("data/maps/easy/01_linear_path.txt"))
    line = _paths(ui)[("start", "waypoint1")]
    ui._t = 0.1  # early in turn 1: D1 just left the start
    early = ui.drone_cells(_paths(ui))[1]
    ui._t = 0.9
    late = ui.drone_cells(_paths(ui))[1]
    assert line.index(early) < line.index(late)
    ui._t = 1.0  # landed: back in a zone, off the link
    assert 1 not in ui.drone_cells(_paths(ui))


def test_a_transit_stops_halfway_and_lands_next_turn() -> None:
    ui = _ui(Path("data/maps/medium/02_circular_loop.txt"))
    line = _paths(ui)[("loop_b", "exit_point")]
    ui._t = 3.0  # D1 took off toward the restricted exit_point
    assert ui.drone_cells(_paths(ui))[1] == line[len(line) // 2]
    ui._t = 3.9  # landing: past the midpoint
    assert line.index(ui.drone_cells(_paths(ui))[1]) > len(line) // 2


def test_zones_list_their_drones_by_number() -> None:
    ui = _ui(Path("data/maps/easy/03_basic_capacity.txt"))
    screen = FakeScreen(140, 30)
    ui._t = 2.0
    ui.draw(screen)  # type: ignore[arg-type]
    # D3 D4 fill the capacity-2 bottleneck; D1 D2 sit in the 3-slot
    # wide_area with one slot free.
    assert "3 4 " in screen.text() and f"1 2 {FREE}" in screen.text()


def test_right_arrow_plays_exactly_one_turn() -> None:
    ui = _ui(Path("data/maps/easy/01_linear_path.txt"))
    ui.handle(ord(" "))  # pause at 0
    ui.handle(261)  # KEY_RIGHT
    ui.advance(0.5)
    assert 0 < ui._t < 1
    ui.advance(60)
    assert ui._t == 1.0 and not ui._playing
