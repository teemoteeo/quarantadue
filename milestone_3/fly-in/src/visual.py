"""Colored terminal visualization for drone simulation output."""

from __future__ import annotations

from .simulation import TurnLog


# ANSI color codes for different zone types and drone states
COLORS: dict[str, str] = {
    "reset": "\033[0m",
    "normal": "\033[37m",       # White
    "restricted": "\033[31m",   # Red
    "priority": "\033[32m",     # Green
    "blocked": "\033[90m",      # Gray
    "start": "\033[36m",        # Cyan
    "end": "\033[33m",          # Yellow
    "drone": "\033[1;34m",      # Bold Blue
    "header": "\033[1;37m",     # Bold White
}


class TerminalVisualizer:
    """Renders a simulation's turn log as colored terminal text.

    When `enabled` is False, output is identical but plain (no ANSI
    codes) — this keeps a single rendering path for both the
    `--visual` and default CLI modes.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        """Create a visualizer; `enabled` toggles ANSI color codes."""
        self._enabled = enabled

    def _color(self, name: str, text: str) -> str:
        """Wrap `text` in the ANSI code for `name`, if coloring is enabled."""
        if not self._enabled:
            return text
        code = COLORS.get(name, "")
        return f"{code}{text}{COLORS['reset']}"

    def render_turn(self, turn: TurnLog) -> str:
        """Render a single turn's movements as one display line."""
        parts = [f"Turn {turn.turn:3d}:"]
        if turn.movements:
            for move in turn.movements:
                parts.append(self._color("drone", move))
        else:
            parts.append("(no movement)")
        return " ".join(parts)

    def render_log(self, log: list[TurnLog]) -> str:
        """Render the full simulation log, one line per turn."""
        lines = [self._color("header", "=== Fly-in Simulation ===")]
        for turn in log:
            lines.append(self.render_turn(turn))
        lines.append(
            self._color(
                "header",
                f"Total turns: {len(log)}",
            )
        )
        return "\n".join(lines)

    def print_log(self, log: list[TurnLog]) -> None:
        """Print the rendered simulation log to stdout."""
        print(self.render_log(log))
