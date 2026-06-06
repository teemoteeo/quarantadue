#!/usr/bin/env python3
"""splash.py — display the aMAZEing title screen."""

import curses

_LOGO = [
    " █████╗  ███╗   ███╗ █████╗ ███████╗███████╗ ██╗███╗   ██╗ ██████╗",
    "██╔══██╗ ████╗ ████║██╔══██╗╚══███╔╝██╔════╝ ██║████╗  ██║██╔════╝",
    "███████║ ██╔████╔██║███████║  ███╔╝ █████╗   ██║██╔██╗ ██║██║  ███╗",
    "██╔══██║ ██║╚██╔╝██║██╔══██║ ███╔╝  ██╔══╝   ██║██║╚██╗██║██║   ██║",
    "██║  ██║ ██║ ╚═╝ ██║██║  ██║███████╗███████╗ ██║██║ ╚████║╚██████╔╝",
    "╚═╝  ╚═╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝",
]


def _main(stdscr: "curses.window") -> None:
    curses.curs_set(0)
    stdscr.clear()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    attr = curses.color_pair(1) | curses.A_BOLD

    # double size: each char repeated twice (width), each line printed twice (height)
    scaled = ["".join(ch * 2 for ch in line) for line in _LOGO]

    max_y, max_x = stdscr.getmaxyx()
    logo_h = len(scaled) * 2
    logo_w = max(len(line) for line in scaled)
    start_row = max(0, (max_y - logo_h) // 2)

    for i, line in enumerate(scaled):
        for rep in range(2):
            row = start_row + i * 2 + rep
            if row >= max_y:
                break
            col = max(0, (max_x - logo_w) // 2)
            try:
                stdscr.addstr(row, col, line[:max_x - col], attr)
            except curses.error:
                pass

    hint = "press any key"
    hint_row = min(start_row + logo_h + 2, max_y - 1)
    hint_col = max(0, (max_x - len(hint)) // 2)
    try:
        stdscr.addstr(hint_row, hint_col, hint, curses.A_BOLD)
    except curses.error:
        pass

    stdscr.refresh()
    stdscr.getch()


def main() -> None:
    curses.wrapper(_main)


if __name__ == "__main__":
    main()
