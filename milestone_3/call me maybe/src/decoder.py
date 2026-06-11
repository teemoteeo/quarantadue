"""Primitive di decodifica vincolata che estraggono chiamate a funzione.

A ogni passo: si chiedono i logit, si maschera (maschere numpy cached per
stato DFA o per prefisso) tutto ciò che uscirebbe dalla grammatica attiva
(nome funzione / numero JSON / stringa JSON / booleano), si prende il token
legale col punteggio più alto. Solo i *valori* sono generati dal modello;
l'impalcatura strutturale JSON è iniettata verbatim. La terminazione è
garantita per costruzione: vicino al budget la grammatica delle stringhe
ammette solo token di chiusura.
"""

from __future__ import annotations

import weakref
from typing import Any

import numpy as np
import numpy.typing as npt

from .model import TokenizedLLM
from .schemas import FunctionDefinition, ParameterSpec

NEG_INF: float = -1e30

BoolMask = npt.NDArray[np.bool_]

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DIGITS = frozenset("0123456789")
# Secondo nibble di un \uDXXX: 8-B => surrogato alto (D800-DBFF),
# C-F => surrogato basso (DC00-DFFF). I surrogati sono validi in JSON solo
# come coppia alto+basso; da soli non si possono codificare in UTF-8.
_HIGH_SURROGATE_SECOND = frozenset("89abAB")
_LOW_SURROGATE_SECOND = frozenset("cdefCDEF")
_HEX_D = frozenset("dD")
_SIMPLE_ESCAPES = frozenset('"\\/bfnrt')
_ESCAPE_MAP = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}

# Valori neutri per tipo, usati come fallback di emergenza così l'output
# rimane sempre schema-valido.
_TYPE_DEFAULTS: dict[str, float | int | str | bool] = {
    "number": 0.0,
    "integer": 0,
    "string": "",
    "boolean": False,
}

# Quando una stringa è a questo numero di passi dal budget, il decoder
# ammette solo token che la chiudono.
_STRING_CLOSE_WINDOW: int = 8


def _argmax_masked_np(logits: list[float], mask: BoolMask) -> int | None:
    """Id del token col logit più alto consentito da ``mask``, o None.

    I logit possono essere più lunghi del vocabolario base (righe di
    embedding con padding, mai valide): si tronca alla lunghezza minore.
    """
    arr = np.asarray(logits, dtype=np.float64)
    k = min(arr.shape[0], mask.shape[0])
    valid = mask[:k]
    if not valid.any():
        return None
    return int(np.where(valid, arr[:k], NEG_INF).argmax())


def _pick_token(
    llm: TokenizedLLM, ids: list[int], mask: BoolMask
) -> int | None:
    """Miglior token legale; salta il forward pass se la scelta è forzata."""
    if not mask.any():
        return None
    if int(mask.sum()) == 1:
        return int(mask.argmax())
    return _argmax_masked_np(llm.get_logits(ids), mask)


# ---------------------------------------------------------------------------
# Assemblaggio del prompt
# ---------------------------------------------------------------------------


def build_context(functions: list[FunctionDefinition], prompt: str) -> str:
    """Costruisce il prompt testuale che imposta il task di function-calling."""
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
# Scelta vincolata a un insieme finito (nomi funzione, booleani)
# ---------------------------------------------------------------------------


def _choose_target(
    llm: TokenizedLLM,
    input_ids: list[int],
    targets: tuple[str, ...],
    *,
    max_steps: int = 32,
) -> tuple[str, list[int]]:
    """Decodifica esattamente uno dei ``targets`` mascherando tutto il resto.

    Se l'accumulato è sia un target completo che prefisso stretto di uno più
    lungo (es. ``fn_add`` vs ``fn_add_numbers``) arbitrano i logit: la
    virgoletta di chiusura compete col miglior token di continuazione.
    Appena un solo target è compatibile, il resto è iniettato verbatim.
    Nessun terminatore viene consumato.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm)
    for _ in range(max_steps):
        matching = [t for t in targets if t.startswith(accumulated)]
        is_complete = accumulated in targets
        if is_complete and len(matching) == 1:
            return accumulated, ids
        if not matching:
            break
        if not is_complete and len(matching) == 1:
            target = matching[0]
            ids.extend(llm.encode_cached(target[len(accumulated):]))
            return target, ids
        mask = masks.prefix_mask(accumulated, targets)
        if is_complete:
            logits = llm.get_logits(ids)
            best_cont = _argmax_masked_np(logits, mask)
            best_stop = _argmax_masked_np(logits, masks.bare_quote)
            if best_cont is None or (
                best_stop is not None
                and logits[best_stop] >= logits[best_cont]
            ):
                return accumulated, ids
            accumulated += id_text[best_cont]
            ids.append(best_cont)
            continue
        best = _pick_token(llm, ids, mask)
        if best is None:
            break
        accumulated += id_text[best]
        ids.append(best)
    if accumulated in targets:
        return accumulated, ids
    raise RuntimeError(
        f"Constrained decoding failed to choose among {targets!r} "
        f"(accumulated={accumulated!r})"
    )


# ---------------------------------------------------------------------------
# Grammatica dei numeri JSON
# ---------------------------------------------------------------------------


_NUMBER_STATES: tuple[str, ...] = ("start", "sign", "int", "dot", "frac")
# Transizioni su cifra; "done" è assente: non ammette altri caratteri.
_NUMBER_ON_DIGIT = {
    "start": "int",
    "sign": "int",
    "int": "int",
    "dot": "frac",
    "frac": "frac",
}


def _step_number(
    state: str,
    text: str,
    terminator: str,
    *,
    allow_fraction: bool = True,
) -> str | None:
    """Avanza il DFA ``number<terminator>`` da ``state`` su ``text``.

    Ritorna lo stato finale (``"done"`` consumato il terminatore) o None se
    il testo non è valido. Con ``allow_fraction=False`` il punto decimale è
    rifiutato, così i parametri interi non troncano mai una frazione.
    """
    for ch in text:
        if ch in _DIGITS:
            nxt = _NUMBER_ON_DIGIT.get(state)
        elif ch == terminator and state in ("int", "frac"):
            nxt = "done"
        elif ch == "-" and state == "start":
            nxt = "sign"
        elif ch == "." and state == "int" and allow_fraction:
            nxt = "dot"
        else:
            nxt = None
        if nxt is None:
            return None
        state = nxt
    return state


def generate_number(
    llm: TokenizedLLM,
    input_ids: list[int],
    terminator: str,
    *,
    allow_fraction: bool = True,
    max_steps: int = 24,
) -> tuple[str, list[int]]:
    """Decodifica un numero JSON fino a (e consumando) ``terminator``.

    Ritorna il testo senza terminatore; il token terminatore è già negli id
    restituiti, quindi chi chiama non deve aggiungere un separatore.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm).number(terminator, allow_fraction)
    state = "start"
    for _ in range(max_steps):
        if state == "done":
            return accumulated[:-1], ids
        best = _pick_token(llm, ids, masks[state])
        if best is None:
            break
        text = id_text[best]
        nxt = _step_number(
            state, text, terminator, allow_fraction=allow_fraction
        )
        if nxt is None:  # irraggiungibile: il token viene dalla maschera
            break
        state = nxt
        accumulated += text
        ids.append(best)
    if state == "done":
        return accumulated[:-1], ids
    # Il solo body potrebbe già essere un numero valido (budget esaurito
    # prima del token terminatore).
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
# Grammatica delle stringhe JSON
# ---------------------------------------------------------------------------

# Transizioni per stato come (charset, prossimo stato), valutate in ordine;
# carattere senza regola = testo invalido. Lo stato "body" è gestito a parte
# (accetta qualsiasi char >= 0x20 tranne '"' e '\\'), "done" non ammette
# nulla. Stati: u* = escape \uXXXX su BMP; u1d distingue D000-D7FF (BMP) dai
# surrogati; u*hi = surrogato alto, che esige subito la coppia bassa
# \uDC00-\uDFFF (esc_low, lu*). Surrogati bassi isolati rifiutati: la
# stringa decodificata resta sempre codificabile in UTF-8.
_STRING_TABLE: dict[str, tuple[tuple[frozenset[str], str], ...]] = {
    "escape": ((_SIMPLE_ESCAPES, "body"), (frozenset("u"), "u0")),
    "u0": ((_HEX_D, "u1d"), (_HEX_DIGITS, "u1n")),
    "u1d": (
        (_HIGH_SURROGATE_SECOND, "u2hi"),
        (_HEX_DIGITS - _LOW_SURROGATE_SECOND, "u2n"),
    ),
    "u1n": ((_HEX_DIGITS, "u2n"),),
    "u2n": ((_HEX_DIGITS, "u3n"),),
    "u3n": ((_HEX_DIGITS, "body"),),
    "u2hi": ((_HEX_DIGITS, "u3hi"),),
    "u3hi": ((_HEX_DIGITS, "after_high"),),
    "after_high": ((frozenset("\\"), "esc_low"),),
    "esc_low": ((frozenset("u"), "lu0"),),
    "lu0": ((_HEX_D, "lu1"),),
    "lu1": ((_LOW_SURROGATE_SECOND, "lu2"),),
    "lu2": ((_HEX_DIGITS, "lu3"),),
    "lu3": ((_HEX_DIGITS, "body"),),
}
_STRING_STATES: tuple[str, ...] = ("body", *_STRING_TABLE)


def _step_string(state: str, text: str) -> str | None:
    """Avanza il DFA della stringa JSON da ``state`` su ``text``.

    Ritorna lo stato finale (``"done"`` consumata la virgoletta di chiusura
    non escapata) o None se il testo non è valido da quello stato.
    """
    for ch in text:
        if state == "body":
            if ch == '"':
                state = "done"
            elif ch == "\\":
                state = "escape"
            elif ord(ch) < 0x20:
                return None
            continue
        rules = _STRING_TABLE.get(state)
        if rules is None:  # "done": nessun carattere ulteriore ammesso
            return None
        for charset, nxt in rules:
            if ch in charset:
                state = nxt
                break
        else:
            return None
    return state


# ---------------------------------------------------------------------------
# Maschere del vocabolario precalcolate per stato
# ---------------------------------------------------------------------------


class GrammarMasks:
    """Maschere booleane numpy sul vocabolario, una per stato DFA.

    Nei DFA la validità di ``accumulato + token`` dipende solo dallo stato
    raggiunto dopo ``accumulato``: ogni stato classifica il vocabolario una
    volta sola e un passo di decodifica diventa lookup + argmax vettorizzato.
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
        # Maschere numeriche lazy: solo i terminatori usati ("," e "}").
        self._number: dict[tuple[str, bool], dict[str, BoolMask]] = {}
        # Maschere lazy per prefisso di un insieme finito di target (nomi
        # funzione, booleani): le chiavi raggiungibili sono poche e ogni
        # maschera è riusata su tutti i prompt.
        self._prefix: dict[tuple[str, tuple[str, ...]], BoolMask] = {}

    def prefix_mask(
        self, accumulated: str, targets: tuple[str, ...]
    ) -> BoolMask:
        """Maschera dei token che tengono ``accumulated`` prefisso di un target."""
        key = (accumulated, targets)
        mask = self._prefix.get(key)
        if mask is None:
            mask = np.zeros(self._llm.vocab_size, dtype=bool)
            for tid, text in self._llm.clean_vocab:
                candidate = accumulated + text
                for target in targets:
                    if target.startswith(candidate):
                        mask[tid] = True
                        break
            self._prefix[key] = mask
        return mask

    def number(
        self, terminator: str, allow_fraction: bool
    ) -> dict[str, BoolMask]:
        """Maschere per una grammatica numerica, costruite alla prima chiamata."""
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
    """Tabelle delle maschere per ``llm``, costruite alla prima chiamata."""
    masks = _MASK_CACHE.get(llm)
    if masks is None:
        masks = GrammarMasks(llm)
        _MASK_CACHE[llm] = masks
    return masks


def _trailing_repetition(text: str) -> tuple[int, int] | None:
    """Rileva un segmento finale ripetuto (loop di generazione degenerato).

    Ritorna ``(period, repetitions)`` o None. Soglie: 5 ripetizioni per
    segmenti di 1-2 char (sequenze brevi legittime come ``"aaa"``
    sopravvivono), 3 fino a 8 char, 2 fino a 24 char (cicli di alternanza
    lunghi tipo ``a|e|i|o|u|A|E|I|O|U|``).
    """
    n = len(text)
    for period in range(1, 25):
        reps = 5 if period <= 2 else 3 if period <= 8 else 2
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
    """Decodifica il corpo di una stringa JSON (senza virgolette).

    Negli ultimi ``_STRING_CLOSE_WINDOW`` passi del budget solo i token che
    completano la stringa restano validi: terminazione forzata, niente
    euristiche di recupero post-hoc. Se l'output degenera in un loop, i
    segmenti duplicati vengono rollbackati (resta una singola istanza) e la
    stringa è chiusa forzatamente da lì.
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
            # Il rollback può aver spezzato una sequenza di escape:
            # ricalcola lo stato da zero.
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
                    # Dopo un loop degenerato, preferisci la virgoletta
                    # semplice a un token di chiusura decorativo ('..."').
                    bare = closing_mask & masks.bare_quote
                    if bare.any():
                        mask = bare
        best = _pick_token(llm, ids, mask)
        if best is None:
            break
        text = id_text[best]
        nxt = _step_string(state, text)
        if nxt is None:  # irraggiungibile: il token viene dalla maschera
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
    """Risolve le sequenze di escape JSON in un body già validato."""
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
            if 0xD800 <= code <= 0xDBFF:
                # Surrogato alto: la grammatica garantisce la coppia bassa.
                # Ricompone il codepoint reale (str UTF-8 valida).
                low = int(raw[i + 8:i + 12], 16)
                code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                i += 12
            else:
                i += 6
            out.append(chr(code))
        else:
            out.append(_ESCAPE_MAP[nxt])
            i += 2
    return "".join(out)


# ---------------------------------------------------------------------------
# Orchestrazione end-to-end per un singolo prompt
# ---------------------------------------------------------------------------


def default_value(expected: str) -> float | int | str | bool:
    """Valore neutro per tipo, fallback di emergenza schema-valido."""
    return _TYPE_DEFAULTS[expected]


def call_for_prompt(
    llm: TokenizedLLM,
    functions: list[FunctionDefinition],
    prompt: str,
    *,
    debug: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Trasforma un prompt in linguaggio naturale in ``(nome, parametri)``."""
    fn_by_name = {fn.name: fn for fn in functions}

    context = build_context(functions, prompt)
    ids = llm.encode(context)

    if debug:
        print(f"[debug] choosing function for: {prompt!r}")
    chosen, ids = _choose_target(llm, ids, tuple(fn_by_name))
    chosen_fn = fn_by_name[chosen]
    if debug:
        print(f"[debug]   -> name={chosen}")

    # Inietta l'apertura strutturale JSON una volta noto il nome.
    ids = ids + llm.encode_cached('", "parameters": {')

    parameters: dict[str, Any] = {}
    items = list(chosen_fn.parameters.items())
    for index, (param_name, spec) in enumerate(items):
        is_last = index == len(items) - 1
        ids = ids + llm.encode_cached(f'"{param_name}": ')
        try:
            value, ids = _generate_value(llm, ids, spec, is_last=is_last)
        except RuntimeError:
            # Output schema-valido: valore neutro solo per questo parametro.
            value = default_value(spec.type)
        parameters[param_name] = value
        if not is_last and spec.type in ("string", "boolean"):
            # number/integer ha già consumato il terminatore ",".
            ids = ids + llm.encode_cached(", ")
        if debug:
            print(f"[debug]   -> {param_name}={value!r}")
    return chosen, parameters


def _generate_value(
    llm: TokenizedLLM,
    ids: list[int],
    spec: ParameterSpec,
    *,
    is_last: bool,
) -> tuple[Any, list[int]]:
    """Decodifica il valore di un parametro in base al tipo dichiarato."""
    terminator = "}" if is_last else ","
    if spec.type in ("number", "integer"):
        text, new_ids = generate_number(
            llm,
            ids,
            terminator,
            allow_fraction=spec.type == "number",
        )
        return (
            int(text) if spec.type == "integer" else float(text), new_ids
        )
    if spec.type == "string":
        ids_with_quote = ids + llm.encode_cached('"')
        text, new_ids = generate_string(llm, ids_with_quote)
        return text, new_ids
    if spec.type == "boolean":
        literal, new_ids = _choose_target(
            llm, ids, ("true", "false"), max_steps=8
        )
        return literal == "true", new_ids
    raise ValueError(f"Unsupported parameter type: {spec.type}")
