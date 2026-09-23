"""Tests for the display-free replay shared by both renderers."""

from __future__ import annotations

from src.schemas import Zone
from src.simulation import Movement, SimulationFilm, TurnLog
from src.tui import ZoneLayout


LOG = [
    TurnLog(1, [Movement(1, "mid")]),
    TurnLog(2, [Movement(1, "mid-sensor"), Movement(2, "mid")]),
    TurnLog(3, [Movement(1, "sensor")]),
]


class TestSimulationFilm:
    def test_frame_zero_puts_every_drone_at_start(self) -> None:
        frames = SimulationFilm(LOG, "hub", 2).frames()
        assert frames[0] == {1: "hub", 2: "hub"}

    def test_one_frame_per_turn_plus_the_start(self) -> None:
        assert len(SimulationFilm(LOG, "hub", 2).frames()) == len(LOG) + 1

    def test_still_drones_keep_their_position(self) -> None:
        # D2 does not move on turn 1, so it is still at the start hub.
        assert SimulationFilm(LOG, "hub", 2).frames()[1] == {
            1: "mid", 2: "hub"
        }

    def test_in_flight_position_is_the_connection(self) -> None:
        assert SimulationFilm(LOG, "hub", 2).frames()[2][1] == "mid-sensor"

    def test_frames_are_independent_snapshots(self) -> None:
        frames = SimulationFilm(LOG, "hub", 2).frames()
        assert frames[3][1] == "sensor" and frames[1][1] == "mid"


class TestZoneLayout:
    ZONES = {
        "hub": Zone("hub", 0, 0),
        "mid": Zone("mid", 5, 2),
        "goal": Zone("goal", 10, 4),
    }

    def test_cells_stay_inside_the_screen(self) -> None:
        cells = ZoneLayout(self.ZONES).cells(24, 80)
        assert all(0 <= r < 24 and 0 <= c < 80 for r, c in cells.values())

    def test_single_row_map_does_not_divide_by_zero(self) -> None:
        flat = {"a": Zone("a", 0, 0), "b": Zone("b", 3, 0)}
        rows = {r for r, _ in ZoneLayout(flat).cells(24, 80).values()}
        assert len(rows) == 1

    def test_zone_and_drone_rows_clear_the_status_bar(self) -> None:
        # Smallest terminal the UI accepts; the drone row sits one
        # below its zone and must not land on the legend.
        cells = ZoneLayout(self.ZONES).cells(14, 60)
        assert max(r for r, _ in cells.values()) + 1 < 14 - 2

    def test_label_carries_marker_and_capacity(self) -> None:
        assert ZoneLayout.label("m8", Zone("m8", 0, 0, "restricted")) == "m8!"
        assert ZoneLayout.label(
            "m9", Zone("m9", 0, 0, "priority", max_drones=2)
        ) == "m9*[2]"

    def test_right_margin_reserves_the_drawn_label_not_the_name(self) -> None:
        # "goal" is 4 characters but draws as "goal*[3]".
        wide = {"a": Zone("a", 0, 0), "goal": Zone("goal", 9, 0, "priority",
                                                   max_drones=3)}
        col = ZoneLayout(wide).cells(24, 80)["goal"][1]
        assert col + len("goal*[3]") < 80

    def test_fit_shifts_a_right_edge_queue_back_onto_the_screen(self) -> None:
        # The bug this guards: 6 drones at a goal on the right margin were
        # drawn as "1 2 3 4" because the rest ran off the screen.
        assert ZoneLayout.fit(75, 80, "1 2 3 4 5 6") == 68
        assert ZoneLayout.fit(10, 80, "1 2") == 10
        assert ZoneLayout.fit(75, 20, "x" * 40) == 0

    def test_horizontal_link_is_all_dashes(self) -> None:
        assert ZoneLayout.segments((0, 0), (0, 4)) == [
            (0, 1, "-"), (0, 2, "-"), (0, 3, "-")
        ]

    def test_vertical_link_is_all_pipes(self) -> None:
        assert [g for _, _, g in ZoneLayout.segments((0, 0), (4, 0))] == [
            "|", "|", "|"
        ]

    def test_shallow_diagonal_is_dashes_with_a_step(self) -> None:
        # Two columns per row: a run of dashes that drops once per row,
        # not a row of backslashes.
        glyphs = [g for _, _, g in ZoneLayout.segments((0, 0), (3, 6))]
        assert set(glyphs) == {"-", "\\"}
        assert glyphs.count("\\") == 2

    def test_upward_diagonal_uses_the_other_slash(self) -> None:
        assert [g for _, _, g in ZoneLayout.segments((4, 0), (0, 4))] == [
            "/", "/", "/"
        ]

    def test_adjacent_cells_have_no_interior(self) -> None:
        assert ZoneLayout.segments((2, 2), (2, 3)) == []
