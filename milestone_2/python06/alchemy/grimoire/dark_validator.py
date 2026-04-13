#!/usr/bin/env python3

from .dark_spellbook import dark_spell_allowed_ingredients


def validate_ingredients(ingredients: str):
    allowed = dark_spell_allowed_ingredients()
    ingredients_lower = ingredients.lower()

    for item in allowed:
        if item in ingredients_lower:
            return f"{ingredients} - VALID"

    return f"{ingredients} - INVALID"
