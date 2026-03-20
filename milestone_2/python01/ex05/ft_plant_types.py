class Plant:
    """base class for all plant types."""

    def __init__(self, name: str, height: int, age: int) -> None:
        """initialize a plant with name, height, and age."""
        self.name = name
        self.height = height  # in centimeters
        self.age = age  # in days


class Flower(Plant):
    """a plant subclass representing flowers."""

    def __init__(self, name: str, height: int, age: int, color: str) -> None:
        """initialize a flower with name, height, age, and color."""
        super().__init__(name, height, age)
        self.color = color

    def bloom(self) -> None:
        """print a blooming message."""
        print(f"{self.name} is blooming beautifully.")


class Tree(Plant):
    """a plant subclass representing trees."""

    def __init__(self, name: str, height: int,
                 age: int, trunk_diameter: int) -> None:
        """initialize a tree with name, height, age, and trunk diameter."""
        super().__init__(name, height, age)
        self.trunk_diameter = trunk_diameter  # in centimeters

    def produce_shade(self) -> None:
        """print the shade area provided by the tree."""
        shade_area = self.trunk_diameter * self.height // 10
        print(f"{self.name} provides {shade_area} square meters of shade.")


class Vegetable(Plant):
    """a plant subclass representing vegetables."""

    def __init__(self, name: str, height: int, age: int,
                 harvest_season: str, nutritional_value: str) -> None:
        """initialize a vegetable with harvest and nutrition info."""
        super().__init__(name, height, age)
        self.harvest_season = harvest_season
        self.nutritional_value = nutritional_value


if __name__ == "__main__":
    print("=== Garden Plant Types ===")
    print()

    rose = Flower("Rose", 25, 30, "red")
    tulip = Flower("Tulip", 30, 20, "white")

    oak = Tree("Oak", 500, 100, 120)
    pine = Tree("Pine", 600, 80, 100)

    tomato = Vegetable("Tomato", 150, 1, "summer", "vitamin C")
    carrot = Vegetable("Carrot", 30, 1, "fall", "beta-carotene")

    print(f"{rose.name} (Flower): {rose.height}cm, "
          f"{rose.age} days, {rose.color} color")
    rose.bloom()
    print()

    print(f"{oak.name} (Tree): {oak.height}cm, "
          f"{oak.age} days, {oak.trunk_diameter}cm diameter")
    oak.produce_shade()
    print()

    print(f"{tomato.name} (Vegetable): {tomato.height}cm, "
          f"{tomato.age} days, {tomato.harvest_season} harvest")
    print(f"Tomato is rich in {tomato.nutritional_value}.")
