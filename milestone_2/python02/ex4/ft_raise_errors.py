#!/usr/bin/env python3

class InvalidName(ValueError):
    pass


class InvalidWaterLevel(ValueError):
    pass


class InvalidSunlightHours(ValueError):
    pass


def check_plant_health(
        plant_name: str, water_level: int, sunlight_hours: int) -> None:
    if plant_name == "":
        raise InvalidName("Plant name cannot be empty.")
    elif water_level < 0 or water_level > 10:
        raise InvalidWaterLevel("Water level must be between 0 and 10.")
    elif sunlight_hours < 2 or sunlight_hours > 12:
        raise InvalidSunlightHours("Sunlight hours must be between 2 and 12.")
    else:
        print("Plant is healthy!")


def test_plant_checks():
    try:
        print("\nTesting good values...")
        check_plant_health("Rose", 5, 6)
    except (InvalidName, InvalidWaterLevel, InvalidSunlightHours) as e:
        print(e)

    try:
        print("\nTesting empty plant name...")
        check_plant_health("", 5, 6)
    except InvalidName as e:
        print(e)

    try:
        print("\nTesting bad water level...")
        check_plant_health("Fern", -1, 6)
    except InvalidWaterLevel as e:
        print(e)

    try:
        print("\nTesting bad sunlight hours...")
        check_plant_health("Cactus", 5, 1)
    except InvalidSunlightHours as e:
        print(e)


if __name__ == "__main__":
    print("=== Garden Plant Health Checker ===\n")
    test_plant_checks()
    print("All error raising tests completed.")
