"""I/O helpers for loading inputs and writing results as JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import TypeAdapter, ValidationError

from .schemas import FunctionCallResult, FunctionDefinition, TestPrompt

_FUNCTIONS_ADAPTER: TypeAdapter[list[FunctionDefinition]] = TypeAdapter(
    list[FunctionDefinition]
)
_TESTS_ADAPTER: TypeAdapter[list[TestPrompt]] = TypeAdapter(list[TestPrompt])


class LoaderError(RuntimeError):
    """Raised when an input file is missing or malformed."""


def _read_json(path: Path) -> object:
    """Read and parse a JSON file, raising LoaderError on failure."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise LoaderError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Invalid JSON in {path}: {exc}") from exc


def load_functions(path: Path) -> list[FunctionDefinition]:
    """Load and validate the function definitions file."""
    payload = _read_json(path)
    try:
        return _FUNCTIONS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid function definitions in {path}: {exc}"
        ) from exc


def load_tests(path: Path) -> list[TestPrompt]:
    """Load and validate the function calling tests file."""
    payload = _read_json(path)
    try:
        return _TESTS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid test prompts in {path}: {exc}"
        ) from exc


def save_results(path: Path, results: Iterable[FunctionCallResult]) -> None:
    """Write results to JSON, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in results]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
