#!/usr/bin/env python3


from .elements import create_air, create_earth


def healing_potion() -> str:
    return (
        f"Healing potion brewed with '{create_earth()}' and '{create_air()}'"
    )


def strenght_potion() -> str:
    return (
        f"Strenght potion brewed with '{create_earth()}'"
        f" and '{create_air()}'"
    )
