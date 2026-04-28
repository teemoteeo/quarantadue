#!/usr/bin/env python3

from typing import List, Tuple

from ex0.factory import CreatureFactory
from .strategy import BattleStrategy, InvalidStrategyError


def battle(opponents: List[Tuple[CreatureFactory, BattleStrategy]]) -> None:
    print("*** Tournament ***")
    print(f"{len(opponents)} opponents involved")

    try:
        for i, (f1, s1) in enumerate(opponents):
            for j in range(i + 1, len(opponents)):
                f2, s2 = opponents[j]
                print()
                print("* Battle *")
                c1 = f1.create_base()
                c2 = f2.create_base()
                print(c1.describe())
                print(" vs.")
                print(c2.describe())
                print(" now fight!")
                s1.act(c1)
                s2.act(c2)
    except InvalidStrategyError as e:
        print(f"Battle error, aborting tournament: {e}")
