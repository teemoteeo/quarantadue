"""Lambda Sanctum - Mastering Anonymous Functions."""


def artifact_sorter(artifacts: list[dict]) -> list[dict]:
    """Sort magical artifacts by power (descending) using lambda."""
    return sorted(artifacts, key=lambda a: a['power'], reverse=True)


def power_filter(mages: list[dict], min_power: int) -> list[dict]:
    """Filter mages whose power is >= min_power."""
    return list(filter(lambda m: m['power'] >= min_power, mages))


def spell_transformer(spells: list[str]) -> list[str]:
    """Add '* ' prefix and ' *' suffix to each spell name."""
    return list(map(lambda s: f"* {s} *", spells))


def mage_stats(mages: list[dict]) -> dict:
    """Compute max, min, and average power of a mage list."""
    if not mages:
        return {'max_power': 0, 'min_power': 0, 'avg_power': 0.0}
    max_power = max(mages, key=lambda m: m['power'])['power']
    min_power = min(mages, key=lambda m: m['power'])['power']
    avg_power = round(sum(map(lambda m: m['power'], mages)) / len(mages), 2)
    return {
        'max_power': max_power,
        'min_power': min_power,
        'avg_power': avg_power,
    }


def main() -> None:
    """Demonstrate all lambda spells."""
    artifacts = [
        {'name': 'Crystal Orb', 'power': 85, 'type': 'focus'},
        {'name': 'Fire Staff', 'power': 92, 'type': 'weapon'},
        {'name': 'Ice Wand', 'power': 70, 'type': 'weapon'},
        {'name': 'Storm Crown', 'power': 110, 'type': 'relic'},
    ]
    mages = [
        {'name': 'Alex', 'power': 65, 'element': 'fire'},
        {'name': 'Jordan', 'power': 88, 'element': 'ice'},
        {'name': 'Riley', 'power': 75, 'element': 'lightning'},
        {'name': 'Sage', 'power': 95, 'element': 'shadow'},
    ]
    spells = ['fireball', 'heal', 'shield']

    print("Testing artifact sorter...")
    sorted_artifacts = artifact_sorter(artifacts)
    for i in range(len(sorted_artifacts) - 1):
        cur = sorted_artifacts[i]
        nxt = sorted_artifacts[i + 1]
        print(
            f"{cur['name']} ({cur['power']} power) comes before "
            f"{nxt['name']} ({nxt['power']} power)"
        )

    print("\nTesting power filter (min_power=75)...")
    for mage in power_filter(mages, 75):
        print(f"{mage['name']} ({mage['power']} power, {mage['element']})")

    print("\nTesting spell transformer...")
    print(" ".join(spell_transformer(spells)))

    print("\nTesting mage stats...")
    stats = mage_stats(mages)
    print(f"Max power: {stats['max_power']}")
    print(f"Min power: {stats['min_power']}")
    print(f"Avg power: {stats['avg_power']}")


if __name__ == "__main__":
    main()
