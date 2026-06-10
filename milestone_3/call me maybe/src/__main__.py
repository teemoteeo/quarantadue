"""punto d'ingresso CLI per ``call me maybe``, il chiamatore di funzioni vincolato."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .decoder import call_for_prompt
from .loader import LoaderError, load_functions, load_tests, save_results
from .model import TokenizedLLM
from .schemas import FunctionCallResult


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """parsa gli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(
        prog="call-me-maybe",
        description=(
            "Resolve natural-language prompts into structured function calls "
            "using a small local LLM with constrained decoding."
        ),
    )
    parser.add_argument(
        "--functions_definition",
        type=Path,
        required=True,
        help="Path to functions_definition.json.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to function_calling_tests.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Where to write function_calling_results.json.",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        help="Hugging Face model id to load via the LLM SDK.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print intermediate decoding decisions to stderr/stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """entrata del programma: ritorna il codice d'uscita del processo."""
    args = _parse_args(argv)
    try:
        functions = load_functions(args.functions_definition)
        tests = load_tests(args.input)
    except LoaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Loaded {len(functions)} function(s) and {len(tests)} prompt(s).")
    print(f"Loading model {args.model!r}...")
    llm = TokenizedLLM(model_name=args.model)
    print(f"Vocab size: {llm.vocab_size}")

    results: list[FunctionCallResult] = []
    for index, test in enumerate(tests, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(tests)}] {test.prompt!r}")
        try:
            name, params = call_for_prompt(
                llm, functions, test.prompt, debug=args.debug
            )
        except Exception as exc:  # noqa: BLE001 - keep the run resilient
            print(f"  ! failed: {exc}", file=sys.stderr)
            name = ""
            params = {}
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

    print(f"Wrote {len(results)} result(s) to {args.output}.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
