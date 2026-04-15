#!/usr/bin/env python3

import sys
import typing


def read_file(filename: str) -> None:
    print("=== Cyber Archives Recovery ===")
    print(f"Accessing file '{filename}'")
    file: typing.IO
    try:
        file = open(filename, "r")
    except FileNotFoundError as error:
        print(f"Error opening file '{filename}': {error}")
        return
    except PermissionError as error:
        print(f"Error opening file '{filename}': {error}")
        return
    print("---")
    print()
    print(file.read(), end="")
    print()
    print("---")
    file.close()
    print(f"File '{filename}' closed.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ft_ancient_text.py <file>")
        sys.exit(1)
    read_file(sys.argv[1])
