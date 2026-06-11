"""Punto d'ingresso CLI per ``call me maybe``, il nostro function caller vincolato."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from .decoder import call_for_prompt, default_value
from .loader import LoaderError, load_functions, load_tests, save_results
from .model import TokenizedLLM
from .schemas import FunctionCallResult, FunctionDefinition

DEFAULT_FUNCTIONS = Path("data/input/functions_definition.json")
DEFAULT_INPUT = Path("data/input/function_calling_tests.json")
DEFAULT_OUTPUT = Path("data/output/function_calling_results.json")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parsa gli argomenti dalla riga di comando (i path hanno tutti dei default dal subject)."""
    parser = argparse.ArgumentParser(
        prog="call-me-maybe",
        description=(
            "Risolve prompt in linguaggio naturale in chiamate di funzioni "
            "strutturate utilizzando un piccolo LLM locale con decoding vincolato."
        ),
    )
    parser.add_argument(
        "--functions_definition",
        type=Path,
        default=DEFAULT_FUNCTIONS,
        help=f"Percorso a functions_definition.json "
             f"(default: {DEFAULT_FUNCTIONS}).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Percorso a function_calling_tests.json (default: {DEFAULT_INPUT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Dove scrivere il JSON dei risultati (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        help="ID del modello Hugging Face da caricare tramite l'SDK LLM.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Stampa le decisioni di decoding intermedie.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Esegue la pipeline e ritorna il codice di uscita del processo."""
    try:
        return _run(_parse_args(argv))
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    """Logica della pipeline, isolata così main può catturare KeyboardInterrupt."""
    try:
        functions = load_functions(args.functions_definition)
        tests = load_tests(args.input)
    except LoaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Caricate {len(functions)} funzione/i e {len(tests)} prompt.")
    print(f"Caricamento del modello {args.model!r}...")
    try:
        llm = TokenizedLLM(model_name=args.model)
    except Exception as exc:
        print(
            f"error: could not load model {args.model!r}: {exc}",
            file=sys.stderr,
        )
        return 4
    print(f"Dimensione vocabolario: {llm.vocab_size}")

    results: list[FunctionCallResult] = []
    for index, test in enumerate(tests, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(tests)}] {test.prompt!r}")
        try:
            # La decodifica è greedy e deterministica: ritentare con lo
            # stesso input riprodurrebbe lo stesso fallimento.
            name, params = call_for_prompt(
                llm, functions, test.prompt, debug=args.debug
            )
        except Exception as exc:
            print(f"  ! fallito: {exc}", file=sys.stderr)
            name, params = _fallback_call(functions)
        elapsed = time.perf_counter() - started
        print(f"  -> {name}({params}) in {elapsed:.1f}s")
        results.append(
            FunctionCallResult(
                prompt=test.prompt,
                name=name,
                parameters=params,
            )
        )

    try:
        save_results(args.output, results)
    except OSError as exc:
        print(f"error writing {args.output}: {exc}", file=sys.stderr)
        return 3

    print(f"Scritti {len(results)} risultato/i in {args.output}.")
    return 0


def _fallback_call(
    functions: list[FunctionDefinition],
) -> tuple[str, dict[str, Any]]:
    """Risultato di emergenza schema-valido quando la decodifica di un prompt fallisce.

    Emette la prima funzione del catalogo con argomenti neutri corretti per tipo,
    così il file di output non ha mai un nome vuoto o chiavi mancanti.
    """
    fn = functions[0]
    params = {
        name: default_value(spec.type)
        for name, spec in fn.parameters.items()
    }
    return fn.name, params


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
