#!/usr/bin/env python3

import random


if __name__ == "__main__":
    print("=== Game Data Alchemist ===")
    players = ["Jafar", "Shaquille", "LaVar", "LeBron",
               "D'angelo", "kevin", "kobe", "ray"]
    print(f"\nInitial list of players: {players}")
    to_capitalize = [player.capitalize() for player in players]
    print(f"New list with all names capitalized: {to_capitalize}")
    already_capital = [player for player in players
                       if player[0] == player[0].upper()]
    print(f"New list of capitalized names only: {already_capital}")

    scorebook = {player: random.randint(0, 1000) for player in to_capitalize}
    print(f"\nScore dict: {scorebook}")
    media = (sum(scorebook.values())/len(scorebook))
    print(f"Score average is {media:.2f}")
    high_scores = {player: score for player, score in scorebook.items() if score > media}
    print(f"High scores: {high_scores}")
