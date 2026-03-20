#!/usr/bin/env python3

import sys


def ft_command_quest() -> None:
    print("=== Command Quest ===")
    if len(sys.argv) == 1:
        print("No argument provided.")
        command = sys.argv[0]
        print(f"Program Name: {command}")
        print(f"Total arguments: {len(sys.argv)}")
    else:
        print(f"Arguments received: {len(sys.argv) - 1}")
        for i in range(1, len(sys.argv)):
            print(f"Argument {i}: {sys.argv[i]}")
        print(f"Total arguments: {len(sys.argv)}")


if __name__ == "__main__":
    ft_command_quest()
