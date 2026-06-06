#!/usr/bin/env python3

import sys

from maze_parser import parse_input
from user import user


def main() -> int:
    """
    Controllo gli argomenti (sys.argv), che il config file esista e sia valido.
    Creo l'oggetto "maze" tramita la classe e la config. Una volta creato
    il labirinto è pronto per l'output e per il visual.

    Return 0 se OK, 1 se Error.
    """
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
    try:
        user()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
