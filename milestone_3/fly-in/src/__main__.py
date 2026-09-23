"""Punto d'ingresso da riga di comando della simulazione Fly-in."""

from __future__ import annotations

import argparse
import curses
import sys
from pathlib import Path
from typing import Sequence

from .graph import MOVE_COST
from .parser import MapParser, ParserError
from .pathfinding import FlightPlanner
from .schemas import MapFile, Zone
from .simulation import SimulationEngine, TurnLog
from .tui import TerminalUI
from .visual import TerminalVisualizer


class SimulationReport:
    """Calcola e stampa le statistiche secondarie di una simulazione."""

    def __init__(
        self,
        zones: dict[str, Zone],
        timelines: list[list[str]],
        log: list[TurnLog],
    ) -> None:
        """Collega il report alle zone, alle timeline dei droni e al log."""
        self._zones = zones
        self._timelines = timelines
        self._log = log

    def total_cost(self) -> float:
        """Somma il costo di ogni zona in cui è entrato ogni drone."""
        return sum(
            MOVE_COST[self._zones[pos].zone_type]
            for timeline in self._timelines
            for prev, pos in zip(timeline, timeline[1:])
            if pos != prev and "-" not in pos
        )

    def avg_turns_per_drone(self) -> float:
        """Turno medio in cui i droni hanno raggiunto la zona finale."""
        delivered_at: dict[int, int] = {}
        for turn_log in self._log:
            for move in turn_log.movements:
                delivered_at[move.drone_id] = turn_log.turn
        return sum(delivered_at.values()) / len(self._timelines)

    def print(self) -> None:
        """Stampa il blocco `--- Stats ---` di questa simulazione."""
        print("\n--- Stats ---")
        print(f"Total turns:   {len(self._log)}")
        print(f"Total drones:  {len(self._timelines)}")
        print(f"Avg turns/drone: {self.avg_turns_per_drone():.1f}")
        print(f"Path cost:     {self.total_cost():.1f}")


class FlyInApplication:
    """Coordina lettura della mappa, percorsi, simulazione e report.

    Questa è la pipeline a oggetti dietro il comando `fly-in`: dati il
    percorso di una mappa e l'opzione di visualizzazione, restituisce il
    codice di uscita previsto dal progetto (0 successo, 1 file non
    trovato, 2 errore di parsing, 3 errore nei percorsi, 4 errore di
    simulazione).
    """

    def __init__(
        self,
        map_path: Path,
        *,
        visual: bool,
        tui: bool = False,
    ) -> None:
        """Prepara l'esecuzione: la mappa e quali viste mostrare."""
        self._map_path = map_path
        self._visual = visual
        self._tui = tui

    def run(self) -> int:
        """Esegue tutta la pipeline e restituisce il codice di uscita."""
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
        SimulationReport(map_data.zones, timelines, log).print()
        if self._tui:
            try:
                TerminalUI(
                    map_data, log,
                    path=self._map_path,
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
        """Legge, pianifica e simula una mappa: tutta la pipeline.

        Returns:
            La mappa letta, una timeline pianificata per ogni drone e il
            log dei turni della simulazione.

        Raises:
            ParserError: Il file manca o non è valido.
            ValueError: Nessun percorso porta dall'inizio alla fine.
            RuntimeError: Un piano ha violato una regola della simulazione.
        """
        map_data = MapParser().parse(path)
        timelines = FlightPlanner(map_data).plan()
        return map_data, timelines, SimulationEngine(map_data, timelines).run()

    def map_choices(self) -> dict[str, Path]:
        """Mappe tra cui la TUI permette di scegliere, per nome.

        Tutte le mappe in `data/maps` se lanciato dalla radice del progetto,
        altrimenti le mappe nella stessa cartella di quella corrente.
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
    """Definisce e legge gli argomenti da riga di comando di `fly-in`."""
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
    """Legge gli argomenti ed esegue una :class:`FlyInApplication`."""
    args = _parse_args(argv)
    try:
        return FlyInApplication(
            args.map_file, visual=args.visual, tui=args.tui
        ).run()
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
