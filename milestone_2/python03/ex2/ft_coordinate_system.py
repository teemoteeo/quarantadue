#!/usr/bin/env python3

import math


def get_player_pos() -> tuple[float, float, float]:
    """ask for valid player coordinates."""
    while True:
        raw = input("Enter new coordinates as floats in format 'x,y,z': ")
        parts = raw.split(',')
        if len(parts) != 3:
            print("Invalid syntax")
            continue
        try:
            x = float(parts[0].strip())
            y = float(parts[1].strip())
            z = float(parts[2].strip())
            return (x, y, z)
        except ValueError as error:
            bad_value = ""
            for part in parts:
                try:
                    float(part.strip())
                except ValueError:
                    bad_value = part.strip()
                    break
            print(f"Error on parameter '{bad_value}': {error}")


def distance(first: tuple[float, float, float],
             second: tuple[float, float, float]) -> float:
    """calculate the distance between two 3D points."""
    return math.sqrt(
        (second[0] - first[0]) ** 2
        + (second[1] - first[1]) ** 2
        + (second[2] - first[2]) ** 2
    )


if __name__ == "__main__":
    print("=== Game Coordinate System ===")
    print("Get a first set of coordinates")
    first = get_player_pos()
    print(f"Got a first tuple: {first}")
    print(f"It includes: X={first[0]}, Y={first[1]}, Z={first[2]}")
    print(f"Distance to center: {round(distance(first, (0.0, 0.0, 0.0)), 4)}")
    print("Get a second set of coordinates")
    second = get_player_pos()
    print("Distance between the 2 sets of coordinates: "
          f"{round(distance(first, second), 4)}")
