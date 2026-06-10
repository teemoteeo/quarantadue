"""CLI entry point for ``call me maybe``, the constrained function caller."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from .decoder import call_for_prompt
from .loader import LoaderError, load_functions, load_tests, save_results
from .model import TokenizedLLM
from .schemas import FunctionCallResult, FunctionDefinition

DEFAULT_FUNCTIONS = Path("data/input/functions_definition.json")
DEFAULT_INPUT = Path("data/input/function_calling_tests.json")
DEFAULT_OUTPUT = Path("data/output/function_calling_results.json")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments (all paths have subject defaults)."""
    parser = argparse.ArgumentParser(
        prog="call-me-maybe",
        description=(
            "Resolve natural-language prompts into structured function "
            "calls using a small local LLM with constrained decoding."
        ),
    )
    parser.add_argument(
        "--functions_definition",
        type=Path,
        default=DEFAULT_FUNCTIONS,
        help=f"Path to functions_definition.json "
             f"(default: {DEFAULT_FUNCTIONS}).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to function_calling_tests.json (default: {DEFAULT_INPUT}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the results JSON (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        help="Hugging Face model id to load via the LLM SDK.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print intermediate decoding decisions.",
    )
    return parser.parse_args(argv)


def _resolve_call(
    llm: TokenizedLLM,
    functions: list[FunctionDefinition],
    prompt: str,
    *,
    debug: bool,
) -> tuple[str, dict[str, Any]]:
    """Resolve one prompt, retrying once before giving up."""
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return call_for_prompt(llm, functions, prompt, debug=debug)
        except Exception as exc:
            last_error = exc
            if debug:
                print(
                    f"[debug] attempt {attempt + 1} failed: {exc}",
                    file=sys.stderr,
                )
    raise RuntimeError(f"decoding failed after retry: {last_error}")


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline; return the process exit code."""
    args = _parse_args(argv)
    try:
        functions = load_functions(args.functions_definition)
        tests = load_tests(args.input)
    except LoaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Loaded {len(functions)} function(s) and {len(tests)} prompt(s).")
    print(f"Loading model {args.model!r}...")
    try:
        llm = TokenizedLLM(model_name=args.model)
    except Exception as exc:
        print(
            f"error: could not load model {args.model!r}: {exc}",
            file=sys.stderr,
        )
        return 4
    print(f"Vocab size: {llm.vocab_size}")

    results: list[FunctionCallResult] = []
    for index, test in enumerate(tests, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(tests)}] {test.prompt!r}")
        try:
            name, params = _resolve_call(
                llm, functions, test.prompt, debug=args.debug
            )
        except Exception as exc:
            print(f"  ! failed: {exc}", file=sys.stderr)
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

    print(f"Wrote {len(results)} result(s) to {args.output}.")
    return 0


def _fallback_call(
    functions: list[FunctionDefinition],
) -> tuple[str, dict[str, Any]]:
    """Last-resort schema-valid result when decoding failed twice.

    Emits the first catalog function with type-correct neutral arguments
    so the output file never contains an empty name or missing keys.
    """
    defaults: dict[str, Any] = {
        "number": 0.0,
        "integer": 0,
        "string": "",
        "boolean": False,
    }
    fn = functions[0]
    params = {
        name: defaults[spec.type] for name, spec in fn.parameters.items()
    }
    return fn.name, params


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
