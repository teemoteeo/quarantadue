"""Visualizzazione a colori nel terminale dell'output della simulazione."""

from __future__ import annotations

from .schemas import Zone
from .simulation import TurnLog


# ANSI codes. Named constants rather than a dict: a typo is then an
# error at import instead of a silently uncolored string at runtime.
RESET = "\033[0m"
HEADER = "\033[1;37m"   # Bold White

# The subject allows any single word as `color=`, so unknown names fall
# back to the zone-type color rather than being an error.
NAMED = {
    "black": "\033[1;30m",
    "red": "\033[1;31m",
    "green": "\033[1;32m",
    "yellow": "\033[1;33m",
    "blue": "\033[1;34m",
    "magenta": "\033[1;35m",
    "cyan": "\033[1;36m",
    "white": "\033[1;37m",
    "gray": "\033[1;90m",
    "grey": "\033[1;90m",
}

# Fallback when a zone declares no color: its state is still visible.
# Shared with the curses UI, which maps the same words to its own palette.
TYPE_COLOR = {
    "normal": "blue",
    "priority": "green",
    "restricted": "red",
    "blocked": "gray",
}
BY_TYPE = {t: NAMED[c] for t, c in TYPE_COLOR.items()}

MARKER = {"normal": "", "priority": "*", "restricted": "!", "blocked": "x"}


class TerminalVisualizer:
    """Mostra il log dei turni di una simulazione come testo colorato.

    Ogni movimento prende il colore `color=` della zona di arrivo (o,
    se manca, un colore in base al tipo di zona), così una riga del
    turno mostra sia chi si è mosso sia in che tipo di zona è entrato.
    Una legenda elenca ogni zona nel suo colore con un simbolo di
    stato.

    Quando `enabled` è False, l'output è identico ma semplice (senza
    codici ANSI): così c'è un solo modo di disegnare sia per
    `--visual` sia per la modalità normale.
    """

    def __init__(
        self, zones: dict[str, Zone], *, enabled: bool = True
    ) -> None:
        """Crea un visualizzatore per `zones`; `enabled` attiva i colori."""
        self._zones = zones
        self._enabled = enabled

    def _color(self, code: str, text: str) -> str:
        """Avvolge `text` in un `code` ANSI, se i colori sono attivi."""
        return f"{code}{text}{RESET}" if self._enabled else text

    def _zone_code(self, name: str) -> str:
        """Codice ANSI per `name`: il suo `color=`, se no il tipo di zona."""
        # In-flight destinations are `origin-dest` connection names, and
        # the subject forbids dashes inside zone names.
        zone = self._zones[name.rsplit("-", 1)[-1]]
        return NAMED.get(zone.color or "", BY_TYPE[zone.zone_type])

    def _legend(self) -> str:
        """Una riga con ogni zona nel suo colore e i simboli di stato."""
        return "Zones: " + " ".join(
            self._color(
                self._zone_code(name), name + MARKER[zone.zone_type]
            )
            for name, zone in self._zones.items()
        ) + "   (* priority, ! restricted, x blocked)"

    def render_log(self, log: list[TurnLog]) -> str:
        """Disegna il log: intestazione, poi una riga per turno."""
        lines = [
            self._color(HEADER, "=== Fly-in Simulation ==="), self._legend()
        ]
        for turn in log:
            lines.append(" ".join(
                self._color(self._zone_code(m.destination), str(m))
                for m in turn.movements
            ))
        return "\n".join(lines)
