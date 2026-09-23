"""Tests for src.visual: movements are painted by destination zone."""

from __future__ import annotations

from src.schemas import Zone
from src.simulation import Movement, TurnLog
from src.visual import NAMED, TerminalVisualizer


ZONES = {
    "hub": Zone("hub", 0, 0, color="green"),
    "sensor": Zone("sensor", 1, 0, "restricted"),
    "fast": Zone("fast", 2, 0, "priority", color="magical"),
}


def _render(enabled: bool) -> str:
    log = [TurnLog(1, [Movement(1, "hub"), Movement(2, "hub-sensor")])]
    return TerminalVisualizer(ZONES, enabled=enabled).render_log(log)


class TestColoring:
    def test_declared_color_wins(self) -> None:
        assert f"{NAMED['green']}D1-hub" in _render(True)

    def test_in_flight_uses_destination_zone_type(self) -> None:
        # No color= on `sensor`, so its restricted type colors the token.
        assert f"{NAMED['red']}D2-hub-sensor" in _render(True)

    def test_unknown_color_falls_back_to_zone_type(self) -> None:
        assert f"{NAMED['green']}fast*" in _render(True)

    def test_plain_mode_emits_no_ansi(self) -> None:
        assert "\033" not in _render(False)

    def test_legend_lists_every_zone_with_state_marker(self) -> None:
        line = _render(False).splitlines()[1]
        assert "hub" in line and "sensor!" in line and "fast*" in line
