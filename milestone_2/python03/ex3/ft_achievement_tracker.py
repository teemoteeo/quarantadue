#!/usr/bin/env python3

import random


def gen_player_achievements() -> set[str]:
    """generate a random set of achievements for one player."""
    achievements = [
        'Crafting Genius',
        'World Savior',
        'Master Explorer',
        'Collector Supreme',
        'Untouchable',
        'Boss Slayer',
        'Strategist',
        'Speed Runner',
        'Survivor',
        'Treasure Hunter',
        'First Steps',
        'Sharp Mind',
        'Hidden Path Finder',
        'Unstoppable',
    ]
    count = random.randint(5, 9)
    return set(random.sample(achievements, count))


if __name__ == "__main__":
    random.seed(42)
    print("=== Achievement Tracker System ===")

    achievement_pool = {
        'Crafting Genius',
        'World Savior',
        'Master Explorer',
        'Collector Supreme',
        'Untouchable',
        'Boss Slayer',
        'Strategist',
        'Speed Runner',
        'Survivor',
        'Treasure Hunter',
        'First Steps',
        'Sharp Mind',
        'Hidden Path Finder',
        'Unstoppable',
    }
    players = {
        'Alice': gen_player_achievements(),
        'Bob': gen_player_achievements(),
        'Charlie': gen_player_achievements(),
        'Dylan': gen_player_achievements(),
    }

    for name, player_achievements in players.items():
        print(f"Player {name}: {player_achievements}")

    all_achievements: set[str] = set()
    for player_achievements in players.values():
        all_achievements = all_achievements.union(player_achievements)
    print(f"All distinct achievements: {all_achievements}")

    common_achievements = achievement_pool.copy()
    for player_achievements in players.values():
        common_achievements = common_achievements.intersection(
                player_achievements
                )
    print(f"Common achievements: {common_achievements}")

    for name, player_achievements in players.items():
        other_achievements: set[str] = set()
        for other_name, other_set in players.items():
            if other_name != name:
                other_achievements = other_achievements.union(other_set)
        print(f"Only {name} has: "
              f"{player_achievements.difference(other_achievements)}")

    for name, player_achievements in players.items():
        print(f"{name} is missing: "
              f"{achievement_pool.difference(player_achievements)}")
