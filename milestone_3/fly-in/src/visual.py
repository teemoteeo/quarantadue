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
    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def _color(self, name: str, text: str) -> str:
        if not self._enabled:
            return text
        code = COLORS.get(name, "")
        return f"{code}{text}{COLORS['reset']}"

    def render_turn(self, turn: TurnLog) -> str:
        parts = [f"Turn {turn.turn:3d}:"]
        if turn.movements:
            for move in turn.movements:
                parts.append(self._color("drone", move))
        else:
            parts.append("(no movement)")
        return " ".join(parts)

    def render_log(self, log: list[TurnLog]) -> str:
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
        print(self.render_log(log))
