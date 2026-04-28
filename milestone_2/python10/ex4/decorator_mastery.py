"""Master's Tower - Decorator Mastery and Class Methods."""

import time
from collections.abc import Callable
from functools import wraps


def spell_timer(func: Callable) -> Callable:
    """Measure and print execution time of a spell."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Casting {func.__name__}...")
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"Spell completed in {elapsed:.3f} seconds")
        return result

    return wrapper


def power_validator(min_power: int) -> Callable:
    """Return a decorator that rejects casts below min_power."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            power = kwargs.get('power')
            if power is None:
                values = [a for a in args if isinstance(a, int)]
                power = values[0] if values else None
            if power is None or power < min_power:
                return "Insufficient power for this spell"
            return func(*args, **kwargs)

        return wrapper

    return decorator


def retry_spell(max_attempts: int) -> Callable:
    """Retry decorator — retry up to max_attempts on exception."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt < max_attempts:
                        print(
                            f"Spell failed, retrying... "
                            f"(attempt {attempt}/{max_attempts})"
                        )
                    else:
                        return (
                            f"Spell casting failed after "
                            f"{max_attempts} attempts"
                        )
            return None

        return wrapper

    return decorator


class MageGuild:
    """A guild of mages."""

    @staticmethod
    def validate_mage_name(name: str) -> bool:
        """Valid if at least 3 chars and only letters/spaces."""
        if not isinstance(name, str) or len(name) < 3:
            return False
        return all(c.isalpha() or c == ' ' for c in name)

    @power_validator(min_power=10)
    def cast_spell(self, spell_name: str, power: int) -> str:
        """Cast a spell when the guild mage has enough power."""
        return f"Successfully cast {spell_name} with {power} power"


@spell_timer
def fireball_spell(target: str) -> str:
    """Slow fireball for timer demo."""
    time.sleep(0.1)
    return f"Fireball cast on {target}!"


def main() -> None:
    """Demonstrate all decorators."""
    print("Testing spell timer...")
    result = fireball_spell("Dragon")
    print(f"Result: {result}")

    print("\nTesting retrying spell...")
    attempts_state = {'count': 0}

    @retry_spell(max_attempts=3)
    def flaky_spell() -> str:
        attempts_state['count'] += 1
        if attempts_state['count'] < 99:
            raise RuntimeError("fizzle")
        return "Spell hit!"

    print(flaky_spell())

    @retry_spell(max_attempts=2)
    def working_spell() -> str:
        return "Waaaaaaagh spelled !"

    print(working_spell())

    print("\nTesting MageGuild...")
    print(MageGuild.validate_mage_name("Alex"))
    print(MageGuild.validate_mage_name("Jo"))
    guild = MageGuild()
    print(guild.cast_spell("Lightning", 15))
    print(guild.cast_spell("Whisper", 5))


if __name__ == "__main__":
    main()
