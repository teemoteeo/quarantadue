#!/usr/bin/env python3

import sys

from generator import MazeGenerator
from parser import parse_input
from visualizer import MazeVisualizer


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py <config.txt>", file=sys.stderr)
        return 1
    config_path = sys.argv[1]
    try:
        config = parse_input(config_path)
    except FileNotFoundError:
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1
    except (KeyError, ValueError) as e:
        print(f"Error: invalid config ({e})", file=sys.stderr)
        return 1
    if not config.validate():
        print("Error: config validation failed", file=sys.stderr)
        return 1

    maze = MazeGenerator(config)
    maze.write_output(config.output_file)
    MazeVisualizer(maze, config).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
