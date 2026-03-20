#!/usr/bin/env python3


class GardenError(Exception):
    pass


class PlantError(GardenError):
    pass


class WaterError(GardenError):
    pass


class GardenManager:
    def __init__(self) -> None:
        self.plants: list = []
        self.water_level: int = 10

    def add_plant(self, plant: str) -> None:
        if not plant:
            raise PlantError("Plant name cannot be empty!")
        self.plants.append(plant)
        print(f"Added {plant} successfully")

    def water_plants(self, plant_list: list) -> None:
        print("Opening watering system")
        try:
            for plant in plant_list:
                print(f"Watering {plant} - success")
                self.water_level -= 1
        finally:
            print("Closing watering system (cleanup)")

    def check_plant_health(
            self, plant: str, water_level: int, sunlight: int) -> None:
        if water_level < 1 or water_level > 10:
            raise WaterError(
                f"Water level {water_level} is too high (max 10)"
            )
        if sunlight < 2 or sunlight > 12:
            raise PlantError(
                f"Sunlight hours {sunlight} out of range (2-12)"
            )
        print(f"{plant}: healthy (water: {water_level}, sun: {sunlight})")

    def consume_water(self, amount: int) -> None:
        if self.water_level < amount:
            raise WaterError("Not enough water in tank")
        self.water_level -= amount


def test_garden_management() -> None:
    print("=== Garden Management System ===\n")
    manager = GardenManager()

    print("Adding plants to garden...")
    try:
        manager.add_plant("tomato")
        manager.add_plant("lettuce")
        manager.add_plant("")
    except PlantError as e:
        print(f"Error adding plant: {e}")

    print("\nWatering plants...")
    manager.water_plants(["tomato", "lettuce"])

    print("\nChecking plant health...")
    for plant, water, sun in [("tomato", 5, 8), ("lettuce", 15, 6)]:
        try:
            manager.check_plant_health(plant, water, sun)
        except GardenError as e:
            print(f"Error checking {plant}: {e}")

    print("\nTesting error recovery...")
    try:
        manager.water_level = 0
        manager.consume_water(5)
    except GardenError as e:
        print(f"Caught GardenError: {e}")
    print("System recovered and continuing...")

    print("\nGarden management system test complete!")


if __name__ == "__main__":
    test_garden_management()
