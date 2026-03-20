class Plant:
    """a simple plant class."""

    pass


if __name__ == "__main__":

    rose = Plant()
    rose.name = "Rose"
    rose.height = 25  # in centimeters
    rose.age = 30     # in days

    sunflower = Plant()
    sunflower.name = "Sunflower"
    sunflower.height = 80  # in centimeters
    sunflower.age = 45     # in days

    cactus = Plant()
    cactus.name = "Cactus"
    cactus.height = 15  # in centimeters
    cactus.age = 120    # in days

    print("=== Garden Plant Registry ===")
    for plant in (rose, sunflower, cactus):
        print(f"{plant.name}: {plant.height}cm, {plant.age} days old")
