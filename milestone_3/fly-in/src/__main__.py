"""CLI entry point for the Fly-in drone simulation."""

from __future__ import annotations

import argparse
import curses
import sys
from pathlib import Path
from typing import Sequence

from .graph import ZoneGraph
from .parser import MapParser, ParserError
from .pathfinding import FlightPlanner, PathFinder
from .schemas import MapFile
from .simulation import SimulationEngine, TurnLog
from .tui import TerminalUI
from .visual import TerminalVisualizer


class SimulationReport:
    """Computes and prints the secondary performance metrics for a run."""

    def __init__(
        self,
        finder: PathFinder,
        timelines: list[list[str]],
        log: list[TurnLog],
    ) -> None:
        """Bind the report to the pathfinder, drone timelines, and log."""
        self._finder = finder
        self._timelines = timelines
        self._log = log

    def total_cost(self) -> float:
        """Sum the weighted movement cost of every drone's flown route."""
        return sum(
            self._finder.path_cost([
                pos for i, pos in enumerate(timeline)
                if "-" not in pos and (i == 0 or pos != timeline[i - 1])
            ])
            for timeline in self._timelines
        )

    def avg_turns_per_drone(self) -> float:
        """Average turn at which each drone reached the end zone."""
        delivered_at: dict[int, int] = {}
        for turn_log in self._log:
            for move in turn_log.movements:
                delivered_at[move.drone_id] = turn_log.turn
        return sum(delivered_at.values()) / len(self._timelines)

    def print(self) -> None:
        """Print the `--- Stats ---` block for this simulation run."""
        print("\n--- Stats ---")
        print(f"Total turns:   {len(self._log)}")
        print(f"Total drones:  {len(self._timelines)}")
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
            map_data, timelines, log = self.load(self._map_path)
        except ParserError as exc:  # a RuntimeError too: catch it first
            print(f"parse error: {exc}", file=sys.stderr)
            return 2
        except ValueError as exc:
            print(f"pathfinding error: {exc}", file=sys.stderr)
            return 3
        except RuntimeError as exc:
            print(f"simulation error: {exc}", file=sys.stderr)
            return 4

        print(
            f"Loaded map: {map_data.nb_drones} drones, "
            f"{len(map_data.zones)} zones, "
            f"{len(map_data.connections)} connections"
        )
        print(TerminalVisualizer(
            map_data.zones, enabled=self._visual
        ).render_log(log))
        SimulationReport(
            PathFinder(ZoneGraph(map_data)), timelines, log
        ).print()
        if self._tui:
            try:
                TerminalUI(
                    map_data, log,
                    title=self._map_path.name,
                    maps=self.map_choices(),
                    loader=self.load,
                ).run()
            except curses.error as exc:
                # No tty or no TERM: the run itself still succeeded.
                print(
                    f"warning: cannot open TUI: {exc}", file=sys.stderr
                )
        return 0

    @staticmethod
    def load(path: Path) -> tuple[MapFile, list[list[str]], list[TurnLog]]:
        """Parse, plan and simulate one map: the whole pipeline.

        Returns:
            The parsed map, one planned timeline per drone, and the
            simulation's turn log.

        Raises:
            ParserError: The file is missing or invalid.
            ValueError: No path leads from start to end.
            RuntimeError: A plan broke a simulation rule.
        """
        map_data = MapParser().parse(path)
        timelines = FlightPlanner(map_data, ZoneGraph(map_data)).plan()
        return map_data, timelines, SimulationEngine(map_data, timelines).run()

    def map_choices(self) -> dict[str, Path]:
        """Maps the TUI offers to switch to, by display name.

        Every map under `data/maps` when run from the project root,
        otherwise the maps next to the current one.
        """
        root = Path("data/maps")
        if not root.is_dir():
            root = self._map_path.parent
        found = {
            str(p.relative_to(root)): p
            for p in sorted(root.rglob("*"))
            if p.suffix in (".txt", ".map") and p.is_file()
        }
        return found or {self._map_path.name: self._map_path}


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
