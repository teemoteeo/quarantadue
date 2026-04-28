#!/usr/bin/env python3

from ex0.creatures import Creature
from ex0.factory import CreatureFactory
from .healing import Sproutling, Bloomelle
from .transforming import Shiftling, Morphagon


class HealingCreatureFactory(CreatureFactory):
    def create_base(self) -> Creature:
        return Sproutling()

    def create_evolved(self) -> Creature:
        return Bloomelle()


class TransformCreatureFactory(CreatureFactory):
    def create_base(self) -> Creature:
        return Shiftling()

    def create_evolved(self) -> Creature:
        return Morphagon()
