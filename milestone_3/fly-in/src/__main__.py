"""CLI entry point for the Fly-in drone simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .graph import ZoneGraph
from .parser import ParserError, parse_map_file
from .pathfinding import compute_shortest_paths
from .simulation import SimulationEngine, TurnLog
from .visual import TerminalVisualizer


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="fly-in",
        description="Multi-drone routing simulation through connected zones.",
    )
    parser.add_argument(
        "map_file",
        type=Path,
        help="Path to the .map file describing the zone network.",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Enable colored terminal visualization.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.map_file.exists():
        print(f"error: map file not found: {args.map_file}", file=sys.stderr)
        return 1

    try:
        map_data = parse_map_file(args.map_file)
    except ParserError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Loaded map: {map_data.nb_drones} drones, "
        f"{len(map_data.zones)} zones, "
        f"{len(map_data.connections)} connections"
    )

    graph = ZoneGraph(map_data)

    try:
        paths = compute_shortest_paths(graph, map_data.nb_drones)
    except ValueError as exc:
        print(f"pathfinding error: {exc}", file=sys.stderr)
        return 3

    engine = SimulationEngine(map_data, paths)
    try:
        log = engine.run()
    except RuntimeError as exc:
        print(f"simulation error: {exc}", file=sys.stderr)
        return 4

    visualizer = TerminalVisualizer(enabled=args.visual)
    visualizer.print_log(log)

    total_cost = _compute_total_cost(graph, paths)
    print("\n--- Stats ---")
    print(f"Total turns:   {len(log)}")
    print(f"Total drones:  {map_data.nb_drones}")
    print(
        "Avg turns/drone: "
        f"{_avg_turns_per_drone(log, map_data.nb_drones):.1f}"
    )
    print(f"Path cost:     {total_cost:.1f}")
    return 0


def _compute_total_cost(graph: ZoneGraph, paths: list[list[str]]) -> float:
    total = 0.0
    for path in paths:
        for i in range(len(path) - 1):
            nxt = path[i + 1]
            ztype = graph.zone_type(nxt)
            if ztype == "restricted":
                total += 2.0
            else:
                total += 1.0
    return total


def _avg_turns_per_drone(log: list[TurnLog], nb_drones: int) -> float:
    first_turn: dict[int, int] = {}
    for turn_log in log:
        for move in turn_log.movements:
            if "-" not in move:
                continue
            parts = move.split("-")
            if not parts[0].startswith("D"):
                continue
            try:
                first_turn.setdefault(int(parts[0][1:]), turn_log.turn)
            except ValueError:
                pass
    if not first_turn:
        return float(len(log))
    return sum(first_turn.values()) / len(first_turn)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
