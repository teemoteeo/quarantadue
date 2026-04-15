#!/usr/bin/env python3

from ex0 import CreatureFactory, FlameFactory, AquaFactory


def test_factory(factory: CreatureFactory) -> None:
    print("Testing factory")

    base = factory.create_base()
    evolved = factory.create_evolved()

    print(base.describe())
    print(base.attack())

    print(evolved.describe())
    print(evolved.attack())


def battle(f1: CreatureFactory, f2: CreatureFactory) -> None:
    print("Testing battle")
    
    c1 = f1.create_base()
    c2 = f2.create_base()
    
    print(c1.describe())
    print("VS.")
    print(c2.describe())
    
    print("fight!")
    print(c1.attack())
    print(c2.attack())


if __name__ == "__main__":
    flame_factory = FlameFactory()
    aqua_factory = AquaFactory()

    test_factory(flame_factory)
    print()
    test_factory(aqua_factory)

    print()
    battle(flame_factory, aqua_factory)
