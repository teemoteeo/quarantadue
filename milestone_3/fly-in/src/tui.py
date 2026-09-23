"""Interfaccia curses: la rete di zone disegnata e animata nel terminale.

Funziona via ssh e sui computer del lab 42 senza interfaccia
grafica. Riproduce un :class:`~src.simulation.SimulationFilm` creato
dallo stesso log dei turni che stampa l'output testuale, quindi i
due non possono mai essere in disaccordo.

`curses` è incluso in CPython su Unix, quindi non aggiunge
dipendenze.
"""

from __future__ import annotations

import curses
import locale
import math
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

from .schemas import MapFile, Zone
from .simulation import SimulationFilm, TurnLog
from .visual import MARKER, NAMED, TYPE_COLOR

UNICODE = (sys.stdout.encoding or "").lower().startswith("utf")
FREE, ARROW, BAR, CUT = (
    ("□", "→", "█", "…") if UNICODE else (".", ">", "#", "~")
)
# Box drawing: top-left, top-right, bottom-left, bottom-right, edges.
TL, TR, BL, BR, HORIZ, VERT = "┌┐└┘─│" if UNICODE else "++++-|"
SLOTS_MAX = 6       # above this capacity, free slots become `n/cap`
PANEL_W = 38        # side panel, shown by default only if the map keeps
PANEL_MIN_PITCH = 11  # at least this many columns per zone column
HEADER_ROWS, FOOTER_ROWS = 2, 2
MIN_COLS = 60
DELAYS_MS = (150, 300, 600, 1000, 1500, 2500)  # per turn

Cell = tuple[int, int]
# The free cells of each link, keyed (from, to) in both directions and
# listed in that walking order.
Paths = dict[tuple[str, str], list[Cell]]


# Parse, plan and simulate a map file; raises on a bad map.
Loader = Callable[[Path], tuple[MapFile, list[list[str]], list[TurnLog]]]
KEY_ENTER = (10, 13, curses.KEY_ENTER)

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
    """Posiziona le zone su una griglia di caratteri, senza curses.

    Le coordinate vengono compresse per rango: la k-esima `x` diversa
    diventa la colonna k e la k-esima `y` diversa diventa la riga k. Le
    zone mantengono l'ordine sinistra/destra e su/giù, ogni colonna ha
    la stessa larghezza e i riquadri non si sovrappongono mai. Ogni
    zona è un riquadro di 3 righe: il nome sul bordo in alto, i droni
    nella riga centrale.
    """

    def __init__(self, zones: dict[str, Zone]) -> None:
        """Collega il layout alle zone della mappa letta."""
        self._zones = zones
        self._xs = sorted({z.x for z in zones.values()})
        self._ys = sorted({z.y for z in zones.values()})

    @property
    def min_height(self) -> int:
        """Righe per la mappa: 3 per ogni `y` diversa, più 1 di spazio."""
        return 4 * len(self._ys) - 1

    @property
    def min_width(self) -> int:
        """Colonne per la mappa: 5 per ogni `x` diversa, più gli spazi."""
        return 8 * len(self._xs)

    @staticmethod
    def label(name: str, zone: Zone, width: int = 0) -> str:
        """Nome e simbolo di stato di una zona, adattati a `width` se c'è.

        Un nome lungo mantiene le cifre finali, che di solito distinguono
        zone simili: `conv_restricted7!` in 9 colonne diventa
        `conv_…7!`.
        """
        marker = MARKER[zone.zone_type]
        room = width - len(marker)
        if not width or len(name) <= room:
            return name + marker
        tail = min(len(name) - len(name.rstrip("0123456789")), room - 2)
        head = room - max(tail, 0) - 1
        return name[:head] + CUT + name[len(name) - max(tail, 0):] + marker

    def pitch(self, width: int) -> int:
        """Colonne per ogni `x` diversa in una mappa larga `width`."""
        return max(8, width // len(self._xs))

    def box_width(self, width: int) -> int:
        """Larghezza di un riquadro in una mappa larga `width`.

        È il nome più lungo più i bordi, limitata in modo da lasciare un
        terzo di ogni colonna al collegamento tra i riquadri, dove si vedono
        scorrere i droni.
        """
        longest = max(
            len(self.label(n, z)) for n, z in self._zones.items()
        )
        pitch = self.pitch(width)
        return min(pitch - max(3, pitch // 3), max(longest, 5) + 2)

    def cells(
        self, top: int, left: int, height: int, width: int
    ) -> dict[str, tuple[int, int]]:
        """Angolo in alto a sinistra `(riga, colonna)` di ogni riquadro."""
        pitch_x = self.pitch(width)
        pitch_y = max(4, height // len(self._ys))
        used_w = pitch_x * (len(self._xs) - 1) + self.box_width(width)
        used_h = pitch_y * (len(self._ys) - 1) + 3
        left += max(0, (width - used_w) // 2)
        top += max(0, (height - used_h) // 2)
        return {
            name: (
                top + self._ys.index(z.y) * pitch_y,
                left + self._xs.index(z.x) * pitch_x,
            )
            for name, z in self._zones.items()
        }

    @staticmethod
    def segments(
        a: tuple[int, int], b: tuple[int, int]
    ) -> list[tuple[int, int, str]]:
        """Celle interne della linea da `a` a `b`, ognuna con il suo carattere.

        Il carattere dipende dal passo che ha raggiunto la cella, non dalla
        pendenza generale del collegamento: una linea che avanza di due
        colonne per riga è una serie di `-` con un `\\` dove scende, proprio
        come in un disegno ASCII.
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
    """Anima la simulazione in una schermata curses, drone per drone.

    La riproduzione segue un orologio continuo: tra due turni ogni
    drone in movimento scorre lungo il suo collegamento, disegnato con
    il suo numero, così si può seguire ogni drone da una zona all'altra.
    Un viaggio verso una zona restricted si ferma a metà collegamento
    dopo il primo turno e atterra al secondo. Da fermi, ogni zona mostra
    i suoi droni accanto ai posti liberi (`□`), in rosso quando è piena;
    i droni che si sono mossi per ultimi sono evidenziati.

    I collegamenti sono colorati in base al traffico: giallo mentre un
    drone ci passa, normale se prima o poi viene usato, spento se il
    piano non lo usa mai. Il pannello laterale elenca le mosse del turno
    e le zone occupate; si nasconde se la mappa ha bisogno di spazio.
    Spazio avvia o mette in pausa, le frecce vanno avanti o indietro di
    un turno, `+`/`-` cambiano la velocità, `p` mostra o nasconde il
    pannello, `m` apre la scelta della mappa, `r` ricomincia e `q` esce.
    """

    def __init__(
        self,
        map_data: MapFile,
        log: list[TurnLog],
        *,
        path: Path,
        maps: dict[str, Path] | None = None,
        loader: Loader | None = None,
    ) -> None:
        """Collega la UI a una mappa, al suo log e al suo file.

        `maps` e `loader` permettono di passare a un'altra mappa dalla UI.
        """
        self._maps = maps or {}
        self._loader = loader
        self._picking = False
        self._choice = 0
        self._error = ""
        self._speed = DELAYS_MS.index(1000)
        self._panel: bool | None = None  # None: decided by terminal width
        self._cols = 0  # width at the last draw, for the panel toggle
        self._pairs: dict[str, int] = {}
        self._show(map_data, log, path)

    def _show(
        self, map_data: MapFile, log: list[TurnLog], path: Path
    ) -> None:
        """Sostituisce la riproduzione con `map_data` e la fa ripartire."""
        self._map = map_data
        self._path = path
        self._layout = ZoneLayout(map_data.zones)
        self._frames = SimulationFilm(
            log, map_data.start.name, map_data.nb_drones
        ).frames()
        self._last = len(self._frames) - 1
        self._turn_links = [self._links(i) for i in range(len(self._frames))]
        self._used_links = set().union(*self._turn_links)
        # Playback clock, in turns: 2.5 is halfway through turn 3. It
        # glides toward `_target`, which is the last turn while playing.
        self._t = 0.0
        self._target = float(self._last)
        self._playing = True

    # ------------------------------------------------------------ clock

    @property
    def turn(self) -> int:
        """Il turno sullo schermo: in animazione o appena finito."""
        return math.ceil(self._t - 1e-9)

    @property
    def progress(self) -> float:
        """Quanto è avanzata l'animazione di `turn`, in (0, 1]."""
        return 1.0 - (self.turn - self._t)

    def advance(self, seconds: float) -> None:
        """Porta l'orologio verso il suo obiettivo alla velocità attuale."""
        step = seconds * 1000 / DELAYS_MS[self._speed]
        if self._t < self._target:
            self._t = min(self._target, self._t + step)
        else:
            self._t = max(self._target, self._t - step)
        if self._t == self._target:
            self._playing = False

    def _links(self, index: int) -> set[frozenset[str]]:
        """Collegamenti su cui c'è qualche drone durante il turno `index`."""
        links: set[frozenset[str]] = set()
        if index == 0:
            return links
        before, after = self._frames[index - 1], self._frames[index]
        for drone_id, pos in after.items():
            prev = before[drone_id]
            if pos == prev:
                continue
            if "-" in pos:  # departing on a transit: `origin-dest`
                links.add(frozenset(pos.split("-")))
            elif "-" in prev:  # landing from one
                links.add(frozenset(prev.split("-")))
            else:
                links.add(frozenset((prev, pos)))
        return links

    def _movers(self) -> set[int]:
        """Droni che si muovono nel turno sullo schermo."""
        if self.turn == 0:
            return set()
        prev, cur = self._frames[self.turn - 1], self._frames[self.turn]
        return {d for d in cur if cur[d] != prev[d]}

    def _resting(self) -> dict[int, str]:
        """Posizione di ogni drone che in questo momento non è in movimento."""
        cur = self._frames[self.turn]
        if self.progress >= 1.0:
            return dict(cur)
        movers = self._movers()
        return {d: p for d, p in cur.items() if d not in movers}

    # ----------------------------------------------------------- curses

    def run(self) -> None:
        """Prende il terminale e riproduce finché l'utente non esce."""
        try:
            locale.setlocale(locale.LC_ALL, "")
        except locale.Error:  # e.g. LANG names a locale not installed
            pass
        curses.wrapper(self._loop)

    def _init_colors(self) -> None:
        """Crea una coppia curses per ogni colore che la mappa può usare."""
        if not curses.has_colors():
            return
        try:
            curses.use_default_colors()
            background = -1  # the terminal's own background
        except curses.error:
            background = curses.COLOR_BLACK
        for index, (name, code) in enumerate(CURSES_COLOR.items(), start=1):
            curses.init_pair(index, code, background)
            self._pairs[name] = curses.color_pair(index)

    def _color(self, word: str) -> int:
        """Attributo curses per un colore; normale se i colori mancano."""
        return self._pairs.get(word, 0)

    @staticmethod
    def _zone_word(zone: Zone) -> str:
        """Colore di una zona: il suo `color=`, se no quello del tipo."""
        if zone.color in NAMED:
            return zone.color or ""
        return TYPE_COLOR[zone.zone_type]

    def _zone_attr(self, name: str) -> int:
        """Attributo curses per il nome di una zona: colore e grassetto."""
        attr = self._color(self._zone_word(self._map.zones[name]))
        attr |= curses.A_BOLD
        if name in (self._map.start.name, self._map.end.name):
            attr |= curses.A_REVERSE
        return attr

    @staticmethod
    def _put(
        screen: curses.window, row: int, col: int, text: str, attr: int = 0
    ) -> None:
        """Scrive `text` se ci sta; curses dà errore sull'ultima cella."""
        rows, cols = screen.getmaxyx()
        if not (0 <= row < rows and 0 <= col < cols):
            return
        try:
            screen.addnstr(row, col, text, cols - col - 1, attr)
        except curses.error:  # pragma: no cover - bottom-right cell
            pass

    # ---------------------------------------------------------- drawing

    def draw(self, screen: curses.window) -> None:
        """Disegna un fotogramma: intestazione, mappa, pannello e fondo."""
        screen.erase()
        rows, cols = screen.getmaxyx()
        self._cols = cols
        need_rows = self._layout.min_height + HEADER_ROWS + FOOTER_ROWS
        need_cols = max(MIN_COLS, self._layout.min_width + 2)
        if rows < need_rows or cols < need_cols:
            self._put(screen, 0, 0, f"Terminal too small: need at least "
                                    f"{need_cols}x{need_rows}, "
                                    f"have {cols}x{rows}")
            if self._maps:
                self._put(screen, 1, 0, "[m] choose another map  [q] quit")
            if self._picking:
                self._draw_picker(screen, rows, cols)
            screen.refresh()
            return
        panel = self._panel_shown(cols)
        map_w = cols - (PANEL_W + 1 if panel else 0) - 2
        map_h = rows - HEADER_ROWS - FOOTER_ROWS
        self._draw_header(screen, cols)
        self._draw_map(screen, HEADER_ROWS, 1, map_h, map_w)
        if panel:
            self._draw_panel(screen, cols - PANEL_W, rows)
        self._draw_footer(screen, rows)
        if self._picking:
            self._draw_picker(screen, rows, cols)
        screen.refresh()

    def _current(self) -> str:
        """Nome nella lista della mappa sullo schermo, o "" se non c'è."""
        here = self._path.resolve()
        return next(
            (n for n, p in self._maps.items() if p.resolve() == here), ""
        )

    def _draw_picker(
        self, screen: curses.window, rows: int, cols: int
    ) -> None:
        """La lista delle mappe, in un riquadro al centro dello schermo."""
        names = list(self._maps)
        current = self._current()
        width = min(cols - 2, max(max(len(n) for n in names) + 8, 58))
        room = max(1, rows - 8)
        first = min(max(0, self._choice - room // 2),
                    max(0, len(names) - room))
        shown = names[first:first + room]
        height = len(shown) + 4  # borders, one blank row, the hint
        top, left = max(0, (rows - height) // 2), max(0, (cols - width) // 2)
        inner = width - 2
        frame = curses.A_BOLD
        title = " Choose a map "
        self._put(screen, top, left,
                  TL + title + HORIZ * (inner - len(title)) + TR, frame)
        for i in range(1, height - 1):
            self._put(screen, top + i, left,
                      VERT + " " * inner + VERT, frame)
        self._put(screen, top + height - 1, left,
                  BL + HORIZ * inner + BR, frame)
        for i, name in enumerate(shown, start=first):
            mark = "*" if name == current else " "
            text = f" {mark} {name}"[:inner - 1]
            attr = curses.A_REVERSE | curses.A_BOLD if i == self._choice else 0
            self._put(screen, top + 1 + i - first, left + 1,
                      text.ljust(inner - 1), attr)
        hint = (self._error or
                "[up/down] select  [enter] load  [m] close   * current")
        self._put(
            screen, top + height - 2, left + 2, hint[:inner - 2],
            self._color("red") | curses.A_BOLD if self._error
            else curses.A_DIM,
        )

    def _panel_shown(self, cols: int) -> bool:
        """Se mostrare il pannello: la scelta dell'utente, se no automatico."""
        if cols - PANEL_W - 3 < max(MIN_COLS, self._layout.min_width):
            return False
        if self._panel is not None:
            return self._panel
        return self._layout.pitch(cols - PANEL_W - 3) >= PANEL_MIN_PITCH

    def _draw_header(self, screen: curses.window, cols: int) -> None:
        """Titolo, turno, barra dei droni arrivati e stato di riproduzione."""
        delivered = sum(
            p == self._map.end.name for p in self._resting().values()
        )
        filled = 10 * delivered // self._map.nb_drones
        right = (
            f"turn {self.turn}/{self._last}  "
            f"{BAR * filled}{FREE * (10 - filled)} "
            f"{delivered}/{self._map.nb_drones} delivered  "
            f"{'playing' if self._playing else 'paused'} "
            f"{DELAYS_MS[self._speed]}ms "
        )
        title = f"FLY-IN  {self._path.name}"
        if len(title) + len(right) + 3 > cols:
            title = "FLY-IN"
        if len(title) + len(right) + 3 > cols:
            right = (
                f"turn {self.turn}/{self._last}  "
                f"{delivered}/{self._map.nb_drones} delivered "
            )
        self._put(screen, 0, 1, title, curses.A_BOLD)
        self._put(
            screen, 0, max(0, cols - len(right) - 1), right, curses.A_BOLD
        )
        self._put(screen, 1, 0, "-" * cols, curses.A_DIM)

    def geometry(
        self, top: int, left: int, h: int, w: int
    ) -> tuple[dict[str, Cell], dict[str, str], dict[str, Cell], Paths]:
        """Angoli dei riquadri, nomi adattati, centri e percorsi dei link.

        Un link va dal centro di un riquadro all'altro, e il suo percorso
        tiene solo le celle fuori da tutti i riquadri: le linee si fermano
        ai bordi, e un drone che scorre lungo una linea non copre mai una
        zona.
        """
        cell = self._layout.cells(top, left, h, w)
        box = self._layout.box_width(w)
        labels = {
            n: self._layout.label(n, z, box - 2)
            for n, z in self._map.zones.items()
        }
        taken = {
            (r + dr, c + dc)
            for r, c in cell.values() for dr in range(3) for dc in range(box)
        }
        anchor = {n: (r + 1, c + box // 2) for n, (r, c) in cell.items()}
        paths: Paths = {}
        for conn in self._map.connections:
            a, b = conn.from_zone, conn.to_zone
            line = [
                (r, c) for r, c, _ in
                self._layout.segments(anchor[a], anchor[b])
                if (r, c) not in taken
            ]
            paths[(a, b)] = line or [anchor[b]]
            paths[(b, a)] = line[::-1] or [anchor[a]]
        return cell, labels, anchor, paths

    def drone_cells(self, paths: Paths) -> dict[int, Cell]:
        """Dove disegnare ogni drone fuori da una zona: in volo o a metà.

        Un drone che va `a -> b` percorre le celle del link partendo da
        `a`; `a -> a-b` (primo turno di un viaggio) arriva fino a metà;
        `a-b -> b` parte da metà. Un drone fermo durante un viaggio aspetta
        a metà.
        """
        placed: dict[int, Cell] = {}
        cur = self._frames[self.turn]
        prev = self._frames[self.turn - 1] if self.turn else cur
        moving = self._movers() if self.progress < 1.0 else set()
        for drone_id, pos in cur.items():
            if drone_id in moving:
                route = self._route(prev[drone_id], pos, paths)
                step = int(self.progress * len(route))
                placed[drone_id] = route[min(step, len(route) - 1)]
            elif "-" in pos:  # resting halfway down a transit
                origin, target = pos.split("-")
                line = paths[(origin, target)]
                placed[drone_id] = line[len(line) // 2]
        return placed

    @staticmethod
    def _route(src: str, dst: str, paths: Paths) -> list[Cell]:
        """Celle che un drone percorre da `src` a `dst`, in ordine."""
        if "-" in dst:  # a -> a-b: first half of the link, to its midpoint
            origin, target = dst.split("-")
            line = paths[(origin, target)]
            return line[:len(line) // 2 + 1]
        if "-" in src:  # a-b -> b: from the midpoint on
            origin, target = src.split("-")
            line = paths[(origin, target)]
            return line[len(line) // 2:]
        return paths[(src, dst)]

    def _draw_map(
        self, screen: curses.window, top: int, left: int, h: int, w: int
    ) -> None:
        """Link in base al traffico, riquadri con i droni, droni in volo.

        Prima si disegnano le linee da centro a centro; i riquadri,
        disegnati dopo con l'interno vuoto, coprono le estremità così ogni
        linea tocca un bordo.
        """
        cell, labels, anchor, paths = self.geometry(top, left, h, w)
        active = self._turn_links[self.turn]
        for conn in self._map.connections:
            link = frozenset((conn.from_zone, conn.to_zone))
            if link in active:
                attr = self._color("yellow") | curses.A_BOLD
            elif link in self._used_links:
                attr = curses.A_NORMAL
            else:
                attr = curses.A_DIM
            for row, col, glyph in self._layout.segments(
                anchor[conn.from_zone], anchor[conn.to_zone]
            ):
                self._put(screen, row, col, glyph, attr)

        box = self._layout.box_width(w)
        here: dict[str, list[int]] = {}
        for drone_id, pos in sorted(self._resting().items()):
            here.setdefault(pos, []).append(drone_id)
        movers = self._movers()
        for name, (row, col) in cell.items():
            ids = here.get(name, [])
            self._draw_box(screen, row, col, box, labels[name], name, ids)
            self._draw_occupants(
                screen, row + 1, col + 1, box - 2, name, ids, movers
            )

        airborne: dict[Cell, list[int]] = {}
        for drone_id, spot in self.drone_cells(paths).items():
            airborne.setdefault(spot, []).append(drone_id)
        for (row, col), ids in airborne.items():
            gliding = self.progress < 1 and any(d in movers for d in ids)
            attr = (
                self._color("yellow") | curses.A_BOLD | curses.A_REVERSE
                if gliding else self._color("magenta") | curses.A_BOLD
            )
            self._put(screen, row, col, ",".join(map(str, ids)), attr)

    def _draw_box(
        self,
        screen: curses.window,
        row: int,
        col: int,
        box: int,
        label: str,
        name: str,
        ids: list[int],
    ) -> None:
        """Il bordo di una zona: il nome in alto, l'interno vuoto.

        Il bordo ha il colore della zona e diventa rosso quando la zona è
        piena, così i colli di bottiglia si vedono da tutta la mappa.
        """
        zone = self._map.zones[name]
        full = (
            name not in (self._map.start.name, self._map.end.name)
            and zone.zone_type != "blocked"
            and len(ids) >= zone.max_drones
        )
        edge = self._color("red") | curses.A_BOLD if full else (
            self._color(self._zone_word(zone))
            | (curses.A_DIM if zone.zone_type == "blocked" else 0)
        )
        inner = box - 2
        self._put(screen, row, col, TL, edge)
        self._put(screen, row, col + 1, label, self._zone_attr(name))
        self._put(
            screen, row, col + 1 + len(label),
            HORIZ * (inner - len(label)) + TR, edge,
        )
        self._put(screen, row + 1, col, VERT + " " * inner + VERT, edge)
        self._put(screen, row + 2, col, BL + HORIZ * inner + BR, edge)

    def _draw_occupants(
        self,
        screen: curses.window,
        row: int,
        col: int,
        width: int,
        name: str,
        ids: list[int],
        movers: set[int],
    ) -> None:
        """Riga centrale di un riquadro: i droni, poi i posti liberi.

        Centrata nel riquadro. I droni appena arrivati sono gialli; quelli
        di una zona piena sono rossi. Se i numeri non ci stanno, viene
        mostrato il conteggio.
        """
        zone = self._map.zones[name]
        if name in (self._map.start.name, self._map.end.name):
            word = "left" if name == self._map.start.name else "in"
            text = f"{len(ids)} {word}"
            text = text if len(text) <= width else str(len(ids))
            attr = (
                curses.A_DIM if name == self._map.start.name
                else self._color("green") | curses.A_BOLD
            )
            self._put(screen, row, col + (width - len(text)) // 2, text, attr)
            return
        if zone.zone_type == "blocked":
            return
        cap = zone.max_drones
        full = len(ids) >= cap
        free = FREE * (cap - len(ids)) if cap <= SLOTS_MAX else ""
        text = " ".join(map(str, ids)) + (" " if ids and free else "") + free
        if len(text) > width:
            count = f"{len(ids)}/{cap}"
            attr = self._color("red") | curses.A_BOLD if full else (
                curses.A_BOLD if ids else curses.A_DIM
            )
            self._put(
                screen, row, col + (width - len(count)) // 2, count, attr
            )
            return
        col += (width - len(text)) // 2
        x = col
        for drone_id in ids:
            if drone_id in movers:
                attr = self._color("yellow") | curses.A_BOLD
            elif full:
                attr = self._color("red") | curses.A_BOLD
            else:
                attr = curses.A_BOLD
            self._put(screen, row, x, str(drone_id), attr)
            x += len(str(drone_id)) + 1
        self._put(screen, row, x if ids else col, free, curses.A_DIM)

    def _draw_panel(self, screen: curses.window, x: int, rows: int) -> None:
        """Totali della flotta, mosse del turno e zone occupate."""
        for row in range(HEADER_ROWS, rows - FOOTER_ROWS):
            self._put(screen, row, x - 1, "|", curses.A_DIM)
        counts = Counter(self._resting().values())
        start, end = self._map.start.name, self._map.end.name
        flying = sum(n for pos, n in counts.items() if "-" in pos)
        moving = len(self._movers()) if self.progress < 1 else 0
        lines: list[tuple[str, int]] = [
            ("FLEET", curses.A_BOLD),
            (f" waiting at start  {counts[start]}", 0),
            (f" moving now        {moving}", 0),
            (f" mid-transit       {flying}", 0),
            (f" delivered         {counts[end]}/{self._map.nb_drones}", 0),
            ("", 0),
            (f"MOVES IN TURN {self.turn}", curses.A_BOLD),
        ]
        yellow = self._color("yellow") | curses.A_BOLD
        lines += [(f" {m}", yellow) for m in self._moves()] or [(" none", 0)]
        lines += [("", 0), ("BUSY ZONES", curses.A_BOLD)]
        busy = sorted(
            (n for n in self._map.zones
             if counts[n] and n not in (start, end)),
            key=lambda n: -counts[n] / self._map.zones[n].max_drones,
        )
        for name in busy:
            cap = self._map.zones[name].max_drones
            full = counts[name] >= cap
            lines.append((
                f" {name[:PANEL_W - 14]:<{PANEL_W - 13}}"
                f"{counts[name]}/{cap}{' full' if full else ''}",
                self._color("red") | curses.A_BOLD if full else 0,
            ))
        if not busy:
            lines.append((" none", 0))
        room = rows - FOOTER_ROWS - HEADER_ROWS
        if len(lines) > room:
            hidden = len(lines) - room + 1
            lines = lines[:room - 1] + [(f" ... {hidden} more lines", 0)]
        for i, (text, attr) in enumerate(lines):
            self._put(screen, HEADER_ROWS + i, x, text[:PANEL_W - 1], attr)

    def _moves(self) -> list[str]:
        """Mosse leggibili del turno sullo schermo, con i nomi interi."""
        if self.turn == 0:
            return []
        before, after = self._frames[self.turn - 1], self._frames[self.turn]
        moves = []
        for drone_id in sorted(self._movers()):
            prev, dest = before[drone_id], after[drone_id]
            if "-" in dest:
                prev, dest = dest.split("-")
                text = f"{prev} {ARROW} {dest} (2 turns)"
            elif "-" in prev:
                text = f"lands in {dest}"
            else:
                text = f"{prev} {ARROW} {dest}"
            if len(text) > PANEL_W - 6:  # keep the destination readable
                text = f"{ARROW} {dest}"
            moves.append(f"D{drone_id:<3} {text}")
        return moves

    def _draw_footer(self, screen: curses.window, rows: int) -> None:
        """Legenda e tasti disponibili."""
        self._put(
            screen, rows - 2, 1,
            f"{TL}name{TR} zone with its drones  12 drone (yellow: moving)"
            f"  {FREE} free slot  red: full  "
            "* priority  ! restricted  x blocked  "
            "link: yellow = in use, dim = never used",
            curses.A_DIM,
        )
        self._put(
            screen, rows - 1, 1,
            "[space] play/pause  [<-/->] one turn  [+/-] speed  "
            "[p] panel  [m] maps  [r] restart  [q] quit",
            curses.A_BOLD,
        )

    # ------------------------------------------------------------ input

    def _pick(self, key: int) -> None:
        """Un tasto con la scelta mappa aperta: sposta, carica o chiudi."""
        names = list(self._maps)
        if key in (ord("m"), ord("q")):
            self._picking = False
        elif key == curses.KEY_UP:
            self._choice = (self._choice - 1) % len(names)
            self._error = ""
        elif key == curses.KEY_DOWN:
            self._choice = (self._choice + 1) % len(names)
            self._error = ""
        elif key in KEY_ENTER and self._loader is not None:
            path = self._maps[names[self._choice]]
            try:
                map_data, _, log = self._loader(path)
            except (RuntimeError, ValueError) as exc:  # ParserError too
                self._error = f"cannot load: {exc}"
                return
            self._show(map_data, log, path)
            self._picking = False

    def handle(self, key: int) -> bool:
        """Gestisce la pressione di un tasto; restituisce False per uscire."""
        if self._picking:
            self._pick(key)
            return True
        if key == ord("m") and self._maps:
            self._picking, self._error = True, ""
            names = list(self._maps)
            if self._current() in names:
                self._choice = names.index(self._current())
            return True
        # Not Esc: an arrow key is Esc + 2 bytes, and over a slow link
        # curses can read that Esc alone and quit mid-replay.
        if key == ord("q"):
            return False
        if key == ord(" "):
            if self._playing:
                self._target, self._playing = self._t, False
            else:
                if self._t >= self._last:
                    self._t = 0.0  # play again from the top
                self._target, self._playing = float(self._last), True
        elif key == curses.KEY_RIGHT:
            self._target = float(min(self._last, math.floor(self._t) + 1))
            self._playing = True
        elif key == curses.KEY_LEFT:
            self._target = float(max(0, math.ceil(self._t) - 1))
            self._playing = True
        elif key in (ord("+"), ord("=")):
            self._speed = max(0, self._speed - 1)
        elif key in (ord("-"), ord("_")):
            self._speed = min(len(DELAYS_MS) - 1, self._speed + 1)
        elif key == ord("p"):
            self._panel = not self._panel_shown(self._cols)
        elif key == ord("r"):
            self._t, self._playing = 0.0, True
            self._target = float(self._last)
        return True

    def _loop(self, screen: curses.window) -> None:
        """Ciclo degli eventi: ridisegna, legge un tasto, avanza l'orologio."""
        try:
            curses.curs_set(0)
        except curses.error:  # terminal cannot hide the cursor: keep it
            pass
        screen.timeout(30)
        self._init_colors()
        last = time.monotonic()
        while True:
            self.draw(screen)
            if not self.handle(screen.getch()):
                return
            now = time.monotonic()
            if self._playing:
                self.advance(now - last)
            last = now
