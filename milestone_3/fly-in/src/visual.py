"""Colored terminal visualization for drone simulation output."""

from __future__ import annotations

from .schemas import Zone
from .simulation import TurnLog


# ANSI codes. Named constants rather than a dict: a typo is then an
# error at import instead of a silently uncolored string at runtime.
RESET = "\033[0m"
HEADER = "\033[1;37m"   # Bold White

# The subject allows any single word as `color=`, so unknown names fall
# back to the zone-type color rather than being an error.
NAMED = {
    "black": "\033[1;30m",
    "red": "\033[1;31m",
    "green": "\033[1;32m",
    "yellow": "\033[1;33m",
    "blue": "\033[1;34m",
    "magenta": "\033[1;35m",
    "cyan": "\033[1;36m",
    "white": "\033[1;37m",
    "gray": "\033[1;90m",
    "grey": "\033[1;90m",
}

# Fallback when a zone declares no color: its state is still visible.
# Shared with the curses UI, which maps the same words to its own palette.
TYPE_COLOR = {
    "normal": "blue",
    "priority": "green",
    "restricted": "red",
    "blocked": "gray",
}
BY_TYPE = {t: NAMED[c] for t, c in TYPE_COLOR.items()}

MARKER = {"normal": "", "priority": "*", "restricted": "!", "blocked": "x"}


class TerminalVisualizer:
    """Renders a simulation's turn log as colored terminal text.

    Each movement is painted with its destination zone's `color=`
    metadata (falling back to a per-zone-type color), so a turn line
    shows both who moved and what kind of zone they entered. A legend
    lists every zone in its own color with a state marker.

    When `enabled` is False, output is identical but plain (no ANSI
    codes) — this keeps a single rendering path for both the
    `--visual` and default CLI modes.
    """

    def __init__(
        self, zones: dict[str, Zone], *, enabled: bool = True
    ) -> None:
        """Create a visualizer over `zones`; `enabled` toggles color."""
        self._zones = zones
        self._enabled = enabled

    def _color(self, code: str, text: str) -> str:
        """Wrap `text` in an ANSI `code`, if coloring is enabled."""
        return f"{code}{text}{RESET}" if self._enabled else text

    def _zone_code(self, name: str) -> str:
        """ANSI code for `name`: its `color=`, else its zone type."""
        # In-flight destinations are `origin-dest` connection names, and
        # the subject forbids dashes inside zone names.
        zone = self._zones[name.rsplit("-", 1)[-1]]
        return NAMED.get(zone.color or "", BY_TYPE[zone.zone_type])

    def _legend(self) -> str:
        """One line naming every zone in its color, with state markers."""
        return "Zones: " + " ".join(
            self._color(
                self._zone_code(name), name + MARKER[zone.zone_type]
            )
            for name, zone in self._zones.items()
        ) + "   (* priority, ! restricted, x blocked)"

    def render_log(self, log: list[TurnLog]) -> str:
        """Render the log: a header, then one subject-format line per turn."""
        lines = [
            self._color(HEADER, "=== Fly-in Simulation ==="), self._legend()
        ]
        for turn in log:
            lines.append(" ".join(
                self._color(self._zone_code(m.destination), str(m))
                for m in turn.movements
            ))
        return "\n".join(lines)
