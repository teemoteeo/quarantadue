class GardenManager:

    class GardenStats:
        """helper class for garden statistics."""

        def __init__(self) -> None:
            """initialize stats tracking"""
            self.plants_added = 0
            self.total_growth = 0

    def __init__(self, garden_name: str) -> None:
        """initialize a garden manager with a garden name."""
        self.garden_name = garden_name
        self.plants = []
        self.stats = GardenManager.GardenStats()

    def add_plant(self, plant: 'Plant') -> None:
        """add a plant to the garden and update stats."""
        self.plants.append(plant)
        self.stats.plants_added += 1
        print(f"Added {plant.name} to {self.garden_name}'s garden")

    def grow_plant(self, plant: 'Plant', growth: int) -> None:
        """grow a plant by a certain amount and update stats."""
        plant.height += growth
        self.stats.total_growth += growth
        print(f"{plant.name} grew {growth}cm")

    def grow_all_plants(self, growth: int) -> None:
        """grow all plants by a certain amount and update stats."""
        print(f"{self.garden_name} is helping all plants grow...")
        for plant in self.plants:
            self.grow_plant(plant, growth)

    @classmethod
    def create_garden_network(cls) -> list:
        """create a network between two gardens (placeholder method)."""
        alice = cls("Alice")
        bob = cls("Bob")
        return [alice, bob]

    @staticmethod
    def validate_height(height: int) -> bool:
        """validate if the height is within acceptable range."""
        return 0 <= height <= 1000


class Plant:
    def __init__(self, name: str, height: int, age: int) -> None:
        """initialize a plant with name, height, and age."""
        self.name = name
        self.height = height
        self.age = age


class FloweringPlant(Plant):
    def __init__(self, name: str, height: int, age: int,
                 color: str, blooming: bool) -> None:
        """initialize a flowering plant with blooming status."""
        super().__init__(name, height, age)
        self.color = color
        self.blooming = blooming


class PrizeFlower(FloweringPlant):
    def __init__(self, name: str, height: int, age: int,
                 blooming: bool, color: str, prize_points: int) -> None:
        """initialize a prize flower with prize points."""
        super().__init__(name, height, age, color, blooming)
        self.prize_points = prize_points


if __name__ == "__main__":

    gardens = GardenManager.create_garden_network()
    alice = gardens[0]
    bob = gardens[1]

    print("=== Garden Management System Demo ===")
    oak = Plant("Oak Tree", 100, 5)
    rose = FloweringPlant("Rose", 25, 2, "red", True)
    sunflower = PrizeFlower("Sunflower", 50, 1, True, "yellow", 10)

    alice.add_plant(oak)
    alice.add_plant(rose)
    alice.add_plant(sunflower)
    bob.add_plant(Plant("Canapa", 92, 4))
    print()

    alice.grow_all_plants(1)
    print()

    print(f"=== {alice.garden_name}'s Garden Report ===")
    print("Plants in garden:")

    for plant in alice.plants:
        if isinstance(plant, PrizeFlower):
            print(f"- {plant.name}: {plant.height}cm, "
                  f"{plant.color} flowers (blooming), "
                  f"Prize points: {plant.prize_points}")
        elif isinstance(plant, FloweringPlant):
            print(f"- {plant.name}: {plant.height}cm, "
                  f"{plant.color} flowers (blooming)")
        else:
            print(f"- {plant.name}: {plant.height}cm")

    regular = 0
    flowering = 0
    prize = 0
    for plant in alice.plants:
        if isinstance(plant, PrizeFlower):
            prize += 1
        elif isinstance(plant, FloweringPlant):
            flowering += 1
        else:
            regular += 1
    print(f"\nPlants added: {alice.stats.plants_added}, Total growth: "
          f"{alice.stats.total_growth}cm")
    print(f"Plant types: {regular} regular, {flowering} flowering, "
          f"{prize} prize flowers\n")

    print(f"Height validation tests: {GardenManager.validate_height(50)}")

    alice_score = sum(plant.height for plant in alice.plants)
    bob_score = sum(plant.height for plant in bob.plants)
    print(f"Garden scores - Alice: {alice_score}, Bob: {bob_score}")

    print(f"Total gardens managed: {len(gardens)}")
