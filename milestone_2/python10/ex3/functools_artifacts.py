"""Ancient Library - Functools Treasures."""

import functools
import operator
from collections.abc import Callable
from typing import Any


def spell_reducer(spells: list[int], operation: str) -> int:
    """Reduce spell powers via the chosen operator module function."""
    if not spells:
        return 0
    ops: dict[str, Callable[[int, int], int]] = {
        'add': operator.add,
        'multiply': operator.mul,
        'max': lambda a, b: a if a >= b else b,
        'min': lambda a, b: a if a <= b else b,
    }
    if operation not in ops:
        raise ValueError(f"Unknown operation: {operation}")
    return functools.reduce(ops[operation], spells)


def base_enchantment(power: int, element: str, target: str) -> str:
    """Generic enchantment that describes a cast."""
    elem = element.capitalize()
    return f"{elem} enchantment hits {target} with {power} power"


def partial_enchanter(base_enchantment: Callable) -> dict[str, Callable]:
    """Build 3 specialized enchantments pre-filling power=50 and element."""
    return {
        'fire': functools.partial(base_enchantment, 50, 'fire'),
        'ice': functools.partial(base_enchantment, 50, 'ice'),
        'lightning': functools.partial(base_enchantment, 50, 'lightning'),
    }


@functools.lru_cache(maxsize=None)
def memoized_fibonacci(n: int) -> int:
    """Cached Fibonacci sequence."""
    if n < 2:
        return n
    return memoized_fibonacci(n - 1) + memoized_fibonacci(n - 2)


def spell_dispatcher() -> Callable[[Any], str]:
    """Return single-dispatch function handling int/str/list/unknown."""
    @functools.singledispatch
    def cast(spell: Any) -> str:
        return "Unknown spell type"

    @cast.register(int)
    def _(spell: int) -> str:
        return f"Damage spell: {spell} damage"

    @cast.register(str)
    def _(spell: str) -> str:
        return f"Enchantment: {spell}"

    @cast.register(list)
    def _(spell: list) -> str:
        return f"Multi-cast: {len(spell)} spells"

    return cast


def main() -> None:
    """Demonstrate functools artifacts."""
    print("Testing spell reducer...")
    spells = [10, 20, 30, 40]
    print(f"Sum: {spell_reducer(spells, 'add')}")
    print(f"Product: {spell_reducer(spells, 'multiply')}")
    print(f"Max: {spell_reducer(spells, 'max')}")
    print(f"Min: {spell_reducer(spells, 'min')}")
    print(f"Empty: {spell_reducer([], 'add')}")
    try:
        spell_reducer(spells, 'divide')
    except ValueError as e:
        print(f"Error handled: {e}")

    print("\nTesting partial enchanter...")
    enchanters = partial_enchanter(base_enchantment)
    print(enchanters['fire']('Dragon'))
    print(enchanters['ice']('Goblin'))
    print(enchanters['lightning']('Knight'))

    print("\nTesting memoized fibonacci...")
    print(f"Fib(0): {memoized_fibonacci(0)}")
    print(f"Fib(1): {memoized_fibonacci(1)}")
    print(f"Fib(10): {memoized_fibonacci(10)}")
    print(f"Fib(15): {memoized_fibonacci(15)}")
    print(f"Cache info: {memoized_fibonacci.cache_info()}")

    print("\nTesting spell dispatcher...")
    cast = spell_dispatcher()
    print(cast(42))
    print(cast("fireball"))
    print(cast([1, 2, 3]))
    print(cast(3.14))


if __name__ == "__main__":
    main()
