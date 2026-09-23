"""Curses terminal UI: the zone network drawn and animated in the shell.

Works over ssh and on a 42 lab machine with no windowing system. It
replays a :class:`~src.simulation.SimulationFilm` built from the same
turn log the text output prints, so the two can never disagree.

`curses` ships with CPython on Unix, so this adds no dependency.
"""

from __future__ import annotations

import curses
import time

from .schemas import MapFile, Zone
from .simulation import SimulationFilm, TurnLog
from .visual import MARKER, NAMED, TYPE_COLOR

PAD_X, PAD_Y = 2, 1
CHROME_ROWS = 4     # title, legend, status, and a spare row for drones
MIN_COLS, MIN_ROWS = 60, 14

# The subject allows any single word as `color=`; NAMED is the set both
# renderers recognise, and anything else falls back to the zone type.
CURSES_COLOR = {
    "black": curses.COLOR_BLACK,
    "red": curses.COLOR_RED,
    "green": curses.COLOR_GREEN,
    "yellow": curses.COLOR_YELLOW,
    "blue": curses.COLOR_BLUE,
    "magenta": curses.COLOR_MAGENTA,
    "cyan": curses.COLOR_CYAN,
    "white": curses.COLOR_WHITE,
    "gray": curses.COLOR_WHITE,
    "grey": curses.COLOR_WHITE,
}


class ZoneLayout:
    """Places zones on a character grid — pure math, no curses.

    Kept separate from the rendering so the placement can be unit-tested
    headlessly, the same way :class:`SimulationFilm` is.
    """

    def __init__(self, zones: dict[str, Zone]) -> None:
        """Bind the layout to the parsed map's zones."""
        self._zones = zones

    @staticmethod
    def label(name: str, zone: Zone) -> str:
        """The text drawn for a zone: name, state marker, capacity."""
        text = name + MARKER[zone.zone_type]
        if zone.max_drones > 1:
            text += f"[{zone.max_drones}]"
        return text

    @staticmethod
    def fit(col: int, cols: int, text: str) -> int:
        """Shift `col` left so `text` ends inside a `cols`-wide screen."""
        return max(0, min(col, cols - 1 - len(text)))

    def cells(self, rows: int, cols: int) -> dict[str, tuple[int, int]]:
        """Scale each zone's `x y` onto a `(row, col)` terminal cell."""
        xs = [z.x for z in self._zones.values()]
        ys = [z.y for z in self._zones.values()]
        # A map may be a single row or column, hence the `or 1` guards.
        span_x = (max(xs) - min(xs)) or 1
        span_y = (max(ys) - min(ys)) or 1
        label = max(
            len(self.label(n, z)) for n, z in self._zones.items()
        ) + 2
        wide = max(1, cols - 2 * PAD_X - label)
        tall = max(1, rows - PAD_Y - CHROME_ROWS - 1)
        return {
            name: (
                PAD_Y + round((z.y - min(ys)) * tall / span_y),
                PAD_X + round((z.x - min(xs)) * wide / span_x),
            )
            for name, z in self._zones.items()
        }

    @staticmethod
    def segments(
        a: tuple[int, int], b: tuple[int, int]
    ) -> list[tuple[int, int, str]]:
        """Interior cells of the line from `a` to `b`, each with its glyph.

        The glyph comes from the step that reached the cell, not from the
        connection's overall slope: a line that advances two columns per
        row is a run of `-` with a `\\` where it drops, which is what an
        ASCII diagram looks like. Picking one glyph per connection instead
        painted those rows as `\\\\\\` blobs.
        """
        steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        cells: list[tuple[int, int, str]] = []
        prev = a
        for i in range(1, steps):
            row = a[0] + round((b[0] - a[0]) * i / steps)
            col = a[1] + round((b[1] - a[1]) * i / steps)
            if col == prev[1]:
                glyph = "|"
            elif row == prev[0]:
                glyph = "-"
            else:
                glyph = "\\" if (row > prev[0]) == (col > prev[1]) else "/"
            cells.append((row, col, glyph))
            prev = (row, col)
        return cells


class TerminalUI:
    """Animates the simulation on a curses screen.

    Space pauses and resumes, the arrow keys step one turn at a time,
    `r` restarts the replay and `q` quits.
    """

    def __init__(
        self,
        map_data: MapFile,
        log: list[TurnLog],
        *,
        delay_ms: int = 700,
    ) -> None:
        """Bind the UI to a parsed map and its simulation log."""
        self._map = map_data
        self._layout = ZoneLayout(map_data.zones)
        self._frames = SimulationFilm(
            log, map_data.start.name, map_data.nb_drones
        ).frames()
        self._delay = delay_ms / 1000
        self._index = 0
        self._playing = True
        self._pairs: dict[str, int] = {}

    def run(self) -> None:
        """Take over the terminal and replay until the user quits."""
        curses.wrapper(self._loop)

    def _init_colors(self) -> None:
        """Allocate one curses pair per color word the map may use."""
        if not curses.has_colors():
            return
        curses.use_default_colors()
        for index, (name, code) in enumerate(CURSES_COLOR.items(), start=1):
            curses.init_pair(index, code, -1)
            self._pairs[name] = index

    def _attr(self, name: str) -> int:
        """Curses attribute for a zone: its `color=`, else its type."""
        zone = self._map.zones[name]
        word = zone.color if zone.color in NAMED else TYPE_COLOR[
            zone.zone_type
        ]
        attr = curses.color_pair(self._pairs.get(word or "", 0))
        if name in (self._map.start.name, self._map.end.name):
            attr |= curses.A_BOLD | curses.A_REVERSE
        return attr

    @staticmethod
    def _put(
        screen: curses.window, row: int, col: int, text: str, attr: int = 0
    ) -> None:
        """Write `text` if it fits; curses raises on the last cell."""
        rows, cols = screen.getmaxyx()
        if not (0 <= row < rows and 0 <= col < cols):
            return
        try:
            screen.addnstr(row, col, text, cols - col - 1, attr)
        except curses.error:  # pragma: no cover - bottom-right cell
            pass

    def _draw(self, screen: curses.window) -> None:
        """Render one frame: links, zones, drones, and the status bar."""
        screen.erase()
        rows, cols = screen.getmaxyx()
        if rows < MIN_ROWS or cols < MIN_COLS:
            self._put(screen, 0, 0, f"terminal too small (need "
                                    f"{MIN_COLS}x{MIN_ROWS})")
            screen.refresh()
            return

        cell = self._layout.cells(rows, cols)
        for conn in self._map.connections:
            for row, col, glyph in self._layout.segments(
                cell[conn.from_zone], cell[conn.to_zone]
            ):
                self._put(screen, row, col, glyph, curses.A_DIM)

        for name, zone in self._map.zones.items():
            row, col = cell[name]
            self._put(
                screen, row, col,
                self._layout.label(name, zone), self._attr(name),
            )

        self._draw_drones(screen, cell)
        self._draw_chrome(screen, rows, cols)
        screen.refresh()

    def _draw_drones(
        self, screen: curses.window, cell: dict[str, tuple[int, int]]
    ) -> None:
        """Print the drone ids parked at each zone or in flight."""
        cols = screen.getmaxyx()[1]
        here: dict[str, list[int]] = {}
        for drone_id, position in sorted(self._frames[self._index].items()):
            here.setdefault(position, []).append(drone_id)
        for position, ids in here.items():
            if position in cell:
                row, col = cell[position]
                row += 1
            else:
                # In flight: `origin-dest`, and zone names have no dashes.
                origin, dest = position.rsplit("-", 1)
                line = self._layout.segments(cell[origin], cell[dest])
                row, col = (
                    line[len(line) // 2][:2] if line else cell[dest]
                )
            # A zone at the right margin has less room than its queue
            # needs, so shift the ids left instead of losing them.
            # ponytail: a queue wider than the whole screen (50+ drones
            # at 80 columns) still truncates; show a count if that lands.
            text = " ".join(f"{i}" for i in ids)
            self._put(
                screen, row, self._layout.fit(col, cols, text), text,
                curses.A_BOLD,
            )

    def _draw_chrome(
        self, screen: curses.window, rows: int, cols: int
    ) -> None:
        """Draw the title, the zone-type legend and the status bar."""
        delivered = sum(
            1 for p in self._frames[self._index].values()
            if p == self._map.end.name
        )
        self._put(screen, 0, 0, "=== Fly-in Simulation ===", curses.A_BOLD)
        self._put(
            screen, rows - 2, 0,
            "* priority  ! restricted  x blocked  [N] capacity",
            curses.A_DIM,
        )
        keys = (
            f"   [space] {'pause' if self._playing else 'play':<5}  "
            "[<-/->] step  [r] replay  [q] quit"
        )
        status = (
            f"Turn {self._index}/{len(self._frames) - 1}   "
            f"delivered {delivered}/{self._map.nb_drones}"
        )
        # Chopping the key hints mid-word is worse than dropping them.
        if len(status) + len(keys) >= cols:
            keys = ""
        self._put(screen, rows - 1, 0, status + keys, curses.A_BOLD)

    def _step(self, delta: int) -> None:
        """Move the replay `delta` frames, clamped to the film's bounds."""
        self._index = max(0, min(len(self._frames) - 1, self._index + delta))

    def _loop(self, screen: curses.window) -> None:
        """Event loop: redraw, read a key, advance on the timer."""
        curses.curs_set(0)
        screen.timeout(40)
        self._init_colors()
        last = time.monotonic()
        while True:
            self._draw(screen)
            key = screen.getch()
            if key in (ord("q"), 27):
                return
            if key == ord(" "):
                self._playing = not self._playing
            elif key == curses.KEY_RIGHT:
                self._playing = False
                self._step(1)
            elif key == curses.KEY_LEFT:
                self._playing = False
                self._step(-1)
            elif key == ord("r"):
                self._index, self._playing = 0, True
            now = time.monotonic()
            if self._playing and now - last >= self._delay:
                last = now
                if self._index < len(self._frames) - 1:
                    self._step(1)
                else:
                    self._playing = False
