"""Constrained-decoding primitives that extract structured function calls.

The decoder works at token level. At each generation step it:

1. Asks the model for next-token logits.
2. Computes the set of token ids whose literal text keeps the accumulated
   output on a path that is still legal under the active grammar
   (function-name choice / JSON number / JSON string / boolean literal).
   For the string and number grammars this set is a precomputed numpy
   boolean mask per DFA state: legality of ``accumulated + token`` only
   depends on the DFA state reached after ``accumulated``, so each state's
   mask is built once over the whole vocabulary at startup.
3. Masks every other logit to ``-inf`` (numerically ``-1e30``).
4. Takes the highest-scoring legal token, appends it, and loops.

The grammar is split into small DFAs, one per state of interest; only the
*values* the LLM is responsible for are generated, while the structural
JSON scaffolding is injected verbatim.

Termination is guaranteed by construction: near the step budget the string
grammar only admits tokens that close the value, so every decode either
completes or raises -- there is no heuristic recovery path.
"""

from __future__ import annotations

import math
import weakref
from typing import Any, Iterable

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from .model import TokenizedLLM
from .schemas import FunctionDefinition, ParameterSpec

NEG_INF: float = -1e30

BoolMask = npt.NDArray[np.bool_]

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DIGITS = frozenset("0123456789")
_SIMPLE_ESCAPES = frozenset('"\\/bfnrt')

# Once a string value has been generated for this many steps short of the
# budget, the decoder only allows tokens that close the string.
_STRING_CLOSE_WINDOW: int = 8


def _argmax_masked(
    logits: list[float], valid_ids: Iterable[int]
) -> int | None:
    """Return the id in ``valid_ids`` with the highest logit, or None."""
    best_id: int | None = None
    best_logit = -math.inf
    for tid in valid_ids:
        score = logits[tid]
        if score > best_logit:
            best_logit = score
            best_id = tid
    return best_id


def _argmax_masked_np(logits: list[float], mask: BoolMask) -> int | None:
    """Return the highest-logit token id allowed by ``mask``, or None.

    The logits vector may be longer than the base vocabulary (padded
    embedding rows); padded ids are never legal, so both arrays are
    clipped to the shorter length.
    """
    arr = np.asarray(logits, dtype=np.float64)
    k = min(arr.shape[0], mask.shape[0])
    valid = mask[:k]
    if not valid.any():
        return None
    return int(np.where(valid, arr[:k], NEG_INF).argmax())


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def build_context(functions: list[FunctionDefinition], prompt: str) -> str:
    """Build the textual prompt that frames the function-calling task."""
    lines: list[str] = [
        "You are a function-calling assistant. Pick the single best function "
        "from the catalog below and fill in its arguments based on the "
        "user's request. Only reply with one JSON object of the form "
        '{"name": "<fn>", "parameters": {...}}.',
        "",
        "Catalog:",
    ]
    for fn in functions:
        params_str = ", ".join(
            f"{name}: {spec.type}" for name, spec in fn.parameters.items()
        )
        lines.append(f"- {fn.name}({params_str}): {fn.description}")
    lines.append("")
    lines.append(f"User request: {prompt}")
    lines.append('Function call: {"name": "')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Function-name selection (constrained to the catalog)
# ---------------------------------------------------------------------------


def choose_function_name(
    llm: TokenizedLLM,
    input_ids: list[int],
    function_names: list[str],
    *,
    max_steps: int = 32,
) -> tuple[str, list[int]]:
    """Decode exactly one of ``function_names`` by masking everything else.

    When the accumulated text is both a complete catalog name and a strict
    prefix of a longer one (e.g. ``fn_add`` vs ``fn_add_numbers``), the
    model's own logits arbitrate: the closing-quote token competes against
    the best continuation token.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    quote_ids = [tid for tid, text in llm.clean_vocab if text == '"']
    for _ in range(max_steps):
        is_complete = accumulated in function_names
        has_longer = any(
            name != accumulated and name.startswith(accumulated)
            for name in function_names
        )
        if is_complete and not has_longer:
            return accumulated, ids
        valid: list[int] = []
        for tid, text in llm.clean_vocab:
            candidate = accumulated + text
            for target in function_names:
                if target.startswith(candidate):
                    valid.append(tid)
                    break
        if is_complete:
            logits = llm.get_logits(ids)
            best_cont = _argmax_masked(logits, valid) if valid else None
            best_stop = _argmax_masked(logits, quote_ids)
            if best_cont is None or (
                best_stop is not None
                and logits[best_stop] >= logits[best_cont]
            ):
                return accumulated, ids
            accumulated += id_text[best_cont]
            ids.append(best_cont)
            continue
        if not valid:
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked(logits, valid)
        if best is None:
            break
        accumulated += id_text[best]
        ids.append(best)
    if accumulated in function_names:
        return accumulated, ids
    raise RuntimeError(
        f"Constrained decoding failed to reach a function name "
        f"(accumulated={accumulated!r})"
    )


# ---------------------------------------------------------------------------
# JSON number grammar
# ---------------------------------------------------------------------------


_NUMBER_STATES: tuple[str, ...] = ("start", "sign", "int", "dot", "frac")


def _step_number(
    state: str,
    text: str,
    terminator: str,
    *,
    allow_fraction: bool = True,
) -> str | None:
    """Advance the ``number<terminator>`` DFA from ``state`` over ``text``.

    Returns the end state (``"done"`` once the terminator is consumed)
    or None when the text is illegal from that state. With
    ``allow_fraction=False`` the decimal point is rejected, so integer
    parameters can never silently truncate a fractional decode.
    """
    for ch in text:
        if state == "done":
            return None
        if state == "start":
            if ch == "-":
                state = "sign"
            elif ch in _DIGITS:
                state = "int"
            else:
                return None
        elif state == "sign":
            if ch in _DIGITS:
                state = "int"
            else:
                return None
        elif state == "int":
            if ch in _DIGITS:
                pass
            elif ch == "." and allow_fraction:
                state = "dot"
            elif ch == terminator:
                state = "done"
            else:
                return None
        elif state == "dot":
            if ch in _DIGITS:
                state = "frac"
            else:
                return None
        elif state == "frac":
            if ch in _DIGITS:
                pass
            elif ch == terminator:
                state = "done"
            else:
                return None
    return state


def generate_number(
    llm: TokenizedLLM,
    input_ids: list[int],
    terminator: str,
    *,
    allow_fraction: bool = True,
    max_steps: int = 24,
) -> tuple[str, list[int]]:
    """Decode a JSON number up to (and consuming) ``terminator``.

    Returns the number text without the terminator. Note: the terminator
    token has been appended to the returned ids, so callers must not add
    a separator of their own afterwards.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm).number(terminator, allow_fraction)
    state = "start"
    for _ in range(max_steps):
        if state == "done":
            return accumulated[:-1], ids
        mask = masks[state]
        if not mask.any():
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked_np(logits, mask)
        if best is None:
            break
        text = id_text[best]
        nxt = _step_number(
            state, text, terminator, allow_fraction=allow_fraction
        )
        if nxt is None:  # unreachable: token came from the valid mask
            break
        state = nxt
        accumulated += text
        ids.append(best)
    if state == "done":
        return accumulated[:-1], ids
    # The body alone may already be a valid number (budget ran out before
    # the terminator token was emitted).
    body_check = _step_number(
        "start",
        accumulated + terminator,
        terminator,
        allow_fraction=allow_fraction,
    )
    if body_check == "done":
        return accumulated, ids
    raise RuntimeError(
        f"Constrained decoding failed to produce a number "
        f"(accumulated={accumulated!r})"
    )


# ---------------------------------------------------------------------------
# JSON string grammar
# ---------------------------------------------------------------------------


_STRING_STATES: tuple[str, ...] = (
    "body", "escape", "uhex0", "uhex1", "uhex2", "uhex3"
)
_UHEX_NEXT = {
    "uhex0": "uhex1",
    "uhex1": "uhex2",
    "uhex2": "uhex3",
    "uhex3": "body",
}


def _step_string(state: str, text: str) -> str | None:
    """Advance the JSON-string DFA from ``state`` over ``text``.

    Returns the end state (``"done"`` once the unescaped closing quote
    is consumed) or None when the text is illegal from that state.
    """
    for ch in text:
        if state == "done":
            return None
        if state == "body":
            if ch == '"':
                state = "done"
            elif ch == "\\":
                state = "escape"
            elif ord(ch) < 0x20:
                return None
        elif state == "escape":
            if ch in _SIMPLE_ESCAPES:
                state = "body"
            elif ch == "u":
                state = "uhex0"
            else:
                return None
        else:  # uhex0..uhex3
            if ch not in _HEX_DIGITS:
                return None
            state = _UHEX_NEXT[state]
    return state


# ---------------------------------------------------------------------------
# Precomputed per-state vocabulary masks
# ---------------------------------------------------------------------------


class GrammarMasks:
    """Numpy boolean masks over the vocabulary, one per DFA state.

    Because the grammars are DFAs, the legality of ``accumulated +
    token_text`` depends only on the state reached after ``accumulated``
    (``step(step(s0, a), b) == step(s0, a + b)``). Each state therefore
    classifies every vocabulary token once, up front; a decode step is
    then a dict lookup plus a vectorized argmax instead of a Python scan
    over the whole vocabulary.
    """

    def __init__(self, llm: TokenizedLLM) -> None:
        self._llm = llm
        size = llm.vocab_size
        self.string_valid: dict[str, BoolMask] = {
            state: np.zeros(size, dtype=bool) for state in _STRING_STATES
        }
        self.string_closing: dict[str, BoolMask] = {
            state: np.zeros(size, dtype=bool) for state in _STRING_STATES
        }
        self.bare_quote: BoolMask = np.zeros(size, dtype=bool)
        for tid, text in llm.clean_vocab:
            if text == '"':
                self.bare_quote[tid] = True
            for state in _STRING_STATES:
                end = _step_string(state, text)
                if end is None:
                    continue
                self.string_valid[state][tid] = True
                if end == "done":
                    self.string_closing[state][tid] = True
        # Number masks are built lazily: only the terminators actually
        # used ("," and "}") ever get a table.
        self._number: dict[tuple[str, bool], dict[str, BoolMask]] = {}

    def number(
        self, terminator: str, allow_fraction: bool
    ) -> dict[str, BoolMask]:
        """Return (building on first use) the masks for a number grammar."""
        key = (terminator, allow_fraction)
        masks = self._number.get(key)
        if masks is None:
            size = self._llm.vocab_size
            masks = {
                state: np.zeros(size, dtype=bool)
                for state in _NUMBER_STATES
            }
            for tid, text in self._llm.clean_vocab:
                for state in _NUMBER_STATES:
                    end = _step_number(
                        state,
                        text,
                        terminator,
                        allow_fraction=allow_fraction,
                    )
                    if end is not None:
                        masks[state][tid] = True
            self._number[key] = masks
        return masks


_MASK_CACHE: weakref.WeakKeyDictionary[TokenizedLLM, GrammarMasks] = (
    weakref.WeakKeyDictionary()
)


def _grammar_masks(llm: TokenizedLLM) -> GrammarMasks:
    """Return the mask tables for ``llm``, building them on first use."""
    masks = _MASK_CACHE.get(llm)
    if masks is None:
        masks = GrammarMasks(llm)
        _MASK_CACHE[llm] = masks
    return masks


def _trailing_repetition(text: str) -> tuple[int, int] | None:
    """Detect a repeated trailing segment (degenerate generation loop).

    Returns ``(period, repetitions)`` when the text ends with the same
    segment repeated enough times to indicate a loop, otherwise None.
    Thresholds: 5 repetitions for 1-2 char segments (so legitimate short
    runs like ``"aaa"`` survive), 3 for segments up to 8 chars, 2 for
    segments up to 24 chars (long alternation cycles such as
    ``a|e|i|o|u|A|E|I|O|U|``).
    """
    n = len(text)
    for period in range(1, 25):
        if period <= 2:
            reps = 5
        elif period <= 8:
            reps = 3
        else:
            reps = 2
        span = period * reps
        if span > n:
            continue
        seg = text[n - period:]
        if text[n - span:] == seg * reps:
            return period, reps
    return None


def generate_string(
    llm: TokenizedLLM,
    input_ids: list[int],
    *,
    max_steps: int = 64,
) -> tuple[str, list[int]]:
    """Decode a JSON string body (without quotes) one token at a time.

    Within the last ``_STRING_CLOSE_WINDOW`` steps of the budget only
    tokens that complete the string remain legal, which forces
    termination instead of relying on post-hoc recovery heuristics.

    If the output degenerates into a repeating loop, the duplicate
    trailing segments are rolled back (their tokens are popped from the
    context, keeping a single instance) and the string is force-closed
    from there.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm)
    state = "body"
    closing_only = False
    for step in range(max_steps):
        if state == "done":
            return _decode_json_string_body(accumulated[:-1]), ids
        rep = _trailing_repetition(accumulated)
        if rep is not None:
            period, reps = rep
            excess = period * (reps - 1)
            removed = 0
            while removed < excess and len(ids) > len(input_ids):
                removed += len(id_text[ids.pop()])
            accumulated = accumulated[:len(accumulated) - removed]
            # Rollback may have severed an escape sequence; re-derive
            # the state from scratch.
            recomputed = _step_string("body", accumulated)
            if recomputed is None:
                break
            state = recomputed
            closing_only = True
        force_close = (
            closing_only or step >= max_steps - _STRING_CLOSE_WINDOW
        )
        mask = masks.string_valid[state]
        if force_close:
            closing_mask = masks.string_closing[state]
            if closing_mask.any():
                mask = closing_mask
                if closing_only:
                    # After a degenerate loop, close with the bare quote
                    # when available instead of letting the model pad
                    # the value with a decorative closing token
                    # (e.g. '..."').
                    bare = closing_mask & masks.bare_quote
                    if bare.any():
                        mask = bare
        if not mask.any():
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked_np(logits, mask)
        if best is None:
            break
        text = id_text[best]
        nxt = _step_string(state, text)
        if nxt is None:  # unreachable: token came from the valid mask
            break
        state = nxt
        accumulated += text
        ids.append(best)
    if state == "done":
        return _decode_json_string_body(accumulated[:-1]), ids
    raise RuntimeError(
        f"Constrained decoding failed to produce a string "
        f"(accumulated={accumulated!r})"
    )


def _decode_json_string_body(raw: str) -> str:
    """Resolve JSON escape sequences in an already-validated body."""
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt == "u":
            code = int(raw[i + 2:i + 6], 16)
            out.append(chr(code))
            i += 6
        else:
            mapping = {
                '"': '"',
                "\\": "\\",
                "/": "/",
                "b": "\b",
                "f": "\f",
                "n": "\n",
                "r": "\r",
                "t": "\t",
            }
            out.append(mapping[nxt])
            i += 2
    return "".join(out)


# ---------------------------------------------------------------------------
# Literal choice (booleans)
# ---------------------------------------------------------------------------


def _choose_literal(
    llm: TokenizedLLM,
    input_ids: list[int],
    choices: tuple[str, ...],
    *,
    max_steps: int = 8,
) -> tuple[str, list[int]]:
    """Decode exactly one of ``choices`` by masking everything else.

    No terminator is consumed: the returned ids end with the literal
    itself, so the caller controls the following separator.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    for _ in range(max_steps):
        if accumulated in choices:
            return accumulated, ids
        valid: list[int] = []
        for tid, text in llm.clean_vocab:
            candidate = accumulated + text
            if any(choice.startswith(candidate) for choice in choices):
                valid.append(tid)
        if not valid:
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked(logits, valid)
        if best is None:
            break
        accumulated += id_text[best]
        ids.append(best)
    if accumulated in choices:
        return accumulated, ids
    raise RuntimeError(
        f"Constrained decoding failed to choose among {choices!r} "
        f"(accumulated={accumulated!r})"
    )


# ---------------------------------------------------------------------------
# End-to-end orchestration for a single prompt
# ---------------------------------------------------------------------------


class _ValueResult(BaseModel):
    """Generated parameter value together with the updated context ids."""

    model_config = ConfigDict(frozen=True)

    python_value: Any
    ids: list[int]


def _coerce_number(text: str, expected: str) -> float | int:
    """Convert decoded numeric text into the matching Python scalar."""
    if expected == "integer":
        return int(text)
    return float(text)


def _default_value(expected: str) -> float | int | str | bool:
    """Return a type-correct neutral value for a parameter type.

    Used only as a last-resort fallback so that the output always stays
    schema-valid even if a single value decode fails.
    """
    defaults: dict[str, float | int | str | bool] = {
        "number": 0.0,
        "integer": 0,
        "string": "",
        "boolean": False,
    }
    return defaults[expected]


def call_for_prompt(
    llm: TokenizedLLM,
    functions: list[FunctionDefinition],
    prompt: str,
    *,
    debug: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Turn a single natural-language prompt into ``(name, parameters)``."""
    function_names = [fn.name for fn in functions]
    fn_by_name = {fn.name: fn for fn in functions}

    context = build_context(functions, prompt)
    ids = llm.encode(context)

    if debug:
        print(f"[debug] choosing function for: {prompt!r}")
    chosen, ids = choose_function_name(llm, ids, function_names)
    chosen_fn = fn_by_name[chosen]
    if debug:
        print(f"[debug]   -> name={chosen}")

    # Inject the structural JSON opening once the name is known.
    ids = ids + llm.encode('", "parameters": {')

    parameters: dict[str, Any] = {}
    items = list(chosen_fn.parameters.items())
    for index, (param_name, spec) in enumerate(items):
        is_last = index == len(items) - 1
        ids = ids + llm.encode(f'"{param_name}": ')
        try:
            value = _generate_value(llm, ids, spec, is_last=is_last)
        except RuntimeError:
            # Keep the output schema-valid: fall back to a neutral value
            # for this parameter only.
            value = _ValueResult(
                python_value=_default_value(spec.type), ids=ids
            )
        parameters[param_name] = value.python_value
        ids = value.ids
        if not is_last and spec.type in ("string", "boolean"):
            # number/integer decoding already consumed the "," terminator.
            ids = ids + llm.encode(", ")
        if debug:
            print(f"[debug]   -> {param_name}={value.python_value!r}")
    return chosen, parameters


def _generate_value(
    llm: TokenizedLLM,
    ids: list[int],
    spec: ParameterSpec,
    *,
    is_last: bool,
) -> _ValueResult:
    """Decode a single parameter value according to its declared type."""
    terminator = "}" if is_last else ","
    if spec.type in ("number", "integer"):
        text, new_ids = generate_number(
            llm,
            ids,
            terminator,
            allow_fraction=spec.type == "number",
        )
        return _ValueResult(
            python_value=_coerce_number(text, spec.type), ids=new_ids
        )
    if spec.type == "string":
        ids_with_quote = ids + llm.encode('"')
        text, new_ids = generate_string(llm, ids_with_quote)
        return _ValueResult(python_value=text, ids=new_ids)
    if spec.type == "boolean":
        literal, new_ids = _choose_literal(llm, ids, ("true", "false"))
        return _ValueResult(python_value=literal == "true", ids=new_ids)
    raise ValueError(f"Unsupported parameter type: {spec.type}")
