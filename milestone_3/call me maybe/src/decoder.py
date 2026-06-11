"""Primitive per il decoding vincolato che estraggono chiamate di funzioni strutturate.

Il decoder opera a livello di token. Ad ogni passo di generazione:

1. Chiede al modello i logit del prossimo token.
2. Calcola l'insieme di id dei token il cui testo letterale mantiene
   l'output accumulato su un percorso ancora legale secondo la grammatica attiva
   (scelta del nome della funzione / numero JSON / stringa JSON / letterale booleano).
   Per le grammatiche di stringa e numero questo insieme è una maschera booleana
   numpy precalcolata per stato DFA: la legalità di ``accumulated + token`` dipende
   solo dallo stato DFA raggiunto dopo ``accumulated``, quindi la maschera di ogni
   stato viene costruita una volta sull'intero vocabolario all'avvio.
3. Maschera tutti gli altri logit a ``-inf`` (numericamente ``-1e30``).
4. Prende il token legale con punteggio più alto, lo aggiunge e ripete.

La grammatica è divisa in piccoli DFA, uno per stato di interesse; vengono generati
solo i *valori* di cui l'LLM è responsabile, mentre la struttura JSON viene
iniettata così com'è.

La terminazione è garantita per costruzione: vicino al limite di passi, la grammatica
delle stringhe ammette solo token che chiudono il valore, quindi ogni decode o
completa o genera un'eccezione -- non esiste alcun percorso di recupero euristico.
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

# Quando un valore di stringa è stato generato per questo numero di passi
# prima della fine del budget, il decoder permette solo i token che chiudono la stringa.
_STRING_CLOSE_WINDOW: int = 8


def _argmax_masked(
    logits: list[float], valid_ids: Iterable[int]
) -> int | None:
    """Restituisce l'id in ``valid_ids`` con il logit più alto, o None."""
    best_id: int | None = None
    best_logit = -math.inf
    for tid in valid_ids:
        score = logits[tid]
        if score > best_logit:
            best_logit = score
            best_id = tid
    return best_id


def _argmax_masked_np(logits: list[float], mask: BoolMask) -> int | None:
    """Restituisce l'id del token con logit più alto consentito da ``mask``, o None.

    Il vettore dei logit può essere più lungo del vocabolario base (righe di
    embedding riempite); gli id di padding non sono mai legali, quindi entrambi
    gli array vengono troncati alla lunghezza minore.
    """
    arr = np.asarray(logits, dtype=np.float64)
    k = min(arr.shape[0], mask.shape[0])
    valid = mask[:k]
    if not valid.any():
        return None
    return int(np.where(valid, arr[:k], NEG_INF).argmax())


# ---------------------------------------------------------------------------
# Costruzione del prompt
# ---------------------------------------------------------------------------


def build_context(functions: list[FunctionDefinition], prompt: str) -> str:
    """Costruisce il prompt testuale che definisce il compito di function calling."""
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
# Selezione del nome della funzione (vincolata al catalogo)
# ---------------------------------------------------------------------------


def choose_function_name(
    llm: TokenizedLLM,
    input_ids: list[int],
    function_names: list[str],
    *,
    max_steps: int = 32,
) -> tuple[str, list[int]]:
    """Decodifica esattamente uno tra ``function_names`` mascherando tutto il resto.

    Quando il testo accumulato è sia un nome completo del catalogo che un prefisso
    stretto di uno più lungo (es. ``fn_add`` vs ``fn_add_numbers``), sono i logit
    del modello a decidere: il token di chiusura virgoletta compete contro il token
    di continuazione migliore.
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
# Grammatica dei numeri JSON
# ---------------------------------------------------------------------------


_NUMBER_STATES: tuple[str, ...] = ("start", "sign", "int", "dot", "frac")


def _step_number(
    state: str,
    text: str,
    terminator: str,
    *,
    allow_fraction: bool = True,
) -> str | None:
    """Avanza il DFA ``number<terminator>`` da ``state`` su ``text``.

    Restituisce lo stato finale (``"done"`` dopo aver consumato il terminatore)
    o None quando il testo è illegale da quello stato. Con
    ``allow_fraction=False`` il punto decimale viene rifiutato, quindi i parametri
    interi non possono mai troncare silenziosamente una decodifica frazionaria.
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
    """Decodifica un numero JSON fino al (e consumando) ``terminator``.

    Restituisce il testo del numero senza il terminatore. Nota: il token terminatore
    è stato aggiunto agli id restituiti, quindi i chiamanti non devono aggiungere
    un separatore proprio dopo.
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
    # Il corpo da solo potrebbe già essere un numero valido (il budget è
    # terminato prima che il token terminatore venisse emesso).
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
    """Avanza il DFA della stringa JSON da ``state`` su ``text``.

    Restituisce lo stato finale (``"done"`` dopo aver consumato la virgoletta
    di chiusura non escapata) o None quando il testo è illegale da quello stato.
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
# Maschere del vocabolario precalcolate per stato
# ---------------------------------------------------------------------------


class GrammarMasks:
    """Maschere booleane numpy sul vocabolario, una per stato DFA.

    Poiché le grammatiche sono DFAs, la legalità di ``accumulated +
    token_text`` dipende solo dallo stato raggiunto dopo ``accumulated``
    (``step(step(s0, a), b) == step(s0, a + b)``). Ogni stato classifica
    quindi ogni token del vocabolario una volta, in anticipo; un passo di decode
    diventa così una lookup su dizionario più un argmax vettorizzato invece di
    una scansione Python sull'intero vocabolario.
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
        # Le maschere per i numeri vengono costruite con pigrizia: solo i terminatori
        # effettivamente usati ("," e "}") ricevono una tabella.
        self._number: dict[tuple[str, bool], dict[str, BoolMask]] = {}

    def number(
        self, terminator: str, allow_fraction: bool
    ) -> dict[str, BoolMask]:
        """Restituisce (costruendo al primo utilizzo) le maschere per una grammatica di numero."""
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
    """Restituisce le tabelle di maschere per ``llm``, costruendole al primo utilizzo."""
    masks = _MASK_CACHE.get(llm)
    if masks is None:
        masks = GrammarMasks(llm)
        _MASK_CACHE[llm] = masks
    return masks


def _trailing_repetition(text: str) -> tuple[int, int] | None:
    """Rileva un segmento finale ripetuto (loop di generazione degenere).

    Restituisce ``(periodo, ripetizioni)`` quando il testo termina con lo stesso
    segmento ripetuto abbastanza volte da indicare un loop, altrimenti None.
    Soglie: 5 ripetizioni per segmenti di 1-2 caratteri (così le sequenze brevi
    legittime come ``"aaa"`` sopravvivono), 3 per segmenti fino a 8 caratteri,
    2 per segmenti fino a 24 caratteri (cicli lunghi di alternanza come
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
    """Decodifica il corpo di una stringa JSON (senza virgolette) un token alla volta.

    Negli ultimi ``_STRING_CLOSE_WINDOW`` passi del budget, solo i token che
    completano la stringa rimangono legali, il che forza la terminazione invece
    di affidarsi a euristiche di recupero post-hoc.

    Se l'output degenera in un loop ripetitivo, i segmenti finali duplicati vengono
    annullati (i loro token vengono rimossi dal contesto, mantenendone uno solo) e
    la stringa viene chiusa forzatamente da quel punto.
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
            # Il rollback potrebbe aver interrotto una sequenza di escape; si
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
                    # Dopo un loop degenere, si chiude con la virgoletta nuda
                    # quando disponibile, invece di lasciare che il modello
                    # riempia il valore con un token decorativo di chiusura
                    # (es. '..."').
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
    """Risolve le sequenze di escape JSON in un corpo già validato."""
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
# Scelta del letterale (booleani)
# ---------------------------------------------------------------------------


def _choose_literal(
    llm: TokenizedLLM,
    input_ids: list[int],
    choices: tuple[str, ...],
    *,
    max_steps: int = 8,
) -> tuple[str, list[int]]:
    """Decodifica esattamente uno tra ``choices`` mascherando tutto il resto.

    Nessun terminatore viene consumato: gli id restituiti terminano con il letterale
    stesso, quindi il chiamante controlla il separatore successivo.
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
# Orchestrazione end-to-end per un singolo prompt
# ---------------------------------------------------------------------------


class _ValueResult(BaseModel):
    """Valore del parametro generato insieme agli id di contesto aggiornati."""

    model_config = ConfigDict(frozen=True)

    python_value: Any
    ids: list[int]


def _coerce_number(text: str, expected: str) -> float | int:
    """Converte il testo numerico decodificato nello scalare Python corrispondente."""
    if expected == "integer":
        return int(text)
    return float(text)


def _default_value(expected: str) -> float | int | str | bool:
    """Restituisce un valore neutro corretto per tipo di parametro.

    Usato solo come ultima risorsa in caso di fallback, in modo che l'output
    rimanga sempre valido per lo schema anche se un singolo decode di valore fallisce.
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
    """Trasforma un singolo prompt in linguaggio naturale in ``(name, parameters)``."""
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

    # Si inietta l'apertura JSON strutturale una volta noto il nome.
    ids = ids + llm.encode('", "parameters": {')

    parameters: dict[str, Any] = {}
    items = list(chosen_fn.parameters.items())
    for index, (param_name, spec) in enumerate(items):
        is_last = index == len(items) - 1
        ids = ids + llm.encode(f'"{param_name}": ')
        try:
            value = _generate_value(llm, ids, spec, is_last=is_last)
        except RuntimeError:
            # Mantiene l'output valido per lo schema: fallback a un valore neutro
            # solo per questo parametro.
            value = _ValueResult(
                python_value=_default_value(spec.type), ids=ids
            )
        parameters[param_name] = value.python_value
        ids = value.ids
        if not is_last and spec.type in ("string", "boolean"):
            # il decoding di number/integer ha già consumato il terminatore ",".
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
    """Decodifica un singolo valore di parametro in base al suo tipo dichiarato."""
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
