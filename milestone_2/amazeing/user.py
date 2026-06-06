#!/usr/bin/env python3
"""user.py — thin entry point: parse config, launch curses TUI."""

from maze_parser import parse_input
from generator import MazeGenerator
from visual import Visualinho
from splash import main as splash


def user() -> None:
    splash()
    config = parse_input("config.txt")
    maze   = MazeGenerator(config)
    vis    = Visualinho(maze)
    vis.run(config)

