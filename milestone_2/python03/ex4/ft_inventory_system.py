#!/usr/bin/env python3

import sys


def parse_input(argument: str) -> tuple[str, int] | None:
    """parse one inventory parameter."""
    parts = argument.split(':')
    if len(parts) != 2:
        print(f"Error - invalid parameter '{argument}'")
        return None
    item = parts[0]
    try:
        quantity = int(parts[1])
    except ValueError as error:
        print(f"Quantity error for '{item}': {error}")
        return None
    return (item, quantity)


def find_most_abundant(inventory: dict[str, int]) -> str:
    """find the most abundant item, keeping the first on ties."""
    first_item = list(inventory.keys())[0]
    most_abundant = first_item
    for item in inventory.keys():
        if inventory[item] > inventory[most_abundant]:
            most_abundant = item
    return most_abundant


def find_least_abundant(inventory: dict[str, int]) -> str:
    """find the least abundant item, keeping the first on ties."""
    first_item = list(inventory.keys())[0]
    least_abundant = first_item
    for item in inventory.keys():
        if inventory[item] < inventory[least_abundant]:
            least_abundant = item
    return least_abundant


if __name__ == "__main__":
    inventory: dict[str, int] = {}

    for argument in sys.argv[1:]:
        parsed = parse_input(argument)
        if parsed is None:
            continue
        item, quantity = parsed
        if item in inventory:
            print(f"Redundant item '{item}' - discarding")
            continue
        inventory[item] = quantity

    print("=== Inventory System Analysis ===")
    print(f"Got inventory: {inventory}")
    print(f"Item list: {list(inventory.keys())}")
    total_quantity = sum(inventory.values())
    print(f"Total quantity of the {len(inventory)} items: {total_quantity}")

    for item in inventory.keys():
        percentage = round((inventory[item] / total_quantity) * 100, 1)
        print(f"Item {item} represents {percentage}%")

    if len(inventory) > 0:
        most_abundant = find_most_abundant(inventory)
        least_abundant = find_least_abundant(inventory)
        print("Item most abundant: "
              f"{most_abundant} with quantity {inventory[most_abundant]}")
        print("Item least abundant: "
              f"{least_abundant} with quantity {inventory[least_abundant]}")

    inventory.update({'magic_item': 1})
    print(f"Updated inventory: {inventory}")
