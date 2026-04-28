#!/usr/bin/env python3

from typing import List, Tuple

from ex0 import CreatureFactory, FlameFactory, AquaFactory
from ex1 import HealingCreatureFactory, TransformCreatureFactory
from ex2 import (
    BattleStrategy,
    NormalStrategy,
    AggressiveStrategy,
    DefensiveStrategy,
    battle,
)


def show(
    idx: int,
    label: str,
    labels: List[Tuple[str, str]],
    opponents: List[Tuple[CreatureFactory, BattleStrategy]],
) -> None:
    print(f"Tournament {idx} ({label})")
    items = ", ".join(f"({a}+{b})" for a, b in labels)
    print(f" [ {items} ]")
    battle(opponents)


if __name__ == "__main__":
    flame = FlameFactory()
    aqua = AquaFactory()
    healing = HealingCreatureFactory()
    transform = TransformCreatureFactory()

    normal = NormalStrategy()
    aggressive = AggressiveStrategy()
    defensive = DefensiveStrategy()

    show(
        0,
        "basic",
        [("Flameling", "Normal"), ("Healing", "Defensive")],
        [(flame, normal), (healing, defensive)],
    )
    print()
    show(
        1,
        "error",
        [("Flameling", "Aggressive"), ("Healing", "Defensive")],
        [(flame, aggressive), (healing, defensive)],
    )
    print()
    show(
        2,
        "multiple",
        [
            ("Aquabub", "Normal"),
            ("Healing", "Defensive"),
            ("Transform", "Aggressive"),
        ],
        [(aqua, normal), (healing, defensive), (transform, aggressive)],
    )
