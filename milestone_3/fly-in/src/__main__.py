"""CLI entry point for the Fly-in drone simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .graph import ZoneGraph
from .parser import MapParser, ParserError
from .pathfinding import PathFinder
from .simulation import SimulationEngine, TurnLog
from .visual import TerminalVisualizer


class SimulationReport:
    """Computes and prints the secondary performance metrics for a run."""

    def __init__(
        self,
        graph: ZoneGraph,
        paths: list[list[str]],
        log: list[TurnLog],
    ) -> None:
        """Bind the report to the graph, drone paths, and turn log to score."""
        self._graph = graph
        self._paths = paths
        self._log = log

    def total_cost(self) -> float:
        """Sum the weighted movement cost of every drone's planned path."""
        total = 0.0
        for path in self._paths:
            for i in range(len(path) - 1):
                zone_type = self._graph.zone_type(path[i + 1])
                total += 2.0 if zone_type == "restricted" else 1.0
        return total

    def avg_turns_per_drone(self, nb_drones: int) -> float:
        """Average turn number at which each drone made its first move."""
        if nb_drones <= 0:
            return 0.0
        first_turn: dict[int, int] = {}
        for turn_log in self._log:
            for move in turn_log.movements:
                drone_id = self._extract_drone_id(move)
                if drone_id is not None:
                    first_turn.setdefault(drone_id, turn_log.turn)
        if not first_turn:
            return float(len(self._log))
        return sum(first_turn.values()) / nb_drones

    @staticmethod
    def _extract_drone_id(move: str) -> int | None:
        """Parse the numeric drone id out of a 'D<id>-<dest>' token."""
        if "-" not in move:
            return None
        token = move.split("-", 1)[0]
        if not token.startswith("D"):
            return None
        try:
            return int(token[1:])
        except ValueError:
            return None

    def print(self, nb_drones: int) -> None:
        """Print the `--- Stats ---` block for this simulation run."""
        print("\n--- Stats ---")
        print(f"Total turns:   {len(self._log)}")
        print(f"Total drones:  {nb_drones}")
        print(f"Avg turns/drone: {self.avg_turns_per_drone(nb_drones):.1f}")
        print(f"Path cost:     {self.total_cost():.1f}")


class FlyInApplication:
    """Orchestrates parsing, pathfinding, simulation and reporting.

    This is the object-oriented pipeline behind the `fly-in` CLI: given a
    map path and a visualization flag, it produces the process exit code
    documented for the project (0 success, 1 file not found, 2 parse
    error, 3 pathfinding error, 4 simulation error).
    """

    def __init__(self, map_path: Path, *, visual: bool) -> None:
        """Configure the run: which map to load and whether to colorize."""
        self._map_path = map_path
        self._visual = visual

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

        graph = ZoneGraph(map_data)
        finder = PathFinder(graph)
        try:
            paths = finder.compute_drone_paths(map_data.nb_drones)
        except ValueError as exc:
            print(f"pathfinding error: {exc}", file=sys.stderr)
            return 3

        engine = SimulationEngine(map_data, paths)
        try:
            log = engine.run()
        except RuntimeError as exc:
            print(f"simulation error: {exc}", file=sys.stderr)
            return 4

        TerminalVisualizer(enabled=self._visual).print_log(log)
        SimulationReport(graph, paths, log).print(map_data.nb_drones)
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run a :class:`FlyInApplication`."""
    args = _parse_args(argv)
    return FlyInApplication(args.map_file, visual=args.visual).run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
