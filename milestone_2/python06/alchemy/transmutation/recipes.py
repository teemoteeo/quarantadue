#!/usr/bin/env python3


import elements
import alchemy
from ..potions import strenght_potion


def lead_to_gold() -> str:
    return (
        f"Recipe transmuting Lead to Gold: brew ‘{alchemy.create_air()}’"
        f" and ‘{strenght_potion()}’ mixed with ‘{elements.create_fire()}’"
    )
