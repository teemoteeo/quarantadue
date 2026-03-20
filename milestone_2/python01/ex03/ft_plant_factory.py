class Plant:
    """a plant with initialized attributes."""

    def __init__(self, name: str, height: int, age: int) -> None:
        """initialize a plant with name, height, and age."""
        self.name = name
        self.age = age
        self.height = height

    def short_info(self) -> str:
        """return a short description of the plant."""
        return f"{self.name} ({self.height}cm, {self.age} days)"


if __name__ == "__main__":

    print("=== Plant Factory Output ===")
    plants = [
        Plant("Rose", 30, 25),
        Plant("Oak", 365, 200),
        Plant("Cactus", 90, 5),
        Plant("Sunflower", 80, 45),
        Plant("Fern", 120, 15),
    ]

    for plant in plants:
        print(f"Created: {plant.short_info()}")

    print(f"\nTotal plants created: {len(plants)}")
