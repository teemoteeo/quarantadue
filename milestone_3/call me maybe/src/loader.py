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
        functions = _FUNCTIONS_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise LoaderError(
            f"Invalid function definitions in {path}: {exc}"
        ) from exc
    if not functions:
        # Senza funzioni il decoder non ha nulla da scegliere e il fallback
        # (functions[0]) andrebbe in IndexError: meglio fallire pulito qui.
        raise LoaderError(
            f"No function definitions in {path}: catalog is empty"
        )
    return functions


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
    """Scrive i risultati come JSON, creando le directory padre."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in results]
    # Serializzo e codifico PRIMA di aprire il file: se un valore avesse
    # un carattere non codificabile in UTF-8 (es. surrogato isolato)
    # l'errore scatta qui, senza troncare un output valido già scritto.
    encoded = (
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    with path.open("wb") as handle:
        handle.write(encoded)
