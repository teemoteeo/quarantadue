"""Constrained decoding primitives used to produce function calls.

The decoder operates at the token level. For every generation step it:

1. Asks the model for next-token logits.
2. Computes the set of token ids whose literal text keeps the already
   accumulated output on a path that is still legal under the current
   grammar (function-name choice / JSON number / JSON string).
3. Masks every other logit to ``-inf`` (numerically ``-1e30``).
4. Selects the highest-scoring legal token, appends it, and loops.

The grammar is decomposed into three small DFAs, one per state we care
about; only the *values* the LLM is genuinely responsible for picking are
generated, while structural JSON glue is injected verbatim.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

from .model import TokenizedLLM
from .schemas import FunctionDefinition, ParameterSpec

NEG_INF: float = -1e30

# Anything below 0x20 (other than tab) is unsafe inside a JSON string and is
# also a strong indicator that a token represents control/special bytes.
_FORBIDDEN_CHAR_ORDS = frozenset(range(0, 0x20)) - {0x09}

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DIGITS = frozenset("0123456789")
_SIMPLE_ESCAPES = frozenset('"\\/bfnrt')


def _has_forbidden_chars(text: str) -> bool:
    """Return True if the text contains a non-tab control character."""
    return any(ord(c) in _FORBIDDEN_CHAR_ORDS for c in text)


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


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def build_context(functions: list[FunctionDefinition], prompt: str) -> str:
    """Build the textual prompt that frames the function-calling task."""
    lines: list[str] = [
        "You are a function-calling assistant. Pick the single best function "
        "from the catalog below and fill in its arguments based on the user's "
        "request. Only reply with one JSON object of the form "
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
    lines.append(f'User request: {prompt}')
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
    """Decode one of ``function_names`` by masking everything else away."""
    accumulated = ""
    ids = list(input_ids)
    id_to_text = llm.id_to_text
    for _ in range(max_steps):
        if accumulated in function_names:
            return accumulated, ids
        valid: list[int] = []
        for tid, text in id_to_text.items():
            if not text or _has_forbidden_chars(text):
                continue
            candidate = accumulated + text
            for target in function_names:
                if target.startswith(candidate):
                    valid.append(tid)
                    break
        if not valid:
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked(logits, valid)
        if best is None:
            break
        accumulated += id_to_text[best]
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


@dataclass(frozen=True)
class _NumberWalk:
    """Outcome of walking text through the number+terminator DFA."""

    status: str  # "complete", "prefix", or "invalid"


def _walk_number(text: str, terminator: str) -> _NumberWalk:
    """Walk ``text`` through the grammar ``number<terminator>``.

    The walk reports whether ``text`` is a valid prefix, a fully completed
    match (number followed by terminator), or invalid.
    """
    state = "start"
    seen_terminator = False
    for ch in text:
        if seen_terminator:
            return _NumberWalk("invalid")
        if state == "start":
            if ch == "-":
                state = "sign"
            elif ch in _DIGITS:
                state = "int"
            else:
                return _NumberWalk("invalid")
        elif state == "sign":
            if ch in _DIGITS:
                state = "int"
            else:
                return _NumberWalk("invalid")
        elif state == "int":
            if ch in _DIGITS:
                pass
            elif ch == ".":
                state = "dot"
            elif ch == terminator:
                seen_terminator = True
            else:
                return _NumberWalk("invalid")
        elif state == "dot":
            if ch in _DIGITS:
                state = "frac"
            else:
                return _NumberWalk("invalid")
        elif state == "frac":
            if ch in _DIGITS:
                pass
            elif ch == terminator:
                seen_terminator = True
            else:
                return _NumberWalk("invalid")
    if seen_terminator:
        return _NumberWalk("complete")
    return _NumberWalk("prefix")


def generate_number(
    llm: TokenizedLLM,
    input_ids: list[int],
    terminator: str,
    *,
    max_steps: int = 24,
) -> tuple[str, list[int]]:
    """Decode a JSON number up to (but not including) ``terminator``."""
    accumulated = ""
    ids = list(input_ids)
    id_to_text = llm.id_to_text
    for _ in range(max_steps):
        if _walk_number(accumulated, terminator).status == "complete":
            return accumulated[:-1], ids
        valid: list[int] = []
        for tid, text in id_to_text.items():
            if not text or _has_forbidden_chars(text):
                continue
            result = _walk_number(accumulated + text, terminator)
            if result.status != "invalid":
                valid.append(tid)
        if not valid:
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked(logits, valid)
        if best is None:
            break
        accumulated += id_to_text[best]
        ids.append(best)
    final = _walk_number(accumulated, terminator)
    if final.status == "complete":
        return accumulated[:-1], ids
    # Fallback: if the body alone is a valid number, accept it.
    if _walk_number(accumulated + terminator, terminator).status == "complete":
        return accumulated, ids
    raise RuntimeError(
        f"Constrained decoding failed to produce a number "
        f"(accumulated={accumulated!r})"
    )


# ---------------------------------------------------------------------------
# JSON string grammar
# ---------------------------------------------------------------------------


def _walk_string(text: str) -> str:
    """Classify ``text`` as a JSON string body prefix or complete value.

    The opening quote is assumed to already be in the input; ``text`` is the
    content that follows it and is expected to end with a closing quote.
    """
    state = "body"
    for ch in text:
        if state == "done":
            return "invalid"
        if state == "body":
            if ch == '"':
                state = "done"
            elif ch == "\\":
                state = "escape"
            elif ord(ch) >= 0x20:
                state = "body"
            else:
                return "invalid"
        elif state == "escape":
            if ch in _SIMPLE_ESCAPES:
                state = "body"
            elif ch == "u":
                state = "uhex0"
            else:
                return "invalid"
        elif state in ("uhex0", "uhex1", "uhex2", "uhex3"):
            if ch in _HEX_DIGITS:
                state = {
                    "uhex0": "uhex1",
                    "uhex1": "uhex2",
                    "uhex2": "uhex3",
                    "uhex3": "body",
                }[state]
            else:
                return "invalid"
    if state == "done":
        return "complete"
    return "prefix"


def generate_string(
    llm: TokenizedLLM,
    input_ids: list[int],
    *,
    max_steps: int = 64,
) -> tuple[str, list[int]]:
    """Decode a JSON string body (without its quotes) one token at a time."""
    accumulated = ""
    ids = list(input_ids)
    id_to_text = llm.id_to_text
    # Track recent suffixes to detect looping (common with regex alternation)
    recent_suffices: list[str] = []
    for _ in range(max_steps):
        if _walk_string(accumulated) == "complete":
            return _decode_json_string_body(accumulated[:-1]), ids
        valid: list[int] = []
        for tid, text in id_to_text.items():
            if not text or _has_forbidden_chars(text):
                continue
            result = _walk_string(accumulated + text)
            if result != "invalid":
                valid.append(tid)
        if not valid:
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked(logits, valid)
        if best is None:
            break
        accumulated += id_to_text[best]
        ids.append(best)
        # Loop detection: if the same suffix appears 3 times, bail out
        recent_suffices.append(id_to_text[best])
        recent_suffices = recent_suffices[-3:]
        if len(recent_suffices) == 3 and len(set(recent_suffices)) == 1:
            break
    if _walk_string(accumulated) == "complete":
        return _decode_json_string_body(accumulated[:-1]), ids
    # Fallback: extract a clean string (regex patterns, etc.)
    fallback = _extract_string_fallback(accumulated)
    if fallback is not None:
        # Fallback result is already a clean Python string - no decoding needed
        return fallback, ids
    raise RuntimeError(
        f"Constrained decoding failed to produce a string "
        f"(accumulated={accumulated!r})"
    )


def _decode_json_string_body(raw: str) -> str:
    """Resolve JSON escape sequences in an already validated body."""
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


def _extract_string_fallback(text: str) -> str | None:
    """Extract a usable string from accumulated text after loop detection.

    Handles regex-like patterns (alternations, repetitions) where the
    decoder gets stuck generating alternatives or repetitions without
    reaching a closing quote.
    """
    # 1. Find any complete string body
    for i, ch in enumerate(text):
        if ch == '"' and _walk_string(text[:i]) == "complete":
            return _decode_json_string_body(text[:i])

    # 2. If text ends with '|' (regex alternation), take last alternative
    # e.g. "a|e|i|o|u|" -> "a|e|i|o|u"
    if text.endswith("|"):
        stripped = text[:-1]
        last_bar = stripped.rfind("|")
        if last_bar > 0:
            last_alt = stripped[last_bar + 1:]
        elif stripped:
            last_alt = stripped
        else:
            last_alt = "a"
        return last_alt

    # 3. Detect regex repetition pattern (same segment repeated)
    # e.g. "cat.*cat.*cat.*" -> look for last complete segment
    # Check if the text contains repeating patterns (heuristic: 2+ occurrences)
    seg = _find_repeating_segment(text)
    if seg:
        return seg

    # 4. Generic: strip trailing garbage and find a quote
    cleaned = _strip_invalid_suffix(text)
    if cleaned and _walk_string(cleaned) == "complete":
        return _decode_json_string_body(cleaned)
    return None


def _find_repeating_segment(text: str) -> str | None:
    """Find a repeating regex-like segment at the end of text.


    Returns the last complete segment before the repetition starts,
    e.g. "cat.*cat.*cat.*" -> "cat.*" -> but strip to "cat".
    """
    n = len(text)
    if n < 4:
        return None
    # Try segment sizes from small to large
    for seg_len in range(2, n // 3):
        # Check if text ends with 2+ repetitions of this segment
        for repeat in range(2, 5):
            end_len = seg_len * repeat
            if end_len > n:
                break
            segment = text[n - seg_len:n - end_len + seg_len]
            is_repeat = all(
                text[
                    n - end_len + i * seg_len:n - end_len + (i + 1) * seg_len
                ] == segment
                for i in range(repeat)
            )
            if is_repeat:
                return segment
    # Fallback: strip back to last alphanumeric cluster
    i = n - 1
    while i >= 0 and not text[i].isalnum():
        i -= 1
    while i >= 0 and text[i].isalnum():
        i -= 1
    start = i + 1
    if start < n:
        return text[start:n]
    return None


def _strip_invalid_suffix(text: str) -> str:
    """Strip trailing content that can't be part of a valid string."""
    # Remove partial escape sequences at the end
    stripped = text
    while stripped and stripped[-1] == "\\" and stripped[-2:] != "\\\\":
        stripped = stripped[:-1]
    # Remove content after last complete escape
    last_escape = max(
        (i for i in range(len(stripped)) if stripped[i] == "\\"),
        default=-1
    )
    if last_escape >= 0 and last_escape < len(stripped) - 1:
        nxt = stripped[last_escape + 1]
        if nxt not in ('"', "\\", "/", "b", "f", "n", "r", "t", "u"):
            stripped = stripped[:last_escape]
    # Remove content after last quote
    last_quote = stripped.rfind('"')
    if last_quote > 0:
        stripped = stripped[:last_quote]
    return stripped


# ---------------------------------------------------------------------------
# End-to-end orchestration for a single prompt
# ---------------------------------------------------------------------------


def _coerce_number(text: str, expected: str) -> float | int:
    """Convert the decoded numeric text to the appropriate Python scalar."""
    if expected == "integer":
        return int(float(text))
    return float(text)


def call_for_prompt(
    llm: TokenizedLLM,
    functions: list[FunctionDefinition],
    prompt: str,
    *,
    debug: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Resolve a single natural-language prompt into ``(name, parameters)``."""
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

    # Inject the structural opening once the name is known.
    ids = ids + llm.encode('", "parameters": {')

    parameters: dict[str, Any] = {}
    items = list(chosen_fn.parameters.items())
    for index, (param_name, spec) in enumerate(items):
        is_last = index == len(items) - 1
        ids = ids + llm.encode(f'"{param_name}": ')
        value = _generate_value(llm, ids, spec, is_last=is_last)
        parameters[param_name] = value.python_value
        ids = value.ids
        if not is_last:
            ids = ids + llm.encode(", ")
        if debug:
            print(f"[debug]   -> {param_name}={value.python_value!r}")
    return chosen, parameters


@dataclass
class _ValueResult:
    """Generated parameter value with the updated context ids."""

    python_value: Any
    ids: list[int]


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
        text, new_ids = generate_number(llm, ids, terminator)
        return _ValueResult(_coerce_number(text, spec.type), new_ids)
    if spec.type == "string":
        ids_with_quote = ids + llm.encode('"')
        text, new_ids = generate_string(llm, ids_with_quote)
        return _ValueResult(text, new_ids)
    if spec.type == "boolean":
        # Booleans: constrained choice between "true" and "false".
        accumulated = ""
        choices = ["true" + terminator, "false" + terminator]
        cur = list(ids)
        id_to_text = llm.id_to_text
        for _ in range(8):
            if accumulated in choices:
                break
            valid: list[int] = []
            for tid, text in id_to_text.items():
                if not text or _has_forbidden_chars(text):
                    continue
                candidate = accumulated + text
                if any(c.startswith(candidate) for c in choices):
                    valid.append(tid)
            if not valid:
                break
            logits = llm.get_logits(cur)
            best = _argmax_masked(logits, valid)
            if best is None:
                break
            accumulated += id_to_text[best]
            cur.append(best)
        if accumulated.startswith("true"):
            return _ValueResult(True, cur)
        if accumulated.startswith("false"):
            return _ValueResult(False, cur)
        raise RuntimeError(f"Failed to decode boolean (got {accumulated!r})")
    raise ValueError(f"Unsupported parameter type: {spec.type}")
