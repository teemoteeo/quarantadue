#!/usr/bin/env python3

import random


def gen_event() -> tuple:
    players = ["Jafar", "Shaquille", "LaVar", "LeBron", "D'angelo"]
    actions = ["score", "rebound", "pass", "tore ACL", "3points"]

    while True:
        yield (random.choice(players), random.choice(actions))


def consume_event(events: list) -> list:
    while len(events) != 0:
        removed_event = random.choice(events)
        events.remove(removed_event)
        yield removed_event


if __name__ == "__main__":
    print("=== Game Data Stream Processor ===")
    couple = gen_event()

    for i in range(1000):
        player, action = next(couple)
        print(f"Event {i}: Player {player} did action {action}.")

    events = []
    for i in range(10):
        events.append(next(couple))
    print(f"\nBuilt list of 10 events: {events}")
    for event in consume_event(events):
        print(f"Got event: {event}")
        print(f"Remains in list: {events}")
