"""Terminal visualization of a drone simulation.

Two rendering modes share this module:

* **plain** (default CLI output) — exactly the format the subject
  specifies: one line per turn listing that turn's `D<id>-<zone>`
  movements, space-separated, and nothing else.
* **visual** (`--visual`) — the same movements, colored, plus a
  per-turn view of *zone state*: which zones hold drones, how full
  they are against their capacity, and which drones are mid-transit on
  a connection toward a restricted zone.

Zone colors come from the map's own `color=` metadata where present,
falling back to a per-zone-type palette, so a map that paints its
zones is rendered in its own colors.
"""

from __future__ import annotations

import shutil

from .graph import ZoneGraph
from .simulation import TurnLog

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# The subject allows `color=` to be any single-word string, so this is a
# best-effort name table; an unrecognised name falls back to the zone's
# type color rather than being dropped.
NAMED_COLORS: dict[str, str] = {
    # Rendered as bright black: true black (30) is invisible against a
    # dark terminal background, and some maps do ask for it.
    "black": "\033[90m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "orange": "\033[38;5;208m",
    "pink": "\033[38;5;213m",
    "brown": "\033[38;5;130m",
}

# Fallback palette and glyph, keyed by zone type.
TYPE_COLORS: dict[str, str] = {
    "normal": "\033[37m",
    "restricted": "\033[31m",
    "priority": "\033[32m",
    "blocked": "\033[90m",
}

TYPE_MARKS: dict[str, str] = {
    "normal": "·",
    "restricted": "!",
    "priority": "*",
    "blocked": "x",
}

START_MARK = ">"
END_MARK = "#"
INFINITE = "∞"


class TerminalVisualizer:
    """Renders a simulation's turn log as terminal text.

    Args:
        graph: The zone network, used for per-zone type, capacity and
            color lookups.
        enabled: When True, render the full colored zone-state view.
            When False, emit only the subject's plain movement lines.
    """

    def __init__(self, graph: ZoneGraph, *, enabled: bool = True) -> None:
        """Create a visualizer bound to `graph`."""
        self._graph = graph
        self._enabled = enabled
        self._width = shutil.get_terminal_size((100, 24)).columns

    # ---------------------------------------------------------------
    # Color helpers
    # ---------------------------------------------------------------

    def _paint(self, code: str, text: str) -> str:
        """Wrap `text` in an ANSI `code`, unless coloring is disabled."""
        if not self._enabled or not code:
            return text
        return f"{code}{text}{RESET}"

    def _zone_code(self, name: str) -> str:
        """Return the ANSI color for a zone.

        The map's own `color=` wins; an unset or unrecognised color
        falls back to the palette for the zone's type.
        """
        named = self._graph.zone_color(name)
        if named is not None:
            code = NAMED_COLORS.get(named.lower())
            if code is not None:
                return code
        return TYPE_COLORS.get(self._graph.zone_type(name), "")

    def _zone_mark(self, name: str) -> str:
        """Return the one-character glyph identifying a zone's role."""
        if name == self._graph.start_name:
            return START_MARK
        if name == self._graph.end_name:
            return END_MARK
        return TYPE_MARKS.get(self._graph.zone_type(name), "?")

    def _capacity_label(self, name: str) -> str:
        """Return a zone's capacity, with start/end shown as unlimited."""
        if name in (self._graph.start_name, self._graph.end_name):
            return INFINITE
        return str(self._graph.zone_capacity(name))

    def _zone_order(self, names: list[str]) -> list[str]:
        """Sort zones start-first, end-last, the rest alphabetically."""
        start, end = self._graph.start_name, self._graph.end_name

        def key(name: str) -> tuple[int, str]:
            if name == start:
                return (0, "")
            if name == end:
                return (2, "")
            return (1, name)

        return sorted(names, key=key)

    # ---------------------------------------------------------------
    # Static map view
    # ---------------------------------------------------------------

    def render_map(self, nb_drones: int) -> str:
        """Render the network itself: every zone with type and capacity."""
        zones = self._zone_order(list(self._graph.zones))
        header = self._paint(
            BOLD, f"Network: {len(zones)} zones, {nb_drones} drones"
        )
        cells = [
            self._paint(
                self._zone_code(name),
                f"{self._zone_mark(name)}{name}"
                f"[{self._capacity_label(name)}]",
            )
            for name in zones
        ]
        return "\n".join([header, *self._wrap(cells, indent="  ")])

    def render_legend(self) -> str:
        """Render the glyph/color key for the zone types."""
        parts = [
            self._paint(TYPE_COLORS[zone_type], f"{mark} {zone_type}")
            for zone_type, mark in TYPE_MARKS.items()
        ]
        parts.append(self._paint(BOLD, f"{START_MARK} start"))
        parts.append(self._paint(BOLD, f"{END_MARK} end"))
        return self._paint(DIM, "Legend: ") + "  ".join(parts)

    # ---------------------------------------------------------------
    # Per-turn views
    # ---------------------------------------------------------------

    def render_movements(self, turn: TurnLog) -> str:
        """Return the subject's plain movement line for one turn."""
        return " ".join(turn.movements)

    def _painted_movements(self, turn: TurnLog) -> str:
        """Return the movement tokens, each colored by its destination."""
        if not turn.movements:
            return self._paint(DIM, "(no movement)")
        painted = []
        for move in turn.movements:
            _, _, dest = move.partition("-")
            # A restricted-zone transit token is `D1-<from>-<to>`; color
            # it by the zone the drone is heading for.
            target = dest.rpartition("-")[2] if "-" in dest else dest
            painted.append(self._paint(self._zone_code(target), move))
        return " ".join(painted)

    def _occupancy(self, turn: TurnLog) -> tuple[dict[str, list[int]],
                                                 dict[str, list[int]]]:
        """Split a turn's drone locations into zones and in-transit links."""
        zones: dict[str, list[int]] = {}
        links: dict[str, list[int]] = {}
        for drone_id, where in sorted(turn.locations.items()):
            bucket = links if where not in self._graph.zones else zones
            bucket.setdefault(where, []).append(drone_id)
        return zones, links

    def render_state(self, turn: TurnLog) -> list[str]:
        """Render the occupied zones and in-transit links for one turn."""
        zones, links = self._occupancy(turn)
        cells: list[str] = []

        for name in self._zone_order(list(zones)):
            drones = zones[name]
            count = len(drones)
            label = (
                f"{self._zone_mark(name)}{name} "
                f"{count}/{self._capacity_label(name)}"
            )
            if name == self._graph.end_name:
                delivered = [d for d in drones if d in turn.delivered]
                if delivered:
                    label += " ok"
            cells.append(self._paint(self._zone_code(name), label))

        for link, drones in sorted(links.items()):
            origin, _, target = link.rpartition("-")
            cells.append(
                self._paint(
                    self._zone_code(target),
                    f"~{origin}>{target} {len(drones)}",
                )
            )

        return self._wrap(cells, indent="          ")

    def _wrap(self, cells: list[str], *, indent: str) -> list[str]:
        """Pack colored cells into lines that fit the terminal width."""
        lines: list[str] = []
        current: list[str] = []
        used = len(indent)
        for cell in cells:
            visible = self._visible_len(cell)
            if current and used + visible + 2 > self._width:
                lines.append(indent + "  ".join(current))
                current, used = [], len(indent)
            current.append(cell)
            used += visible + 2
        if current:
            lines.append(indent + "  ".join(current))
        return lines

    @staticmethod
    def _visible_len(text: str) -> int:
        """Length of `text` ignoring ANSI escape sequences."""
        length = 0
        in_escape = False
        for char in text:
            if in_escape:
                in_escape = char != "m"
            elif char == "\033":
                in_escape = True
            else:
                length += 1
        return length

    # ---------------------------------------------------------------
    # Whole-log rendering
    # ---------------------------------------------------------------

    def render_log(self, log: list[TurnLog], nb_drones: int) -> str:
        """Render the full simulation.

        In plain mode this is exactly the subject's output format: one
        movement line per turn. In visual mode each turn is followed by
        its zone-state view, framed by the network map and a legend.
        """
        if not self._enabled:
            return "\n".join(self.render_movements(t) for t in log)

        lines = [
            self._paint(BOLD, "=== Fly-in Simulation ==="),
            self.render_map(nb_drones),
            self.render_legend(),
            "",
        ]
        for entry in log:
            lines.append(
                f"{self._paint(BOLD, f'Turn {entry.turn:3d}')} "
                f"{self._painted_movements(entry)}"
            )
            lines.extend(self.render_state(entry))
        lines.append("")
        lines.append(
            self._paint(
                BOLD,
                f"Total turns: {len(log)}  "
                f"Delivered: {len(log[-1].delivered) if log else 0}"
                f"/{nb_drones}",
            )
        )
        return "\n".join(lines)

    def print_log(self, log: list[TurnLog], nb_drones: int) -> None:
        """Print the rendered simulation to stdout."""
        print(self.render_log(log, nb_drones))
