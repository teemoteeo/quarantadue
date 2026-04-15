#!/usr/bin/env python3


from .elements import create_air, create_earth
import elements as root_elements


def healing_potion() -> str:
    return (
        f"Healing potion brewed with '{create_earth()}' and '{create_air()}'"
    )


def strength_potion() -> str:
    return (
        f"Strength potion brewed with '{root_elements.create_fire()}'"
        f" and '{root_elements.create_water()}'"
    )
