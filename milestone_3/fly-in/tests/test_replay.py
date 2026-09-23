"""Tests for the display-free replay and layout behind the TUI."""

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

    def test_boxes_stay_inside_the_area(self) -> None:
        layout = ZoneLayout(self.ZONES)
        cells = layout.cells(2, 1, 20, 78)
        box = layout.box_width(78)
        assert all(
            r >= 2 and r + 3 <= 22 and c >= 1 and c + box <= 79
            for r, c in cells.values()
        )

    def test_distinct_coordinates_get_evenly_spaced_columns(self) -> None:
        # x = 0, 5, 10 and x = 0, 1, 100 lay out the same: rank, not value.
        skewed = {
            "hub": Zone("hub", 0, 0),
            "mid": Zone("mid", 1, 2),
            "goal": Zone("goal", 100, 4),
        }
        assert ZoneLayout(skewed).cells(0, 0, 20, 60) == ZoneLayout(
            self.ZONES
        ).cells(0, 0, 20, 60)

    def test_boxes_leave_room_for_connections_between_them(self) -> None:
        row = {f"zone_number_{i}": Zone(f"zone_number_{i}", i, 0)
               for i in range(12)}
        layout = ZoneLayout(row)
        cols = sorted(c for _, c in layout.cells(0, 0, 10, 90).values())
        box = layout.box_width(90)
        assert box >= 5
        assert all(b - a >= box + 2 for a, b in zip(cols, cols[1:]))

    def test_single_row_map_does_not_divide_by_zero(self) -> None:
        flat = {"a": Zone("a", 0, 0), "b": Zone("b", 3, 0)}
        rows = {r for r, _ in ZoneLayout(flat).cells(0, 0, 24, 80).values()}
        assert len(rows) == 1

    def test_label_carries_the_state_marker(self) -> None:
        assert ZoneLayout.label("m8", Zone("m8", 0, 0, "restricted")) == "m8!"

    def test_long_label_keeps_its_digits_and_marker(self) -> None:
        zone = Zone("conv_restricted7", 0, 0, "restricted")
        label = ZoneLayout.label("conv_restricted7", zone, 9)
        assert len(label) == 9
        assert label.startswith("conv_") and label.endswith("7!")

    def test_label_without_digits_is_just_cut(self) -> None:
        label = ZoneLayout.label("bottleneck", Zone("bottleneck", 0, 0), 6)
        assert len(label) == 6 and label.startswith("bottl")

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
