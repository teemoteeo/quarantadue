"""Helper di I/O per caricare gli input e scrivere i risultati come JSON."""

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
    """Sollevata quando un file di input manca o è malformato."""


def _read_json(path: Path) -> object:
    """Legge e parsa un file JSON, sollevando LoaderError in caso di errore."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise LoaderError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Invalid JSON in {path}: {exc}") from exc


def load_functions(path: Path) -> list[FunctionDefinition]:
    """Carica e valida il file delle definizioni delle funzioni."""
    payload = _read_json(path)
    try:
        return _FUNCTIONS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid function definitions in {path}: {exc}"
        ) from exc


def load_tests(path: Path) -> list[TestPrompt]:
    """Carica e valida il file dei prompt di test per il function-calling."""
    payload = _read_json(path)
    try:
        return _TESTS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid test prompts in {path}: {exc}"
        ) from exc


def save_results(path: Path, results: Iterable[FunctionCallResult]) -> None:
    """Scrive i risultati come JSON, creando le directory padre se necessario."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in results]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
