#!/usr/bin/env python3
#!/usr/bin/env python3

import sys
import curses
import time
import pyfiglet  # type: ignore

from generator import MazeGenerator
from parser import MazeConfig, parse_input

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

_SPLASH_FONT = {
    'A': ["01110", "10001", "11111", "10001", "10001"],
    '-': ["00000", "00000", "11111", "00000", "00000"],
    'M': ["10001", "11011", "10101", "10001", "10001"],
    'Z': ["11111", "00011", "00110", "01100", "11111"],
    'E': ["11111", "10000", "11110", "10000", "11111"],
    'I': ["11111", "00100", "00100", "00100", "11111"],
    'N': ["10001", "11001", "10101", "10011", "10001"],
    'G': ["01110", "10000", "10111", "10001", "01110"],
}

_CP_ENTRY = 1
_CP_EXIT = 2
_CP_FRONT_A = 3  # BFS from entry — frontier
_CP_FRONT_B = 4  # BFS from exit — frontier
_CP_SEEN_A = 5  # BFS from entry — explored (semi-transparent tint)
_CP_SEEN_B = 6  # BFS from exit — explored (semi-transparent tint)
_CP_PATH = 7  # final path
_CP_WALL = 8
_CP_TITLE = 9
_CP_STATUS = 10
_CP_42 = 11
_CP_BTN = 12
_CP_BTN_HOV = 13

_BUTTONS = [
    (' Regen ', 0),
    (' Path  ', 1),
    (' Color ', 2),
    (' Quit  ', 3),
]

# (wall_fg, p42_fg, p42_bg) — basic 8-color schemes
_BASE_SCHEMES: list[tuple[int, int, int]] = [
    (curses.COLOR_WHITE,   curses.COLOR_WHITE,   curses.COLOR_RED),
    (curses.COLOR_CYAN,    curses.COLOR_BLACK,   curses.COLOR_CYAN),
    (curses.COLOR_YELLOW,  curses.COLOR_BLACK,   curses.COLOR_YELLOW),
    (curses.COLOR_GREEN,   curses.COLOR_BLACK,   curses.COLOR_GREEN),
    (curses.COLOR_MAGENTA, curses.COLOR_WHITE,   curses.COLOR_MAGENTA),
    (curses.COLOR_BLUE,    curses.COLOR_WHITE,   curses.COLOR_BLUE),
    (curses.COLOR_RED,     curses.COLOR_BLACK,   curses.COLOR_WHITE),
]

# Extra schemes for terminals with 256-color support
_SCHEMES_256: list[tuple[int, int, int]] = [
    (208, 0,   208),  # orange
    (93,  255, 93),   # purple
    (201, 0,   201),  # hot pink
    (46,  0,   46),   # lime
    (196, 255, 196),  # bright red
    (51,  0,   51),   # bright cyan
    (226, 0,   226),  # bright yellow
]


class MazeVisualizer:
    def __init__(self, generator: MazeGenerator, config: MazeConfig) -> None:
        self.generator = generator
        self.config = config
        self.grid = generator.grid
        self.show_path = False
        self.animating = False
        self.bfs_done = False
        self.bfs_state: dict | None = None
        self.path: list[tuple[int, int]] = []
        self._last_step = 0.0
        self._step_s = 0.01  # seconds between BFS expansion steps
        self._wall_idx = 0
        self._schemes: list[tuple[int, int, int]] = list(_BASE_SCHEMES)
        self._btn_rects: list[tuple[int, int, int]] = []
        self._hovered_btn: int = 0

    def run(self) -> None:
        import os
        tty = os.open('/dev/tty', os.O_RDWR)
        os.dup2(tty, 0)
        os.dup2(tty, 1)
        os.close(tty)
        curses.wrapper(self._main)

    # ------------------------------------------------------------------ setup

    def _init_colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(_CP_ENTRY,   curses.COLOR_BLACK,  curses.COLOR_GREEN)
        curses.init_pair(_CP_EXIT,    curses.COLOR_BLACK,  curses.COLOR_RED)
        curses.init_pair(_CP_FRONT_A, curses.COLOR_WHITE,  curses.COLOR_CYAN)
        curses.init_pair(_CP_FRONT_B, curses.COLOR_WHITE,  curses.COLOR_BLUE)
        curses.init_pair(_CP_SEEN_A,  curses.COLOR_CYAN,   -1)
        curses.init_pair(_CP_SEEN_B,  curses.COLOR_MAGENTA, -1)
        curses.init_pair(_CP_TITLE,   curses.COLOR_RED,    -1)
        curses.init_pair(_CP_STATUS,  curses.COLOR_BLACK,  curses.COLOR_WHITE)
        curses.init_pair(_CP_BTN,     curses.COLOR_BLACK,  curses.COLOR_WHITE)
        curses.init_pair(_CP_BTN_HOV, curses.COLOR_BLACK,  curses.COLOR_CYAN)
        if curses.COLORS >= 256:
            self._schemes.extend(_SCHEMES_256)
            curses.init_pair(_CP_PATH, 0, 226)
        else:
            curses.init_pair(
                _CP_PATH, curses.COLOR_BLACK, curses.COLOR_YELLOW
            )
        wall_fg, p42_fg, p42_bg = self._schemes[0]
        curses.init_pair(_CP_WALL, wall_fg, -1)
        curses.init_pair(_CP_42, p42_fg, p42_bg)

    def _main(self, stdscr: "curses._CursesWindow") -> None:
        self._init_colors()
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(50)
        curses.mousemask(
            curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
        )

        self._splash(stdscr)

        running = True
        while running:
            ch = stdscr.getch()
            n_btns = len(_BUTTONS)
            if ch in (ord('q'), ord('Q'), 27):
                running = False
            elif ch == curses.KEY_MOUSE:
                if self._handle_mouse():
                    running = False
            elif ch == curses.KEY_LEFT:
                self._hovered_btn = (self._hovered_btn - 1) % n_btns
            elif ch == curses.KEY_RIGHT:
                self._hovered_btn = (self._hovered_btn + 1) % n_btns
            elif ch in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                if self._activate_btn(self._hovered_btn):
                    running = False
            elif ch in (ord('r'), ord('R')):
                self._regenerate()
            elif ch in (ord('p'), ord('P')):
                self._toggle_path()
            elif ch in (ord('c'), ord('C')):
                self._cycle_wall_color()

            now = time.monotonic()
            if self.animating and not self.bfs_done:
                if now - self._last_step >= self._step_s:
                    self._step_bfs()
                    self._last_step = now

            stdscr.erase()
            self._draw_ui(stdscr)
            stdscr.refresh()

    # --------------------------------------------------------------- actions

    def _regenerate(self) -> None:
        new_gen = type(self.generator)(self.config)
        self.generator = new_gen
        self.grid = new_gen.grid
        self.show_path = False
        self.animating = False
        self.bfs_done = False
        self.bfs_state = None
        self.path = []

    def _toggle_path(self) -> None:
        self.show_path = not self.show_path
        if self.show_path:
            self._start_bfs()
        else:
            self.animating = False
            self.bfs_done = False
            self.bfs_state = None
            self.path = []

    def _cycle_wall_color(self) -> None:
        self._wall_idx = (self._wall_idx + 1) % len(self._schemes)
        wall_fg, p42_fg, p42_bg = self._schemes[self._wall_idx]
        curses.init_pair(_CP_WALL, wall_fg, -1)
        curses.init_pair(_CP_42, p42_fg, p42_bg)

    def _activate_btn(self, idx: int) -> bool:
        """Fire button action. Return True to quit."""
        if idx == 0:
            self._regenerate()
        elif idx == 1:
            self._toggle_path()
        elif idx == 2:
            self._cycle_wall_color()
        elif idx == 3:
            return True
        return False

    def _handle_mouse(self) -> bool:
        """Process mouse event. Return True to quit."""
        try:
            _, mx, my, _, bstate = curses.getmouse()
        except curses.error:
            return False
        prev = self._hovered_btn
        self._hovered_btn = prev  # keep selection if mouse off buttons
        for i, (br, c0, c1) in enumerate(self._btn_rects):
            if my == br and c0 <= mx < c1:
                self._hovered_btn = i
                break
        clicked = bool(
            bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED)
        )
        if not clicked:
            return False
        return self._activate_btn(self._hovered_btn)

    # -------------------------------------------------------------------- BFS

    def _start_bfs(self) -> None:
        entry = self.config.entry
        exit_ = self.config.exit
        self.bfs_state = {
            'visited_a': {entry: None},
            'visited_b': {exit_: None},
            'front_a':   {entry},
            'front_b':   {exit_},
            'meet':      None,
            'done':      False,
        }
        self.animating = True
        self.bfs_done = False
        self.path = []
        self._last_step = time.monotonic()

    def _step_bfs(self) -> None:
        state = self.bfs_state
        if not state or state['done']:
            self.bfs_done = True
            self.animating = False
            return

        W, H = self.config.width, self.config.height
        dirs = [(0, -1, NORTH), (1, 0, EAST), (0, 1, SOUTH), (-1, 0, WEST)]

        def expand(front, visited_self, visited_other):
            nxt = set()
            meet = None
            for x, y in front:
                for dx, dy, wb in dirs:
                    if not (self.grid[y][x] & (1 << wb)):
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < W and 0 <= ny < H
                                and (nx, ny) not in visited_self):
                            visited_self[(nx, ny)] = (x, y)
                            nxt.add((nx, ny))
                            if (nx, ny) in visited_other:
                                meet = (nx, ny)
            return nxt, meet

        new_a, meet = expand(
            state['front_a'], state['visited_a'], state['visited_b'])
        state['front_a'] = new_a
        if meet:
            state['meet'] = meet
            state['done'] = True
            self._build_path()
            self.bfs_done = True
            self.animating = False
            return

        new_b, meet = expand(
            state['front_b'], state['visited_b'], state['visited_a'])
        state['front_b'] = new_b
        if meet:
            state['meet'] = meet
            state['done'] = True
            self._build_path()
            self.bfs_done = True
            self.animating = False
            return

        if not new_a and not new_b:
            state['done'] = True
            self.bfs_done = True
            self.animating = False

    def _build_path(self) -> None:
        state = self.bfs_state
        meet = state['meet']

        seg_a: list[tuple[int, int]] = []
        cur = meet
        while cur is not None:
            seg_a.append(cur)
            cur = state['visited_a'].get(cur)
        seg_a.reverse()

        seg_b: list[tuple[int, int]] = []
        cur = state['visited_b'].get(meet)
        while cur is not None:
            seg_b.append(cur)
            cur = state['visited_b'].get(cur)

        self.path = seg_a + seg_b
        state['front_a'] = set()
        state['front_b'] = set()
        state['visited_a'] = {}
        state['visited_b'] = {}

    # -------------------------------------------------------------- rendering

    def _splash(self, scr: "curses._CursesWindow") -> None:
        scr.erase()
        rows, cols = scr.getmaxyx()
        raw = pyfiglet.figlet_format('A-MAZE-ING', font='ansi_shadow')
        lines = raw.splitlines()
        title_h = len(lines)
        title_w = max(len(ln) for ln in lines) if lines else 0
        origin_row = max(0, (rows - title_h) // 2)
        origin_col = max(0, (cols - title_w) // 2)
        attr = curses.color_pair(_CP_TITLE) | curses.A_BOLD
        for r, line in enumerate(lines):
            sy = origin_row + r
            if sy >= rows - 1:
                break
            for c, ch in enumerate(line):
                sx = origin_col + c
                if 0 <= sx < cols - 1:
                    try:
                        scr.addstr(sy, sx, ch, attr)
                    except curses.error:
                        pass
        hint = "Press any key to start..."
        try:
            scr.addstr(
                rows - 1,
                max(0, (cols - len(hint)) // 2),
                hint
            )
        except curses.error:
            pass
        scr.refresh()
        scr.timeout(2000)
        scr.getch()
        scr.timeout(50)

    def _draw_ui(self, scr: "curses._CursesWindow") -> None:
        rows, cols = scr.getmaxyx()
        wall_attr = curses.color_pair(_CP_WALL)

        # title
        title = ' A-MAZE-ING '
        cx = 0
        try:
            scr.addstr(0, cx, title[:cols - 1], curses.A_BOLD | wall_attr)
        except curses.error:
            pass
        cx += len(title) + 1

        # buttons
        self._btn_rects = []
        for i, (lbl, _) in enumerate(_BUTTONS):
            btn = f'[{lbl}]'
            if cx + len(btn) >= cols:
                break
            if i == self._hovered_btn:
                attr = curses.color_pair(_CP_BTN_HOV) | curses.A_BOLD
            else:
                attr = curses.color_pair(_CP_BTN) | curses.A_BOLD
            self._btn_rects.append((0, cx, cx + len(btn)))
            try:
                scr.addstr(0, cx, btn, attr)
            except curses.error:
                pass
            cx += len(btn) + 2

        maze_h = self.config.height * 2 + 1
        maze_w = self.config.width * 3 + 1
        row_off = max(1, 1 + (rows - 2 - maze_h) // 2)
        col_off = max(0, (cols - maze_w) // 2)
        self._draw_maze(scr, row_offset=row_off, col_offset=col_off)

        if self.animating:
            status = "  BFS running..."
        elif self.bfs_done and self.path:
            status = f"  Path found — {len(self.path)} cells"
        elif self.bfs_done:
            status = "  No path found"
        else:
            status = "  [P] to run bidirectional BFS"
        try:
            scr.addstr(
                rows - 1, 0,
                status[:cols - 1],
                curses.color_pair(_CP_STATUS)
            )
        except curses.error:
            pass

    def _draw_maze(
            self, scr: "curses._CursesWindow",
            row_offset: int = 2, col_offset: int = 0) -> None:
        rows, cols = scr.getmaxyx()
        W, H = self.config.width, self.config.height
        entry = self.config.entry
        exit_ = self.config.exit
        wall_attr = curses.color_pair(_CP_WALL) | curses.A_DIM
        path_attr = curses.color_pair(_CP_PATH) | curses.A_BOLD

        state = self.bfs_state
        front_a = state['front_a'] if state else set()
        front_b = state['front_b'] if state else set()
        visited_a = state['visited_a'] if state else {}
        visited_b = state['visited_b'] if state else {}
        path_set = set(self.path) if self.bfs_done else set()

        def corner(wy: int, wx: int) -> str:
            top, bot = wy == 0, wy == H
            lft, rgt = wx == 0, wx == W
            if top and lft: return '╔'
            if top and rgt: return '╗'
            if bot and lft: return '╚'
            if bot and rgt: return '╝'
            if top: return '╦'
            if bot: return '╩'
            if lft: return '╠'
            if rgt: return '╣'
            return '╬'

        pattern_cells = self.generator._pattern_cells

        def cell_display(x: int, y: int) -> tuple[int, str]:
            pos = (x, y)
            if pos in pattern_cells:
                return curses.color_pair(_CP_42) | curses.A_BOLD, '▓▓'
            if pos in path_set:
                lbl = ' E' if pos == entry else (
                    ' X' if pos == exit_ else '▓▓')
                return path_attr, lbl
            if pos == entry:
                return curses.color_pair(_CP_ENTRY), ' E'
            if pos == exit_:
                return curses.color_pair(_CP_EXIT),  ' X'
            if pos in front_a:
                return curses.color_pair(_CP_FRONT_A), '  '
            if pos in front_b:
                return curses.color_pair(_CP_FRONT_B), '  '
            if pos in visited_a:
                return curses.color_pair(_CP_SEEN_A) | curses.A_DIM, '· '
            if pos in visited_b:
                return curses.color_pair(_CP_SEEN_B) | curses.A_DIM, '· '
            return 0, '  '

        for y in range(H):
            # horizontal-wall row (top of cell y)
            sr = row_offset + y * 2
            if sr >= rows - 1:
                break
            sc = col_offset
            try:
                scr.addstr(sr, col_offset, corner(y, 0), wall_attr)
            except curses.error:
                pass
            for x in range(W):
                n_wall = bool(self.grid[y][x] & (1 << NORTH))
                p_conn = (not n_wall and y > 0
                          and (x, y - 1) in path_set
                          and (x, y) in path_set)
                hw = '▓▓' if p_conn else ('══' if n_wall else '  ')
                ha = path_attr if p_conn else wall_attr
                try:
                    scr.addstr(sr, sc + 1, hw, ha)
                    scr.addstr(sr, sc + 3, corner(y, x + 1), wall_attr)
                except curses.error:
                    pass
                sc += 3

            # cell-content row
            sr = row_offset + y * 2 + 1
            if sr >= rows - 1:
                break
            sc = col_offset
            for x in range(W):
                w_wall = bool(self.grid[y][x] & (1 << WEST))
                p_conn = (not w_wall and x > 0
                          and (x - 1, y) in path_set
                          and (x, y) in path_set)
                vw = '▓' if p_conn else ('║' if w_wall else ' ')
                va = path_attr if p_conn else wall_attr
                attr, text = cell_display(x, y)
                try:
                    scr.addstr(sr, sc, vw, va)
                    scr.addstr(sr, sc + 1, text, attr)
                except curses.error:
                    pass
                sc += 3
            rv = '║' if (self.grid[y][W - 1] & (1 << EAST)) else ' '
            try:
                scr.addstr(sr, sc, rv, wall_attr)
            except curses.error:
                pass

        # bottom border
        sr = row_offset + H * 2
        if sr < rows - 1:
            sc = col_offset
            try:
                scr.addstr(sr, col_offset, corner(H, 0), wall_attr)
            except curses.error:
                pass
            for x in range(W):
                s_wall = bool(self.grid[H - 1][x] & (1 << SOUTH))
                hw = '══' if s_wall else '  '
                try:
                    scr.addstr(sr, sc + 1, hw, wall_attr)
                    scr.addstr(sr, sc + 3, corner(H, x + 1), wall_attr)
                except curses.error:
                    pass
                sc += 3


if __name__ == "__main__":
    config = parse_input("config.txt")
    if not config.validate():
        print("config non valida")
        sys.exit(1)
    gen = MazeGenerator(config)
    MazeVisualizer(gen, config).run()
