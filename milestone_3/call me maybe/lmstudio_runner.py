"""Esegue la pipeline di function calling contro il server locale di LM Studio.

Variante sperimentale di ``python -m src``: invece del decoding vincolato
locale (llm_sdk + masking dei logit), invia ogni prompt all'endpoint
OpenAI-compatibile di LM Studio e delega il vincolo strutturale al suo
structured output (``response_format: json_schema``).

Uso:
    uv run python lmstudio_runner.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from src.loader import LoaderError, load_functions, load_tests, save_results
from src.schemas import FunctionCallResult, FunctionDefinition

# --------------------------------------------------------------------------
# Configurazione: modifica qui per cambiare server, modello o percorsi.
# --------------------------------------------------------------------------
BASE_URL = "http://127.0.0.1:1234"
MODEL = "qwen2.5-0.5b-instruct-mlx"
TEMPERATURE = 0.0
MAX_TOKENS = 256
TIMEOUT_SECONDS = 120

FUNCTIONS_PATH = Path("data/input/functions_definition.json")
INPUT_PATH = Path("data/input/function_calling_tests.json")
OUTPUT_PATH = Path("data/output/function_calling_results_lmstudio.json")

SYSTEM_PROMPT = (
    "You are a function-calling assistant. Given a user request, pick the "
    "single most appropriate function from the catalog and extract its "
    "arguments from the request. Respond only with the JSON function call."
)
# --------------------------------------------------------------------------


def _catalog_schema(functions: list[FunctionDefinition]) -> dict[str, Any]:
    """Costruisce il JSON Schema che vincola l'output a una chiamata valida."""
    branches: list[dict[str, Any]] = []
    for fn in functions:
        params_schema = {
            "type": "object",
            "properties": {
                pname: {"type": spec.type}
                for pname, spec in fn.parameters.items()
            },
            "required": list(fn.parameters),
            "additionalProperties": False,
        }
        branches.append(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": [fn.name]},
                    "parameters": params_schema,
                },
                "required": ["name", "parameters"],
                "additionalProperties": False,
            }
        )
    return {"anyOf": branches}


def _catalog_text(functions: list[FunctionDefinition]) -> str:
    """Descrizione leggibile del catalogo da includere nel prompt."""
    lines = []
    for fn in functions:
        params = ", ".join(
            f"{pname}: {spec.type}" for pname, spec in fn.parameters.items()
        )
        lines.append(f"- {fn.name}({params}): {fn.description}")
    return "\n".join(lines)


def _chat_completion(
    schema: dict[str, Any], catalog: str, prompt: str
) -> dict[str, Any]:
    """Invia una richiesta a LM Studio e restituisce la chiamata decodificata."""
    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Available functions:\n{catalog}\n\nRequest: {prompt}",
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "function_call",
                "strict": True,
                "schema": schema,
            },
        },
    }
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = json.load(response)
    message = body["choices"][0]["message"]
    # Con i modelli "thinking" la grammatica impedisce di chiudere il blocco
    # di reasoning, quindi LM Studio consegna il JSON in reasoning_content.
    content = message.get("content") or message.get("reasoning_content") or ""
    call = json.loads(content)
    if not isinstance(call, dict):
        raise ValueError(f"unexpected response payload: {content!r}")
    return call


def _validate_call(
    call: dict[str, Any], functions: list[FunctionDefinition]
) -> tuple[str, dict[str, Any]]:
    """Verifica nome e tipi dei parametri rispetto al catalogo."""
    by_name = {fn.name: fn for fn in functions}
    name = call.get("name")
    if name not in by_name:
        raise ValueError(f"unknown function name: {name!r}")
    fn = by_name[name]
    raw_params = call.get("parameters")
    if not isinstance(raw_params, dict):
        raise ValueError("missing 'parameters' object")
    params: dict[str, Any] = {}
    for pname, spec in fn.parameters.items():
        if pname not in raw_params:
            raise ValueError(f"missing parameter {pname!r}")
        value = raw_params[pname]
        if spec.type == "integer":
            params[pname] = int(value)
        elif spec.type == "number":
            params[pname] = float(value)
        elif spec.type == "boolean":
            params[pname] = bool(value)
        else:
            params[pname] = str(value)
    return name, params


def main() -> int:
    """Esegue la pipeline; restituisce il codice di uscita del processo."""
    try:
        functions = load_functions(FUNCTIONS_PATH)
        tests = load_tests(INPUT_PATH)
    except LoaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Caricate {len(functions)} funzione/i e {len(tests)} prompt.")
    print(f"Server: {BASE_URL}  modello: {MODEL!r}")

    schema = _catalog_schema(functions)
    catalog = _catalog_text(functions)

    results: list[FunctionCallResult] = []
    for index, test in enumerate(tests, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(tests)}] {test.prompt!r}")
        try:
            call = _chat_completion(schema, catalog, test.prompt)
            name, params = _validate_call(call, functions)
        except urllib.error.URLError as exc:
            print(
                f"error: cannot reach LM Studio at {BASE_URL}: {exc}",
                file=sys.stderr,
            )
            return 4
        except Exception as exc:
            print(f"  ! fallito: {exc}", file=sys.stderr)
            continue
        elapsed = time.perf_counter() - started
        print(f"  -> {name}({params}) in {elapsed:.1f}s")
        results.append(
            FunctionCallResult(
                prompt=test.prompt, name=name, parameters=params
            )
        )

    try:
        save_results(OUTPUT_PATH, results)
    except OSError as exc:
        print(f"error writing {OUTPUT_PATH}: {exc}", file=sys.stderr)
        return 3

    print(f"Scritti {len(results)} risultato/i in {OUTPUT_PATH}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.", file=sys.stderr)
        raise SystemExit(1)
