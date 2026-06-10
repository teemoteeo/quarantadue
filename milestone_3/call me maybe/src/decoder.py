"""primitive di decoding vincolato per tirar fuori chiamate di funzione.

il decoder lavora a livello di token. ad ogni passo di generazione fa così:

1. chiede al modello i logit del prossimo token.
2. calcola l'insieme di id di token il cui testo letterale tiene l'output
   accumulato su una strada ancora legale secondo la grammatica corrente
   (scelta del nome di funzione / numero JSON / stringa JSON).
3. maschera ogni altro logit a ``-inf`` (numericamente ``-1e30``).
4. piglia il token legale col punteggio più alto, lo attacca, e cicla.

la grammatica è spezzata in tre DFA piccoletti, uno per stato che ci interessa;
si generano solo i *valori* di cui l'LLM è davvero responsabile, mentre la
roba strutturale del JSON viene buttata dentro pari pari.
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
    """ritorna True se il testo ha dentro un carattere di controllo che non è tab."""
    return any(ord(c) in _FORBIDDEN_CHAR_ORDS for c in text)


def _argmax_masked(
    logits: list[float], valid_ids: Iterable[int]
) -> int | None:
    """ritorna l'id in ``valid_ids`` col logit più alto, oppure None."""
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
    """costruisce il prompt testuale che inquadra il compito di chiamata funzione."""
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
    """decodifica uno tra ``function_names`` mascherando via tutto il resto."""
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
    """risultato del passaggio del testo nel DFA numero+terminatore."""

    status: str  # "complete", "prefix", or "invalid"


def _walk_number(text: str, terminator: str) -> _NumberWalk:
    """fa camminare ``text`` dentro la grammatica ``number<terminator>``.

    la camminata dice se ``text`` è un prefisso valido, un match completo
    (numero seguito dal terminatore), oppure roba non valida.
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
    """decodifica un numero JSON fino a (escluso) ``terminator``."""
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
    """classifica ``text`` come prefisso del corpo di una stringa JSON oppure valore completo.

    si dà per scontato che la virgoletta d'apertura stia già nell'input;
    ``text`` è la roba che viene dopo e si aspetta finisca con la virgoletta di chiusura.
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
    """decodifica il corpo di una stringa JSON (senza le virgolette) un token alla volta."""
    accumulated = ""
    ids = list(input_ids)
    id_to_text = llm.id_to_text
    # tiene traccia dei suffissi recenti per beccare loop (capita con alternative regex)
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
        # rilevamento loop: se lo stesso suffisso esce 3 volte, mollo tutto
        recent_suffices.append(id_to_text[best])
        recent_suffices = recent_suffices[-3:]
        if len(recent_suffices) == 3 and len(set(recent_suffices)) == 1:
            break
    if _walk_string(accumulated) == "complete":
        return _decode_json_string_body(accumulated[:-1]), ids
    # ripiego: tira fuori una stringa pulita (pattern regex, ecc.)
    fallback = _extract_string_fallback(accumulated)
    if fallback is not None:
        # il risultato del ripiego è già una stringa Python pulita, niente da decodificare
        return fallback, ids
    raise RuntimeError(
        f"Constrained decoding failed to produce a string "
        f"(accumulated={accumulated!r})"
    )


def _decode_json_string_body(raw: str) -> str:
    """risolve le sequenze di escape JSON in un corpo già validato."""
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
    """tira fuori una stringa usabile dal testo accumulato dopo aver beccato un loop.

    gestisce pattern tipo regex (alternative, ripetizioni) dove il decoder
    rimane incastrato a sfornare alternative o ripetizioni senza arrivare
    mai alla virgoletta di chiusura.
    """
    # 1. trova un corpo di stringa completo
    for i, ch in enumerate(text):
        if ch == '"' and _walk_string(text[:i]) == "complete":
            return _decode_json_string_body(text[:i])

    # 2. se il testo finisce con '|' (alternativa regex), pigliamo l'ultima alternativa
    # tipo "a|e|i|o|u|" -> "a|e|i|o|u"
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

    # 3. becca pattern di ripetizione regex (stesso segmento ripetuto)
    # tipo "cat.*cat.*cat.*" -> guarda l'ultimo segmento completo
    # controlla se il testo ha dentro pattern ripetuti (a occhio: 2+ volte)
    seg = _find_repeating_segment(text)
    if seg:
        return seg

    # 4. modalità generica: leva la robaccia in coda e trova una virgoletta
    cleaned = _strip_invalid_suffix(text)
    if cleaned and _walk_string(cleaned) == "complete":
        return _decode_json_string_body(cleaned)
    return None


def _find_repeating_segment(text: str) -> str | None:
    """trova un segmento ripetuto tipo regex alla fine del testo.


    ritorna l'ultimo segmento completo prima che parta la ripetizione,
    tipo "cat.*cat.*cat.*" -> "cat.*" -> ma poi tagliato a "cat".
    """
    n = len(text)
    if n < 4:
        return None
    # prova le dimensioni dei segmenti dal piccolo al grande
    for seg_len in range(2, n // 3):
        # controlla se il testo finisce con 2 o più ripetizioni di questo segmento
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
    # ripiego: torna indietro fino all'ultimo gruppo alfanumerico
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
    """leva la roba in coda che non può stare dentro una stringa valida."""
    # via le sequenze di escape monche alla fine
    stripped = text
    while stripped and stripped[-1] == "\\" and stripped[-2:] != "\\\\":
        stripped = stripped[:-1]
    # via la roba dopo l'ultimo escape completo
    last_escape = max(
        (i for i in range(len(stripped)) if stripped[i] == "\\"),
        default=-1
    )
    if last_escape >= 0 and last_escape < len(stripped) - 1:
        nxt = stripped[last_escape + 1]
        if nxt not in ('"', "\\", "/", "b", "f", "n", "r", "t", "u"):
            stripped = stripped[:last_escape]
    # via la roba dopo l'ultima virgoletta
    last_quote = stripped.rfind('"')
    if last_quote > 0:
        stripped = stripped[:last_quote]
    return stripped


# ---------------------------------------------------------------------------
# End-to-end orchestration for a single prompt
# ---------------------------------------------------------------------------


def _coerce_number(text: str, expected: str) -> float | int:
    """converte il testo numerico decodificato nello scalare Python giusto."""
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
    """trasforma un singolo prompt in linguaggio naturale in ``(name, parameters)``."""
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

    # buttiamo dentro l'apertura strutturale una volta che sappiamo il nome.
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
    """valore del parametro generato insieme agli id di contesto aggiornati."""

    python_value: Any
    ids: list[int]


def _generate_value(
    llm: TokenizedLLM,
    ids: list[int],
    spec: ParameterSpec,
    *,
    is_last: bool,
) -> _ValueResult:
    """decodifica il valore di un singolo parametro in base al tipo dichiarato."""
    terminator = "}" if is_last else ","
    if spec.type in ("number", "integer"):
        text, new_ids = generate_number(llm, ids, terminator)
        return _ValueResult(_coerce_number(text, spec.type), new_ids)
    if spec.type == "string":
        ids_with_quote = ids + llm.encode('"')
        text, new_ids = generate_string(llm, ids_with_quote)
        return _ValueResult(text, new_ids)
    if spec.type == "boolean":
        # booleani: scelta vincolata tra "true" e "false".
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
