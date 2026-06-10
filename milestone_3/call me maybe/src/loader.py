"""aiutini di I/O per caricare gli input e sputare fuori i risultati in JSON."""

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
    """sollevata quando un file di input manca o è scritto male."""


def _read_json(path: Path) -> object:
    """legge e parsa un file JSON, tira su LoaderError se va male."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise LoaderError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoaderError(f"Invalid JSON in {path}: {exc}") from exc


def load_functions(path: Path) -> list[FunctionDefinition]:
    """carica e valida il file con le definizioni delle funzioni."""
    payload = _read_json(path)
    try:
        return _FUNCTIONS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid function definitions in {path}: {exc}"
        ) from exc


def load_tests(path: Path) -> list[TestPrompt]:
    """carica e valida il file dei test di function calling."""
    payload = _read_json(path)
    try:
        return _TESTS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid test prompts in {path}: {exc}"
        ) from exc


def save_results(path: Path, results: Iterable[FunctionCallResult]) -> None:
    """scrive i risultati in JSON, creando le cartelle che servono."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in results]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
