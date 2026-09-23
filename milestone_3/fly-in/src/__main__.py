"""CLI entry point for the Fly-in drone simulation."""

from __future__ import annotations

import argparse
import curses
import sys
from pathlib import Path
from typing import Sequence

from .graph import ZoneGraph
from .parser import MapParser, ParserError
from .pathfinding import PathFinder
from .simulation import RouteScheduler, SimulationEngine, TurnLog
from .tui import TerminalUI
from .visual import TerminalVisualizer


class SimulationReport:
    """Computes and prints the secondary performance metrics for a run."""

    def __init__(
        self,
        finder: PathFinder,
        paths: list[list[str]],
        log: list[TurnLog],
    ) -> None:
        """Bind the report to the pathfinder, drone paths, and turn log."""
        self._finder = finder
        self._paths = paths
        self._log = log

    def total_cost(self) -> float:
        """Sum the weighted movement cost of every drone's planned path."""
        return sum(self._finder.path_cost(p) for p in self._paths)

    def avg_turns_per_drone(self) -> float:
        """Average turn at which each drone reached the end zone."""
        delivered_at: dict[int, int] = {}
        for turn_log in self._log:
            for move in turn_log.movements:
                delivered_at[move.drone_id] = turn_log.turn
        return sum(delivered_at.values()) / len(self._paths)

    def print(self) -> None:
        """Print the `--- Stats ---` block for this simulation run."""
        print("\n--- Stats ---")
        print(f"Total turns:   {len(self._log)}")
        print(f"Total drones:  {len(self._paths)}")
        print(f"Avg turns/drone: {self.avg_turns_per_drone():.1f}")
        print(f"Path cost:     {self.total_cost():.1f}")


class FlyInApplication:
    """Orchestrates parsing, pathfinding, simulation and reporting.

    This is the object-oriented pipeline behind the `fly-in` CLI: given a
    map path and a visualization flag, it produces the process exit code
    documented for the project (0 success, 1 file not found, 2 parse
    error, 3 pathfinding error, 4 simulation error).
    """

    def __init__(
        self,
        map_path: Path,
        *,
        visual: bool,
        tui: bool = False,
    ) -> None:
        """Configure the run: the map, and which views to render."""
        self._map_path = map_path
        self._visual = visual
        self._tui = tui

    def run(self) -> int:
        """Execute the full pipeline and return the process exit code."""
        if not self._map_path.exists():
            print(
                f"error: map file not found: {self._map_path}",
                file=sys.stderr,
            )
            return 1

        try:
            map_data = MapParser().parse(self._map_path)
        except ParserError as exc:
            print(f"parse error: {exc}", file=sys.stderr)
            return 2

        print(
            f"Loaded map: {map_data.nb_drones} drones, "
            f"{len(map_data.zones)} zones, "
            f"{len(map_data.connections)} connections"
        )

        finder = PathFinder(ZoneGraph(map_data))
        try:
            routes = finder.k_shortest_paths(
                map_data.start.name,
                map_data.end.name,
                map_data.nb_drones,
            )
            paths = RouteScheduler(map_data, routes).assign()
        except ValueError as exc:
            print(f"pathfinding error: {exc}", file=sys.stderr)
            return 3

        engine = SimulationEngine(map_data, paths)
        try:
            log = engine.run()
        except RuntimeError as exc:
            print(f"simulation error: {exc}", file=sys.stderr)
            return 4

        print(TerminalVisualizer(
            map_data.zones, enabled=self._visual
        ).render_log(log))
        SimulationReport(finder, paths, log).print()
        if self._tui:
            try:
                TerminalUI(map_data, log).run()
            except curses.error as exc:
                # No tty or no TERM: the run itself still succeeded.
                print(
                    f"warning: cannot open TUI: {exc}", file=sys.stderr
                )
        return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Build and apply the argparse CLI definition for `fly-in`."""
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
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Replay the simulation as an animated terminal UI.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run a :class:`FlyInApplication`."""
    args = _parse_args(argv)
    try:
        return FlyInApplication(
            args.map_file, visual=args.visual, tui=args.tui
        ).run()
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
