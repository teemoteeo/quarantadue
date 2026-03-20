class Plant:
    """a plant with growth methods."""

    def grow(self, cm: int) -> None:
        """increase the plant's height by cm."""
        self.height += cm

    def increment_age(self, days: int) -> None:
        """increase the plant's age by days."""
        self.age += days

    def get_info(self) -> str:
        """return plant info as a formatted string."""
        return f"{self.name}: {self.height}cm, {self.age} days old"


if __name__ == "__main__":

    rose = Plant()
    rose.name = "Rose"
    rose.height = 25
    rose.age = 30

    rose.initial_height = rose.height

    sunflower = Plant()
    sunflower.name = "Sunflower"
    sunflower.height = 80
    sunflower.age = 45

    sunflower.initial_height = sunflower.height

    print("=== Day 1 ===\n")
    print(rose.get_info())
    print(sunflower.get_info())
    print()
    rose.grow(7)
    rose.increment_age(6)
    sunflower.grow(4)
    sunflower.increment_age(6)
    print("=== Day 7 ===\n")
    print(rose.get_info())
    print(sunflower.get_info())
    print()
    print(f"Growth this week: +{rose.height - rose.initial_height}cm"
          f" for {rose.name}, +{sunflower.height - sunflower.initial_height}cm"
          f" for {sunflower.name}"
          )
