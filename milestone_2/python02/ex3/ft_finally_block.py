#!/usr/bin/env python3

class InvalidPlantError(Exception):
    pass


def raise_invalid_plant_error(plant_name: str) -> None:
    raise InvalidPlantError(f"'{plant_name}' "
                            f"is not a valid plant for this garden!")


def water_plants(plant_list: list) -> None:
    print("Opening watering system")
    try:
        for plant in plant_list:
            if plant is None:
                raise_invalid_plant_error(plant)
            print(f"Watering {plant}...")
        print("Watering completed successfully!")
    except InvalidPlantError:
        print("Cannot water None - invalid plant")
    finally:
        print("Closing watering system (cleanup)")


def test_watering_system():
    print("Testing normal watering...")
    water_plants(["tomato", "lettuce", "carrots"])
    print("\nTesting with error...")
    water_plants(["tomato", None, "carrots"])


if __name__ == "__main__":
    print("=== Garden Watering System ===")
    print()
    test_watering_system()
