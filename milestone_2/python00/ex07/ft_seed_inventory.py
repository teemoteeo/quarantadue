def ft_seed_inventory(seed_type: str, quantity: int, unit: str) -> None:
    seed_capitalized = seed_type.capitalize()

    if unit == "packets":
        print(f"{seed_capitalized} seeds: {quantity} packets available")
    elif unit == "grams":
        print(f"{seed_capitalized} seeds: {quantity} grams total")
    elif unit == "area":
        print(f"{seed_capitalized} seeds: covers {quantity} square meters")
    else:
        print("Unknown unit type")
