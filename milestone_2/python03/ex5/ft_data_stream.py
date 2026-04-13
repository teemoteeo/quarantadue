#!/usr/bin/env python3

import random
import typing


def gen_event() -> typing.Generator[tuple, None, None]:
    players = ["Jafar", "Shaquille", "LaVar", "LeBron", "D'angelo"]
    actions = ["score", "rebound", "pass", "tore ACL", "3points"]

    while True:
        yield (random.choice(players), random.choice(actions))


def consume_event(
    events: list
) -> typing.Generator[tuple, None, None]:
    while len(events) != 0:
        removed_event = random.choice(events)
        events.remove(removed_event)
        yield removed_event


if __name__ == "__main__":
    print("=== Game Data Stream Processor ===")
    couple = gen_event()

    for i in range(1000):
        player, action = next(couple)
        print(f"Event {i}: Player {player} did action {action}")

    events = []
    for i in range(10):
        events.append(next(couple))
    print(f"\nBuilt list of 10 events: {events}")
    for event in consume_event(events):
        print(f"Got event from list: {event}")
        print(f"Remains in list: {events}")
