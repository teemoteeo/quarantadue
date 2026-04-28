"""Higher Realm - Functions Operating on Functions."""

from collections.abc import Callable


def spell_combiner(spell1: Callable, spell2: Callable) -> Callable:
    """Return function casting both spells; returns tuple of results."""
    if not (callable(spell1) and callable(spell2)):
        raise TypeError("spell_combiner expects two callables")

    def combined(target: str, power: int) -> tuple:
        return spell1(target, power), spell2(target, power)

    return combined


def power_amplifier(base_spell: Callable, multiplier: int) -> Callable:
    """Return a new spell that multiplies the power before casting."""
    if not callable(base_spell):
        raise TypeError("base_spell must be callable")

    def amplified(target: str, power: int) -> str:
        return base_spell(target, power * multiplier)

    return amplified


def conditional_caster(condition: Callable, spell: Callable) -> Callable:
    """Cast spell only if condition returns True for the same arguments."""
    if not (callable(condition) and callable(spell)):
        raise TypeError("condition and spell must be callables")

    def guarded(target: str, power: int) -> str:
        if condition(target, power):
            return spell(target, power)
        return "Spell fizzled"

    return guarded


def spell_sequence(spells: list[Callable]) -> Callable:
    """Return a function that casts all spells in order, returns list."""
    for s in spells:
        if not callable(s):
            raise TypeError("all elements of spells must be callable")

    def sequence(target: str, power: int) -> list:
        return [s(target, power) for s in spells]

    return sequence


def fireball(target: str, power: int) -> str:
    """Damage spell."""
    return f"Fireball hits {target} for {power} damage"


def heal(target: str, power: int) -> str:
    """Healing spell."""
    return f"Heal restores {target} for {power} HP"


def shield(target: str, power: int) -> str:
    """Shielding spell."""
    return f"Shield protects {target} with {power} armor"


def main() -> None:
    """Demonstrate all higher-order function spells."""
    print("Testing spell combiner...")
    combined = spell_combiner(fireball, heal)
    result = combined("Dragon", 20)
    print(f"Combined spell result: {result[0]}, {result[1]}")

    print("\nTesting power amplifier...")
    mega_fireball = power_amplifier(fireball, 3)
    print(f"Original: {fireball('Goblin', 10)}")
    print(f"Amplified: {mega_fireball('Goblin', 10)}")

    print("\nTesting conditional caster...")
    strong_enough = conditional_caster(
        lambda target, power: power >= 15, fireball,
    )
    print(f"Power 20: {strong_enough('Orc', 20)}")
    print(f"Power 5: {strong_enough('Orc', 5)}")

    print("\nTesting spell sequence...")
    combo = spell_sequence([fireball, heal, shield])
    for line in combo("Wizard", 12):
        print(line)


if __name__ == "__main__":
    main()
