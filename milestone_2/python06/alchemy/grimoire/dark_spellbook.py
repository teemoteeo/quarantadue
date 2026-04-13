#!/usr/bin/env python3

from .dark_validator import validate_ingredients


def dark_spell_allowed_ingredients():
    return ["bats", "frogs", "arsenic", "eyeball"]


def dark_spell_record(spell_name: str, ingredients: str):
    result = validate_ingredients(ingredients)
    return f"Spell recorded: {spell_name} ({result})"
