#!/usr/bin/env python3

import sys


def ft_command_quest() -> None:
    """display the command-line parameters."""
    print("=== Command Quest ===")
    print(f"Program name: {sys.argv[0]}")
    if len(sys.argv) == 1:
        print("No arguments provided!")
        print(f"Total arguments: {len(sys.argv)}")
        return
    print(f"Arguments received: {len(sys.argv) - 1}")
    index = 1
    for argument in sys.argv[1:]:
        print(f"Argument {index}: {argument}")
        index += 1
    print(f"Total arguments: {len(sys.argv)}")


if __name__ == "__main__":
    ft_command_quest()
