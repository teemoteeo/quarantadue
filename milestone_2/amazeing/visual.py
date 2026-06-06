#!/usr/bin/env python3
"""visual.py — curses renderer for aMAZEing.

Layout (inside curses window):

  ┌─ MENU (left, 14 cols) ─┬─ MAZE (centre) ─┬─ INFO (right, 18 cols) ─┐
  │  [R] Regen             │  actual maze     │  Algorithm: DFS          │
  │  [S] Setup             │                  │  Perfect:   YES          │
  │  [P] Path              │                  │  Size:  20 × 20          │
  │  [C] Color             │                  │  Seed:  —                │
  │  [Q] Quit              │                  │                          │
  └────────────────────────┴──────────────────┴──────────────────────────┘

Two background threads drive animations:
  - AnimThread: streams carve_steps / knock_steps to the grid
  - SolveThread: streams bidir-BFS frontier cells then final path

The main curses loop only handles input + triggers redraws via _dirty flag.
"""

import curses
import threading
import time
from typing import Any, Optional

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

# ── colour pair IDs ───────────────────────────────────────────────────────
_C_WALL    = 1   # maze walls
_C_ENTRY   = 2   # E cell
_C_EXIT    = 3   # X cell
_C_PAT42   = 4   # ██ pattern cells
_C_FA      = 5   # BFS frontier A (from entry)  — cyan
_C_FB      = 6   # BFS frontier B (from goal)   — magenta
_C_PATH    = 7   # final solution path          — yellow
_C_MENU_HL = 8   # highlighted menu item
_C_INFO    = 9   # info panel text

# one fixed colour pair per palette entry (IDs 10-15)
_C_PAL_BASE = 10  # _C_PAL_BASE + i  →  colour pair for _WALL_PALETTES[i]

# available wall colour schemes (pair id, fg, bg)
_WALL_PALETTES = [
    (curses.COLOR_GREEN,   curses.COLOR_BLACK),  # 0 green (default)
    (curses.COLOR_YELLOW,  curses.COLOR_BLACK),  # 1 yellow
    (curses.COLOR_RED,     curses.COLOR_BLACK),  # 2 red
    (curses.COLOR_BLUE,    curses.COLOR_BLACK),  # 3 blue
    (curses.COLOR_WHITE,   curses.COLOR_BLACK),  # 4 white
    (curses.COLOR_CYAN,    curses.COLOR_BLACK),  # 5 cyan
]
_PALETTE_NAMES = ["Green", "Yellow", "Red", "Blue", "White", "Cyan"]

# available 42-pattern colour schemes (same palette ids)
_PAT_PALETTES = _WALL_PALETTES
_PAT_NAMES    = _PALETTE_NAMES

MENU_ITEMS = [
    ("R", "REGEN"),
    ("S", "SETUP"),
    ("P", "PATH"),
    ("C", "COLOR"),
    ("Q", "QUIT"),
]
# Each button renders as 5 lines: 2 blank / label / 2 blank
_BTN_H    = 5
# Total block height = n_items * btn_h + (n_items-1) spacer lines
_MENU_BLOCK_H = len(MENU_ITEMS) * _BTN_H + (len(MENU_ITEMS) - 1)
MENU_W = 44  # left sidebar width
INFO_W = 26  # right info panel width


# ── animation delays ─────────────────────────────────────────────────────
_CARVE_DELAY = 0.00003125
_LAYER_DELAY = 0.02   # seconds per BFS wave layer (one redraw per layer)

# ── path connector glyphs ─────────────────────────────────────────────────
_DIRS_TO_GLYPH = {
    (0, -1, 1,  0): "╭", (-1, 0, 0,  1): "╭",
    (0, -1, -1, 0): "╮", (1,  0, 0,  1): "╮",
    (0,  1, 1,  0): "╰", (-1, 0, 0, -1): "╰",
    (0,  1, -1, 0): "╯", (1,  0, 0, -1): "╯",
}

# corner glyphs for BFS turns: (prev_dx, prev_dy, dx, dy) → char
_BFS_TURN: dict[tuple[int, int, int, int], str] = {
    (1,  0,  0,  1): "┐",  # right→down
    (1,  0,  0, -1): "┘",  # right→up
    (-1, 0,  0,  1): "┌",  # left→down
    (-1, 0,  0, -1): "└",  # left→up
    (0,  1,  1,  0): "└",  # down→right
    (0,  1, -1,  0): "┘",  # down→left
    (0, -1,  1,  0): "┌",  # up→right
    (0, -1, -1,  0): "┐",  # up→left
}


class Visualinho:
    """curses-based maze renderer with threaded animations."""

    def __init__(self, generator: Any) -> None:
        self.generator  = generator
        self.grid       = generator.grid
        self.w: int     = generator.width
        self.h: int     = generator.height
        self.pattern42  = generator._pattern_cells

        # overlay state (written by anim threads, read by draw thread)
        self._lock              = threading.Lock()
        self._frontier_a: dict[tuple[int, int], str] = {}
        self._frontier_b: dict[tuple[int, int], str] = {}
        self._visited_a: dict[tuple[int, int], str]  = {}
        self._visited_b: dict[tuple[int, int], str]  = {}
        self._path: list[tuple[int, int]]       = []
        self._full_path: list[tuple[int, int]]  = []   # full path for glyph direction
        self._show_path: bool                   = False
        self._dirty: bool                       = True

        # settings
        self._wall_palette: int = 3   # index into _WALL_PALETTES
        self._pat_palette:  int = 2   # index into _PAT_PALETTES
        self._menu_sel:     int = 0   # selected menu item index

        # timing (0.0 = idle / not yet measured)
        self._maze_t0:   float = 0.0   # perf_counter at regen start; 0 when idle
        self._maze_time: float = 0.0   # frozen total after carve anim ends
        self._path_t0:   float = 0.0   # perf_counter at solve start; 0 when idle
        self._path_time: float = 0.0   # frozen total after path anim ends

        # animation thread handles
        self._anim_thread:  Optional[threading.Thread] = None
        self._solve_thread: Optional[threading.Thread] = None
        self._anim_stop    = threading.Event()
        self._solve_stop   = threading.Event()
        self._final_grid: list[list[int]] = [
            list(row) for row in self.grid
        ]

        # curses screen (set by run())
        self._scr: Any = None
        self._maze_win: Any = None
        self._menu_win: Any = None
        self._info_win: Any = None

    # ── colour init ───────────────────────────────────────────────────────
    def _init_colours(self) -> None:
        curses.start_color()
        curses.use_default_colors()  # -1 = terminal default (transparent bg)

        wp = _WALL_PALETTES[self._wall_palette]
        pp = _PAT_PALETTES[self._pat_palette]

        curses.init_pair(_C_WALL,    wp[0],               -1)
        curses.init_pair(_C_ENTRY,   curses.COLOR_WHITE,  -1)
        curses.init_pair(_C_EXIT,    curses.COLOR_WHITE,  -1)
        curses.init_pair(_C_PAT42,   pp[0],               -1)
        curses.init_pair(_C_FA,      curses.COLOR_CYAN,   -1)
        curses.init_pair(_C_FB,      curses.COLOR_MAGENTA,-1)
        curses.init_pair(_C_PATH,    curses.COLOR_YELLOW, -1)
        curses.init_pair(_C_MENU_HL, curses.COLOR_BLACK,  curses.COLOR_GREEN)
        curses.init_pair(_C_INFO,    curses.COLOR_WHITE,  -1)
        for i, (fg, bg) in enumerate(_WALL_PALETTES):
            curses.init_pair(_C_PAL_BASE + i, fg, -1)

    def _refresh_wall_colour(self) -> None:
        wp = _WALL_PALETTES[self._wall_palette]
        curses.init_pair(_C_WALL, wp[0], -1)

    def _refresh_pat_colour(self) -> None:
        pp = _PAT_PALETTES[self._pat_palette]
        curses.init_pair(_C_PAT42, pp[0], -1)

    # ── window layout ─────────────────────────────────────────────────────
    def _build_windows(self) -> None:
        """Create/resize sub-windows for menu, maze, info."""
        max_y, max_x = self._scr.getmaxyx()
        # wipe stdscr so a shrunken maze does not leave ghost cells from
        # the previous (larger) maze in the now-uncovered region
        self._scr.clear()
        self._scr.noutrefresh()

        # panel widths grow with the terminal so content breathes on wide screens
        menu_w = max(MENU_W, min(70, max_x // 4))
        info_w = max(INFO_W, min(45, max_x // 7))

        maze_cols = self.w * 4 + 1
        maze_rows = self.h * 2 + 1
        maze_cols = min(maze_cols, max(1, max_x - menu_w - info_w))
        maze_rows = min(maze_rows, max_y)

        # maze centred in the middle band (between menu and info)
        middle_band_w = max_x - menu_w - info_w
        maze_top  = max(0, (max_y - maze_rows) // 2)
        maze_left = menu_w + max(0, (middle_band_w - maze_cols) // 2)

        # menu window spans from col 0 to maze_left (full left margin)
        self._menu_win = curses.newwin(max_y, maze_left, 0, 0)
        self._maze_win = curses.newwin(
            maze_rows, maze_cols, maze_top, maze_left
        )
        info_left = maze_left + maze_cols
        info_cols = max(1, max_x - info_left)
        self._info_win = curses.newwin(
            max_y, min(info_w, info_cols), 0, info_left
        )
        # store screen dims for menu drawing
        self._scr_y = max_y
        self._scr_x = max_x

    # ── BFS direction glyph ──────────────────────────────────────────────
    @staticmethod
    def _bfs_glyph(
        cell: tuple[int, int],
        parent: Optional[tuple[int, int]],
        child: Optional[tuple[int, int]] = None,
    ) -> str:
        if parent is None:
            return "·"
        dx = cell[0] - parent[0]
        dy = cell[1] - parent[1]
        if child is None:
            return "─" if dx != 0 else "│"
        cdx = child[0] - cell[0]
        cdy = child[1] - cell[1]
        if cdx == dx and cdy == dy:
            return "─" if dx != 0 else "│"
        return _BFS_TURN.get((dx, dy, cdx, cdy), "·")

    # ── path connector glyph ─────────────────────────────────────────────
    def _path_glyph(self, path: list[tuple[int, int]], idx: int) -> str:
        """Return the display glyph for path[idx], using the given snapshot."""
        if idx == len(path) - 1:
            return "♘"
        cx, cy = path[idx]
        nx, ny = path[idx + 1]
        if idx == 0:
            to_dx, to_dy = nx - cx, ny - cy
            if to_dy == 0:
                return "─"
            if to_dx == 0:
                return "│"
            return "•"
        px, py = path[idx - 1]
        key = (cx - px, cy - py, nx - cx, ny - cy)
        if key in _DIRS_TO_GLYPH:
            return _DIRS_TO_GLYPH[key]
        from_dx = cx - px
        from_dy = cy - py
        to_dx   = nx - cx
        to_dy   = ny - cy
        if from_dy == 0 and to_dy == 0:
            return "─"
        if from_dx == 0 and to_dx == 0:
            return "│"
        return "•"

    # ── maze drawing ──────────────────────────────────────────────────────
    def _draw_maze(self) -> None:
        win = self._maze_win
        win.bkgd(' ', curses.A_NORMAL)
        win.erase()
        wattr  = curses.color_pair(_C_WALL)
        eattr  = curses.color_pair(_C_ENTRY)  | curses.A_BOLD
        xattr  = curses.color_pair(_C_EXIT)   | curses.A_BOLD
        pattr  = curses.color_pair(_C_PAT42)  | curses.A_BOLD
        faattr = curses.color_pair(_C_FA)
        fbattr = curses.color_pair(_C_FB)
        ptattr = curses.color_pair(_C_PATH)   | curses.A_BOLD
        blank  = curses.A_NORMAL  # transparent background for empty cells

        entry  = self.generator.entry
        exit_  = self.generator.exit
        max_r, max_c = win.getmaxyx()

        with self._lock:
            fa   = self._frontier_a
            fb   = self._frontier_b
            va   = self._visited_a
            vb   = self._visited_b
            pth  = self._path          # already a fresh slice set atomically
            fpth = self._full_path     # full path for direction lookup
            spth = self._show_path

        # Build index map from the partial snapshot.
        # Use full_path indices so _path_glyph always has valid prev/next.
        fp_index: dict[tuple[int, int], int] = {
            cell: i for i, cell in enumerate(fpth)
        }
        path_set: dict[tuple[int, int], int] = {
            cell: fp_index[cell] for cell in pth if cell in fp_index
        }

        def _addch(row: int, col: int, ch: str, attr: int) -> None:
            if 0 <= row < max_r and 0 <= col < max_c:
                try:
                    win.addstr(row, col, ch, attr)
                except curses.error:
                    pass

        def _addstr(row: int, col: int, s: str, attr: int) -> None:
            for i, ch in enumerate(s):
                _addch(row, col + i, ch, attr)

        # top border
        _addch(0, 0, "╔", wattr)
        for x in range(self.w):
            nwall = "═══" if self.grid[0][x] & (1 << NORTH) else "   "
            _addstr(0, 1 + x * 4, nwall, wattr)
            if x < self.w - 1:
                _addch(0, 1 + x * 4 + 3, "╦", wattr)
        _addch(0, 1 + (self.w - 1) * 4 + 3, "╗", wattr)

        for y in range(self.h):
            row = 1 + y * 2
            # cell row
            _addch(row, 0, "║", wattr)
            for x in range(self.w):
                cell  = self.grid[y][x]
                col   = 1 + x * 4
                wwall = "║" if cell & (1 << WEST) else " "
                # west wall of current cell (already drawn by previous
                # cell's east, but first col needs it)
                if x > 0:
                    ewall = "║" if self.grid[y][x - 1] & (1 << EAST) else " "
                    _addch(row, col - 1, ewall, wattr)

                # cell content
                if (x, y) == entry:
                    _addstr(row, col, " E ", eattr)
                elif (x, y) == exit_:
                    _addstr(row, col, " X ", xattr)
                elif (x, y) in self.pattern42:
                    _addstr(row, col, " █ ", pattr)
                elif spth and (x, y) in path_set:
                    glyph = self._path_glyph(fpth, path_set[(x, y)])
                    _addstr(row, col, f" {glyph} ", ptattr)
                elif (x, y) in fa:
                    _addstr(row, col, " ● ", faattr | curses.A_BOLD)
                elif (x, y) in fb:
                    _addstr(row, col, " ● ", fbattr | curses.A_BOLD)
                elif (x, y) in va:
                    _addstr(row, col,
                            f" {va[(x, y)]} ", faattr | curses.A_BOLD)
                elif (x, y) in vb:
                    _addstr(row, col,
                            f" {vb[(x, y)]} ", fbattr | curses.A_BOLD)
                else:
                    _addstr(row, col, "   ", blank)

            # right border
            _addch(row, 1 + self.w * 4 - 1, "║", wattr)

            # horizontal divider row
            if y < self.h - 1:
                drow = row + 1
                _addch(drow, 0, "╠", wattr)
                for x in range(self.w):
                    swall = "═══" if self.grid[y][x] & (
                        1 << SOUTH
                    ) else "   "
                    _addstr(drow, 1 + x * 4, swall,
                            wattr if self.grid[y][x] & (1 << SOUTH)
                            else blank)
                    sep = "╬" if x < self.w - 1 else "╣"
                    _addch(drow, 1 + x * 4 + 3, sep, wattr)

        # bottom border
        brow = 1 + self.h * 2 - 1
        _addch(brow, 0, "╚", wattr)
        for x in range(self.w):
            swall = "═══" if self.grid[self.h - 1][x] & (
                1 << SOUTH
            ) else "   "
            _addstr(brow, 1 + x * 4, swall, wattr)
            sep = "╩" if x < self.w - 1 else "╝"
            _addch(brow, 1 + x * 4 + 3, sep, wattr)

        win.noutrefresh()

    # ── menu drawing ──────────────────────────────────────────────────────
    def _draw_menu(self) -> None:
        win  = self._menu_win
        win.bkgd(' ', curses.A_NORMAL)   # force transparent background
        win.erase()
        max_y, max_x = win.getmaxyx()

        hl   = curses.color_pair(_C_MENU_HL) | curses.A_BOLD
        norm = curses.A_BOLD

        # double-wide label: insert a space after every character
        def _wide(s: str) -> str:
            return " ".join(s)

        # uniform button width = widest wide-label + 6 padding chars
        btn_w     = max(len(_wide(f"[{k}] {l}")) for k, l in MENU_ITEMS) + 6
        btn_w     = min(btn_w, max_x)   # clamp to window width
        block_h   = _MENU_BLOCK_H
        start_row = max(0, (max_y - block_h) // 2)
        col       = max(0, (max_x - btn_w) // 2)

        for i, (key, label) in enumerate(MENU_ITEMS):
            btn_top = start_row + i * (_BTN_H + 1)
            attr    = hl if i == self._menu_sel else norm
            text    = _wide(f"[{key}] {label}").center(btn_w)
            for drow in range(_BTN_H):
                row = btn_top + drow
                if row >= max_y:
                    break
                line = text if drow == 2 else " " * btn_w
                try:
                    win.addstr(row, col, line, attr)
                except curses.error:
                    pass

        win.noutrefresh()

    # ── info panel drawing ────────────────────────────────────────────────
    def _draw_info(self) -> None:
        win = self._info_win
        win.bkgd(' ', curses.A_NORMAL)
        win.erase()
        attr     = curses.color_pair(_C_INFO) | curses.A_BOLD
        wall_attr = curses.color_pair(_C_PAL_BASE + self._wall_palette) | curses.A_BOLD
        pat_attr  = curses.color_pair(_C_PAL_BASE + self._pat_palette)  | curses.A_BOLD
        g        = self.generator

        seed_val = g.seed if hasattr(g, 'seed') and g.seed else "-"

        # live or frozen timing strings
        now = time.perf_counter()
        if self._maze_t0 > 0:
            gen_str = f"gen {now - self._maze_t0:.1f}s..."
        elif self._maze_time > 0:
            gen_str = f"gen {self._maze_time:.2f}s"
        else:
            gen_str = ""
        if self._path_t0 > 0:
            path_str = f"path {now - self._path_t0:.1f}s..."
        elif self._path_time > 0:
            path_str = f"path {self._path_time:.2f}s"
        else:
            path_str = ""

        # (text, attribute) pairs — None attr means use default `attr`
        entries: list[tuple[str, Any]] = [
            (g.algorithm,                              None),
            ("PERFECT" if g.perfect else "IMPERFECT", None),
            (f"{g.width}x{g.height}",                 None),
            (f"seed:{seed_val}",                       None),
            ("",                                       None),
            (gen_str,                                  None),
            (path_str,                                 None),
        ]
        # colour rows rendered separately so label and name use different attrs
        wall_label = "Maze: "
        wall_name  = _PALETTE_NAMES[self._wall_palette]
        pat_label  = "42:   "
        pat_name   = _PAT_NAMES[self._pat_palette]

        max_y, max_x = win.getmaxyx()
        # +2 for the two colour rows after the blank
        start = max(0, (max_y - len(entries) - 2) // 2)

        for i, (line, a) in enumerate(entries):
            row = start + i
            if row >= max_y:
                break
            col = max(0, (max_x - len(line)) // 2)
            try:
                win.addstr(row, col, line[:max_x], a if a is not None else attr)
            except curses.error:
                pass

        # draw the two colour lines: plain label + coloured name
        for label, name, cattr in [
            (wall_label, wall_name, wall_attr),
            (pat_label,  pat_name,  pat_attr),
        ]:
            row = start + len(entries)
            start += 1          # advance for next line
            if row >= max_y:
                break
            full  = label + name
            col   = max(0, (max_x - len(full)) // 2)
            try:
                win.addstr(row, col, label, attr)
                win.addstr(row, col + len(label), name, cattr)
            except curses.error:
                pass

        win.noutrefresh()

    # ── full redraw ───────────────────────────────────────────────────────
    def redraw(self) -> None:
        """Redraw all panels and flush to screen."""
        self._draw_menu()
        self._draw_maze()
        self._draw_info()
        curses.doupdate()
        self._dirty = False

    # ── animation threads ─────────────────────────────────────────────────
    def start_carve_animation(
        self,
        carve_steps: list[Any],
        knock_steps: list[Any],
    ) -> None:
        """Start background thread that replays carving + knocking."""
        self._stop_anim()
        # snapshot the fully-carved grid BEFORE we reset it to all-walls
        self._final_grid = [
            list(row) for row in self.grid
        ]
        # reset grid to all-walls for replay
        for y in range(self.h):
            for x in range(self.w):
                self.grid[y][x] = 15
        # restore pattern cells
        for cx, cy in self.pattern42:
            self.grid[cy][cx] = 15

        self._anim_stop.clear()

        # capture grid, dims and snapshot NOW so the thread always restores
        # the maze it was started for — even if a new regen swaps self.grid,
        # self.h/w, or self._final_grid before this thread finishes
        _grid  = self.grid
        _h     = self.h
        _w     = self.w
        _final = self._final_grid
        _t0    = self._maze_t0

        def _run() -> None:
            for step in carve_steps + knock_steps:
                if self._anim_stop.is_set():
                    break
                cy, cx, wh, ny, nx, wo = step
                with self._lock:
                    _grid[cy][cx] &= ~(1 << wh)
                    _grid[ny][nx] &= ~(1 << wo)
                self._dirty = True
                if self._anim_stop.wait(_CARVE_DELAY):
                    break
            # after animation: restore final grid into the captured grid object
            with self._lock:
                for y in range(_h):
                    for x in range(_w):
                        _grid[y][x] = _final[y][x]
            self._maze_time = time.perf_counter() - _t0
            self._maze_t0   = 0.0
            self._dirty = True

        self._anim_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._anim_thread.start()

    def start_bidir_animation(
        self,
        path: list[tuple[int, int]],
        layers: list[
            tuple[
                str,
                list[
                    tuple[
                        tuple[int, int], Optional[tuple[int, int]]
                    ]
                ],
            ]
        ],
    ) -> None:
        """Animate bidirectional BFS exploration then reveal optimal path.

        Animation is layer-batched: each BFS wave (one full frontier layer)
        is rendered in a single frame. Cost is O(num_layers) frames instead
        of O(num_cells) — eliminates lag on open mazes.
        """
        self._stop_solve()
        with self._lock:
            self._frontier_a = {}
            self._frontier_b = {}
            self._visited_a  = {}
            self._visited_b  = {}
            self._path       = []
            self._show_path  = False
            self._full_path  = list(path)
        self._dirty = True

        _path_t0 = self._path_t0

        def _run() -> None:
            # first child each BFS cell expanded to (for glyph direction)
            child_map: dict[
                tuple[str, tuple[int, int]], tuple[int, int]
            ] = {}
            for side, cells in layers:
                for cell, parent in cells:
                    if (
                        parent is not None
                        and (side, parent) not in child_map
                    ):
                        child_map[(side, parent)] = cell

            for side, cells in layers:
                if self._solve_stop.is_set():
                    break
                with self._lock:
                    # promote previous layer of THIS side to visited,
                    # then build fresh frontier from the new layer cells
                    if side == 'a':
                        self._visited_a.update(self._frontier_a)
                        self._frontier_a = {}
                        for cell, parent in cells:
                            child = child_map.get((side, cell))
                            self._frontier_a[cell] = self._bfs_glyph(
                                cell, parent, child
                            )
                    else:
                        self._visited_b.update(self._frontier_b)
                        self._frontier_b = {}
                        for cell, parent in cells:
                            child = child_map.get((side, cell))
                            self._frontier_b[cell] = self._bfs_glyph(
                                cell, parent, child
                            )
                self._dirty = True
                # interruptible delay
                if self._solve_stop.wait(_LAYER_DELAY):
                    break
            # always finalise: clear overlay, reveal optimal path
            with self._lock:
                self._frontier_a = {}
                self._frontier_b = {}
                self._visited_a  = {}
                self._visited_b  = {}
                self._path       = self._full_path
                self._show_path  = bool(self._full_path)
            if _path_t0 > 0:
                self._path_time = time.perf_counter() - _path_t0
                self._path_t0   = 0.0
            self._dirty = True

        self._solve_stop.clear()
        self._solve_thread = threading.Thread(
            target=_run, daemon=True
        )
        self._solve_thread.start()

    def _stop_anim(self) -> None:
        self._anim_stop.set()
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_thread.join(timeout=1.0)
        self._anim_stop.clear()

    def _stop_solve(self) -> None:
        self._solve_stop.set()
        if self._solve_thread and self._solve_thread.is_alive():
            self._solve_thread.join(timeout=1.0)
        self._solve_stop.clear()

    def stop_all(self) -> None:
        """Stop all running animation threads."""
        self._anim_stop.set()
        self._solve_stop.set()
        for t in (self._anim_thread, self._solve_thread):
            if t and t.is_alive():
                t.join(timeout=1.0)

    # ── setup inline (draws into _menu_win) ────────────────────────────
    def show_setup(self, config: Any) -> bool:
        """Render setup form inside _menu_win. Returns True if applied."""
        win = self._menu_win
        scr = self._scr
        scr.nodelay(False)
        curses.curs_set(1)
        _ = scr.getmaxyx()  # unused but keeps linter happy

        fields = [
            ("Algorithm", "enum", ["DFS", "PRIM", "KRUSKAL"],
             config.algorithm),
            ("Perfect",   "bool", None, config.perfect),
            ("Width",     "int",  None, str(config.width)),
            ("Height",    "int",  None, str(config.height)),
            ("Entry X",   "int",  None, str(config.entry[0])),
            ("Entry Y",   "int",  None, str(config.entry[1])),
            ("Exit X",    "int",  None, str(config.exit[0])),
            ("Exit Y",    "int",  None, str(config.exit[1])),
            ("Seed",      "int",  None,
             str(config.seed) if config.seed is not None else ""),
        ]
        values: list[Any] = [f[3] for f in fields]
        sel = 0
        err = ""
        hl      = curses.color_pair(_C_MENU_HL) | curses.A_BOLD
        norm    = curses.A_BOLD
        errattr = curses.color_pair(_C_PATH) | curses.A_BOLD

        def _render() -> None:
            win.bkgd(' ', curses.A_NORMAL)
            win.erase()
            max_y, max_x = win.getmaxyx()
            title  = "[ SETUP ]"
            hint   = "ENTER apply  ESC cancel"
            n_rows = len(fields)
            # header(1) + blank(1) + hint(1) + blank(1) + fields with 1-row gaps
            block_h = 4 + n_rows * 2 - 1
            start_row = max(0, (max_y - block_h) // 2)
            try:
                win.addstr(start_row,
                           max(0, (max_x - len(title)) // 2),
                           title, hl)
                win.addstr(start_row + 2,
                           max(0, (max_x - len(hint)) // 2),
                           hint, norm)
            except curses.error:
                pass
            if err:
                try:
                    win.addstr(start_row + 3,
                               max(0, (max_x - len(err)) // 2),
                               err[:max_x - 2], errattr)
                except curses.error:
                    pass
            for i, (name, kind, _, __) in enumerate(fields):
                row = start_row + 4 + i * 2
                if row >= max_y:
                    break
                attr = hl if i == sel else norm
                val  = values[i]
                disp = ("YES" if val else "NO") if kind == "bool" else str(val)
                line = f"{name:<9} {disp}"
                col  = max(0, (max_x - len(line)) // 2)
                try:
                    win.addstr(row, col, line, attr)
                except curses.error:
                    pass
            win.noutrefresh()
            curses.doupdate()

        while True:
            _render()
            key = scr.getch()
            if key in (curses.KEY_UP, ord('k')):
                sel = (sel - 1) % len(fields)
                err = ""
            elif key in (curses.KEY_DOWN, ord('j')):
                sel = (sel + 1) % len(fields)
                err = ""
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, ord(' ')):
                kind = fields[sel][1]
                opts = fields[sel][2]
                if kind == "bool":
                    values[sel] = not values[sel]
                elif kind == "enum" and opts:
                    idx   = opts.index(values[sel])
                    delta = -1 if key == curses.KEY_LEFT else 1
                    values[sel] = opts[(idx + delta) % len(opts)]
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if fields[sel][1] == "int":
                    values[sel] = str(values[sel])[:-1]
            elif 48 <= key <= 57:
                if fields[sel][1] == "int":
                    values[sel] = str(values[sel]) + chr(key)
            elif key == 27:
                curses.curs_set(0)
                scr.nodelay(True)
                return False
            elif key in (curses.KEY_ENTER, 10, 13):
                try:
                    new_w  = int(values[2]) if values[2] else config.width
                    new_h  = int(values[3]) if values[3] else config.height
                    new_ex = int(values[4]) if values[4] else 0
                    new_ey = int(values[5]) if values[5] else 0
                    new_ux = int(values[6]) if values[6] else 0
                    new_uy = int(values[7]) if values[7] else 0
                    s      = str(values[8]).strip()
                    new_seed: Optional[int] = int(s) if s else None
                except ValueError:
                    err = "Invalid number"
                    continue
                if new_w <= 0 or new_h <= 0:
                    err = "Width/Height > 0"
                    continue
                if not (0 <= new_ex < new_w and 0 <= new_ey < new_h):
                    err = "Entry out of bounds"
                    continue
                if not (0 <= new_ux < new_w and 0 <= new_uy < new_h):
                    err = "Exit out of bounds"
                    continue
                if (new_ex, new_ey) == (new_ux, new_uy):
                    err = "Entry == Exit"
                    continue
                # check entry/exit don't land on the 42 pattern cells
                from generator import (
                    _PATTERN_4, _PATTERN_2,
                    _PATTERN_W, _PATTERN_H,
                    _PATTERN_MIN_W, _PATTERN_MIN_H,
                    _DIGIT_W, _PATTERN_GAP,
                )
                if new_w >= _PATTERN_MIN_W and new_h >= _PATTERN_MIN_H:
                    _ax  = (new_w - _PATTERN_W) // 2
                    _ay  = (new_h - _PATTERN_H) // 2
                    _off = _DIGIT_W + _PATTERN_GAP
                    _pat = (
                        {(_ax + dx, _ay + dy) for dx, dy in _PATTERN_4}
                        | {(_ax + _off + dx, _ay + dy) for dx, dy in _PATTERN_2}
                    )
                    if (new_ex, new_ey) in _pat:
                        err = "Entry inside 42 pattern"
                        continue
                    if (new_ux, new_uy) in _pat:
                        err = "Exit inside 42 pattern"
                        continue
                config.algorithm = values[0]
                config.perfect   = values[1]
                config.width     = new_w
                config.height    = new_h
                config.entry     = (new_ex, new_ey)
                config.exit      = (new_ux, new_uy)
                config.seed      = new_seed
                curses.curs_set(0)
                scr.nodelay(True)
                return True

    # ── color picker (draws into _menu_win like show_setup) ───────────────
    def show_color_picker(self) -> None:
        """Render colour picker inside _menu_win.
        Changes are previewed live; ENTER applies, ESC reverts."""
        win = self._menu_win
        scr = self._scr
        scr.nodelay(False)

        # save originals so ESC can revert
        orig_wall = self._wall_palette
        orig_pat  = self._pat_palette

        sections = [
            ("Wall colour",   "wall"),
            ("42 Pattern colour", "pat"),
        ]
        sec_sel = 0

        hl      = curses.color_pair(_C_MENU_HL) | curses.A_BOLD
        norm    = curses.A_BOLD

        def _preview() -> None:
            """Apply current selections to colour pairs and redraw."""
            self._refresh_wall_colour()
            self._refresh_pat_colour()
            self._draw_maze()
            self._draw_info()

        def _render() -> None:
            win.bkgd(' ', curses.A_NORMAL)
            win.erase()
            max_y, max_x = win.getmaxyx()
            title  = "[ COLOR ]"
            hint1  = "ENTER apply   ESC cancel"
            hint2  = "up/dn section   lt/rt colour"
            n_col  = len(_PALETTE_NAMES)
            # title(1) + blank(1) + hint1(1) + hint2(1) + blank(1)
            # + per section: label(1) + blank(1) + n colours with 1-row gaps
            sec_h   = 2 + n_col * 2 - 1
            block_h = 5 + len(sections) * sec_h
            start   = max(0, (max_y - block_h) // 2)
            try:
                win.addstr(start,
                           max(0, (max_x - len(title)) // 2),
                           title, hl)
                win.addstr(start + 2,
                           max(0, (max_x - len(hint1)) // 2),
                           hint1, norm)
                win.addstr(start + 3,
                           max(0, (max_x - len(hint2)) // 2),
                           hint2, norm)
            except curses.error:
                pass
            for i, (label, skey) in enumerate(sections):
                base  = start + 5 + i * sec_h + (1 if i > 0 else 0)
                cur_p = (
                    self._wall_palette if skey == "wall"
                    else self._pat_palette
                )
                a = hl if i == sec_sel else norm
                try:
                    win.addstr(base,
                               max(0, (max_x - len(label)) // 2),
                               label, a)
                    for j, name in enumerate(_PALETTE_NAMES):
                        pa   = hl if j == cur_p else norm
                        line = f"{j + 1}.  {name}"
                        col  = max(0, (max_x - len(line)) // 2)
                        row  = base + 2 + j * 2
                        if row < max_y:
                            win.addstr(row, col, line, pa)
                except curses.error:
                    pass
            win.noutrefresh()
            curses.doupdate()

        while True:
            _render()
            key = scr.getch()
            if key in (curses.KEY_ENTER, 10, 13):   # ENTER — keep changes
                break
            elif key == 27:                          # ESC — revert
                self._wall_palette = orig_wall
                self._pat_palette  = orig_pat
                self._refresh_wall_colour()
                self._refresh_pat_colour()
                break
            elif key in (curses.KEY_UP, ord('k')):
                sec_sel = (sec_sel - 1) % len(sections)
            elif key in (curses.KEY_DOWN, ord('j')):
                sec_sel = (sec_sel + 1) % len(sections)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                delta = -1 if key == curses.KEY_LEFT else 1
                if sections[sec_sel][1] == "wall":
                    self._wall_palette = (
                        self._wall_palette + delta
                    ) % len(_WALL_PALETTES)
                else:
                    self._pat_palette = (
                        self._pat_palette + delta
                    ) % len(_PAT_PALETTES)
                _preview()
            elif ord('1') <= key <= ord(str(len(_PALETTE_NAMES))):
                idx = key - ord('1')
                if sections[sec_sel][1] == "wall":
                    self._wall_palette = idx
                else:
                    self._pat_palette = idx
                _preview()

        self._dirty = True
        scr.nodelay(True)

    # ── main curses event loop ──────────────────────────────────────────────
    def run(self, config: Any) -> None:
        """Entry point: wrap everything in curses.wrapper."""
        curses.wrapper(self._main, config)

    def _regen(self, config: Any) -> None:
        """Rebuild maze from config, update internal refs, start anim."""
        from generator import MazeGenerator  # avoid circular at module level
        # stop both threads BEFORE swapping the grid reference — the anim
        # thread's cleanup writes self._final_grid back into self.grid, so if
        # we swap first it overwrites the new maze's grid with old maze data
        self._stop_solve()
        self._stop_anim()
        self._maze_t0   = time.perf_counter()
        self._maze_time = 0.0
        self._path_t0   = 0.0
        self._path_time = 0.0
        maze = MazeGenerator(config)
        self.generator  = maze
        self.grid       = maze.grid
        self.w          = maze.width
        self.h          = maze.height
        self.pattern42  = maze._pattern_cells
        with self._lock:
            self._frontier_a = {}
            self._frontier_b = {}
            self._visited_a  = {}
            self._visited_b  = {}
            self._path       = []
            self._full_path  = []
            self._show_path  = False
        self._build_windows()
        self.start_carve_animation(
            maze.carve_steps, maze.knock_steps
        )
        maze.write_output(config.output_file)

    def _main(self, stdscr: Any, config: Any) -> None:
        self._scr = stdscr
        curses.set_escdelay(25)  # kill the default ~1 s ESC wait
        curses.curs_set(0)
        stdscr.nodelay(True)   # non-blocking getch
        stdscr.keypad(True)
        self._init_colours()
        self._build_windows()

        # initial generation + animation
        self._regen(config)

        FRAME_MS = 33   # ~30 fps redraw cap

        while True:
            # ─ handle input ──────────────────────────────────────────────
            key = stdscr.getch()

            if key == curses.KEY_RESIZE:
                self._build_windows()
                self._dirty = True

            elif key == ord(' '):
                # skip active animation — flush to final state immediately
                anim_running = (
                    self._anim_thread and self._anim_thread.is_alive()
                )
                solve_running = (
                    self._solve_thread and self._solve_thread.is_alive()
                )
                if anim_running or solve_running:
                    if anim_running:
                        self._anim_stop.set()
                    if solve_running:
                        self._solve_stop.set()
                    if anim_running and self._anim_thread:
                        self._anim_thread.join(timeout=0.5)
                    if solve_running and self._solve_thread:
                        self._solve_thread.join(timeout=0.5)
                    # snap to fully-completed final state
                    with self._lock:
                        if anim_running:
                            # carve skip: restore from the saved final snapshot
                            for y in range(self.h):
                                for x in range(self.w):
                                    self.grid[y][x] = (
                                        self._final_grid[y][x]
                                    )
                        if solve_running:
                            # solve skip: show the complete solution path
                            self._path      = self._full_path
                            self._show_path = bool(self._full_path)
                        self._frontier_a = {}
                        self._frontier_b = {}
                        self._visited_a  = {}
                        self._visited_b  = {}
                    self._anim_stop.clear()
                    self._solve_stop.clear()
                    self._dirty = True
                else:
                    self._dispatch(config)

            elif key in (curses.KEY_UP, ord('k')):
                self._menu_sel = (
                    self._menu_sel - 1
                ) % len(MENU_ITEMS)
                self._dirty = True

            elif key in (curses.KEY_DOWN, ord('j')):
                self._menu_sel = (
                    self._menu_sel + 1
                ) % len(MENU_ITEMS)
                self._dirty = True

            elif key in (curses.KEY_ENTER, 10, 13):
                self._dispatch(config)

            # direct hotkeys
            elif key == ord('r') or key == ord('R'):
                self._menu_sel = 0
                self._regen(config)
                self._dirty = True

            elif key == ord('s') or key == ord('S'):
                self._menu_sel = 1
                changed = self.show_setup(config)
                if changed:
                    self._regen(config)
                self._dirty = True

            elif key == ord('p') or key == ord('P'):
                self._menu_sel = 2
                self._do_solve()

            elif key == ord('c') or key == ord('C'):
                self._menu_sel = 3
                self.show_color_picker()
                self._dirty = True

            elif key in (ord('q'), ord('Q'), 27):
                self.stop_all()
                break

            # ─ redraw if needed ──────────────────────────────────────────
            # keep timer ticking every frame while a countdown is running
            if self._maze_t0 > 0 or self._path_t0 > 0:
                self._dirty = True
            if self._dirty:
                try:
                    self.redraw()
                except curses.error:
                    pass

            curses.napms(FRAME_MS)

    def _dispatch(self, config: Any) -> None:
        """Execute the currently selected menu item."""
        item = MENU_ITEMS[self._menu_sel][0]
        if item == 'R':
            self._regen(config)
        elif item == 'S':
            changed = self.show_setup(config)
            if changed:
                self._regen(config)
        elif item == 'P':
            self._do_solve()
        elif item == 'C':
            self.show_color_picker()
        elif item == 'Q':
            self.stop_all()
            raise SystemExit(0)
        self._dirty = True

    def _do_solve(self) -> None:
        """Run bidirectional BFS and animate exploration + optimal path."""
        from solver import MazeSolver
        self._path_t0   = time.perf_counter()
        self._path_time = 0.0
        solver = MazeSolver(self.generator)
        path, layers = solver.bfs_bidir_layers(
            self.generator.entry, self.generator.exit
        )
        self.start_bidir_animation(path, layers)
        self._dirty = True

