#!/usr/bin/env python3

import sys
import typing


def read_file(filename: str) -> str | None:
    print("=== Cyber Archives Recovery & Preservation ===")
    print(f"Accessing file '{filename}'")
    file: typing.IO
    try:
        file = open(filename, "r")
    except FileNotFoundError as error:
        print(f"Error opening file '{filename}': {error}")
        return None
    except PermissionError as error:
        print(f"Error opening file '{filename}': {error}")
        return None
    print("---")
    print()
    content = file.read()
    print(content, end="")
    print()
    print("---")
    file.close()
    print(f"File '{filename}' closed.")
    return content


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ft_archive_creation.py <file>")
        sys.exit(1)

    content = read_file(sys.argv[1])
    if content is None:
        sys.exit(1)

    lines = content.splitlines()
    new_lines = [line + "#" for line in lines]
    new_content = "\n".join(new_lines)

    print()
    print("Transform data:")
    print("---")
    print()
    print(new_content)
    print()
    print("---")

    output_name = input("Enter new file name (or empty): ")
    if not output_name:
        print("Not saving data.")
    else:
        print(f"Saving data to '{output_name}'")
        try:
            out_file = open(output_name, "w")
            out_file.write(new_content)
            out_file.close()
            print(f"Data saved in file '{output_name}'.")
        except PermissionError as error:
            print(f"Error opening file '{output_name}': {error}")
            print("Data not saved.")
