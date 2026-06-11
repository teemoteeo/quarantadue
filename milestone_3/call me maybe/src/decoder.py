"""Primitive di decodifica vincolata che estraggono chiamate a funzione strutturate.

Il decoder lavora a livello di token. A ogni passo di generazione fa:

1. Chiede al modello i logit del prossimo token.
2. Calcola l'insieme degli id di token il cui testo letterale mantiene l'output
   accumulato su un percorso ancora valido secondo la grammatica attiva
   (scelta del nome funzione / numero JSON / stringa JSON / letterale booleano).
   Questo insieme è sempre una maschera booleana numpy cached: per stringhe e
   numeri la validità di ``accumulato + token`` dipende solo dallo stato DFA
   raggiunto dopo ``accumulato``, quindi la maschera di ogni stato viene
   costruita una volta sola su tutto il vocabolario all'avvio; per nomi funzione
   e letterali booleani dipende solo dal prefisso accumulato, quindi le maschere
   vengono costruite lazy per prefisso e riusate su tutti i prompt.
3. Mette tutti gli altri logit a ``-inf`` (numericamente ``-1e30``).
4. Prende il token legale col punteggio più alto, lo appende, e riparte.

La grammatica è divisa in piccoli DFA, uno per stato di interesse; vengono generati
solo i *valori* di cui è responsabile il LLM, mentre l'impalcatura strutturale JSON
viene iniettata verbatim.

La terminazione è garantita per costruzione: vicino al budget di passi la grammatica
delle stringhe ammette solo token che chiudono il valore, quindi ogni decodifica o
si completa o solleva un'eccezione -- non c'è nessun percorso di recupero euristico.
"""

from __future__ import annotations

import weakref
from typing import Any, NamedTuple

import numpy as np
import numpy.typing as npt

from .model import TokenizedLLM
from .schemas import FunctionDefinition, ParameterSpec

NEG_INF: float = -1e30

BoolMask = npt.NDArray[np.bool_]

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_DIGITS = frozenset("0123456789")
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

# Valori neutri corretti per tipo, usati come fallback di emergenza così
# l'output rimane sempre schema-valido.
_TYPE_DEFAULTS: dict[str, float | int | str | bool] = {
    "number": 0.0,
    "integer": 0,
    "string": "",
    "boolean": False,
}

# Quando una stringa è stata generata per questo numero di passi prima del budget,
# il decoder ammette solo token che chiudono la stringa.
_STRING_CLOSE_WINDOW: int = 8


def _argmax_masked_np(logits: list[float], mask: BoolMask) -> int | None:
    """Ritorna l'id del token col logit più alto consentito da ``mask``, o None.

    Il vettore dei logit può essere più lungo del vocabolario base (righe di embedding
    con padding); gli id con padding non sono mai validi, quindi entrambi gli array
    vengono troncati alla lunghezza minore.
    """
    arr = np.asarray(logits, dtype=np.float64)
    k = min(arr.shape[0], mask.shape[0])
    valid = mask[:k]
    if not valid.any():
        return None
    return int(np.where(valid, arr[:k], NEG_INF).argmax())


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
# Selezione del nome funzione (vincolata al catalogo)
# ---------------------------------------------------------------------------


def choose_function_name(
    llm: TokenizedLLM,
    input_ids: list[int],
    function_names: list[str],
    *,
    max_steps: int = 32,
) -> tuple[str, list[int]]:
    """Decodifica esattamente uno dei ``function_names`` mascherando tutto il resto.

    Quando il testo accumulato è sia un nome completo del catalogo che un prefisso
    stretto di uno più lungo (es. ``fn_add`` vs ``fn_add_numbers``), sono i logit
    del modello ad arbitrare: il token della virgoletta di chiusura compete contro
    il miglior token di continuazione.

    Il modello viene interrogato solo finché il prefisso è ambiguo: appena
    un solo nome del catalogo è compatibile, il resto viene iniettato verbatim.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm)
    names = tuple(function_names)
    for _ in range(max_steps):
        matching = [
            name for name in function_names if name.startswith(accumulated)
        ]
        is_complete = accumulated in function_names
        if is_complete and len(matching) == 1:
            return accumulated, ids
        if not matching:
            break
        if not is_complete and len(matching) == 1:
            # Prefisso univoco: il resto del nome è forzato dalla grammatica,
            # quindi viene iniettato verbatim senza interrogare il modello
            # token per token.
            target = matching[0]
            ids.extend(llm.encode_cached(target[len(accumulated):]))
            return target, ids
        mask = masks.prefix_mask(accumulated, names)
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
        if not mask.any():
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked_np(logits, mask)
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
    """Avanza il DFA ``number<terminator>`` dallo ``state`` corrente su ``text``.

    Ritorna lo stato finale (``"done"`` una volta consumato il terminatore)
    o None se il testo non è valido da quello stato. Con
    ``allow_fraction=False`` il punto decimale viene rifiutato, così i parametri
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
    """Decodifica un numero JSON fino a (e consumando) ``terminator``.

    Ritorna il testo del numero senza il terminatore. Nota: il token terminatore
    è già stato aggiunto agli id restituiti, quindi chi chiama non deve aggiungere
    un separatore dopo.
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
        best: int | None
        if int(mask.sum()) == 1:
            # Un solo token legale: scelta forzata, niente forward pass.
            best = int(mask.argmax())
        else:
            logits = llm.get_logits(ids)
            best = _argmax_masked_np(logits, mask)
        if best is None:
            break
        text = id_text[best]
        nxt = _step_number(
            state, text, terminator, allow_fraction=allow_fraction
        )
        if nxt is None:  # irraggiungibile: il token viene dalla maschera valida
            break
        state = nxt
        accumulated += text
        ids.append(best)
    if state == "done":
        return accumulated[:-1], ids
    # Il solo body potrebbe già essere un numero valido (budget esaurito prima
    # che il token terminatore venisse emesso).
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
    """Avanza il DFA della stringa JSON dallo ``state`` corrente su ``text``.

    Ritorna lo stato finale (``"done"`` una volta consumata la virgoletta di chiusura
    non escapata) o None se il testo non è valido da quello stato.
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

    Siccome le grammatiche sono DFA, la validità di ``accumulato + testo_token``
    dipende solo dallo stato raggiunto dopo ``accumulato``
    (``step(step(s0, a), b) == step(s0, a + b)``). Ogni stato classifica quindi
    ogni token del vocabolario una volta sola, all'inizio; un passo di decodifica
    è poi una lookup nel dict più un argmax vettorizzato invece di uno scan Python
    su tutto il vocabolario.
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
        # Le maschere dei numeri vengono costruite lazy: solo i terminatori
        # davvero usati ("," e "}") ottengono una tabella.
        self._number: dict[tuple[str, bool], dict[str, BoolMask]] = {}
        # Maschere lazy per la decodifica vincolata a un insieme finito di
        # target (nomi funzione, letterali booleani). L'accumulato è sempre
        # un prefisso di un target, quindi le chiavi raggiungibili sono poche
        # e ogni maschera viene riusata su tutti i prompt.
        self._prefix: dict[tuple[str, tuple[str, ...]], BoolMask] = {}

    def prefix_mask(
        self, accumulated: str, targets: tuple[str, ...]
    ) -> BoolMask:
        """Maschera dei token che mantengono ``accumulated`` prefisso di un target."""
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
        """Ritorna (costruendo alla prima chiamata) le maschere per una grammatica numerica."""
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
    """Ritorna le tabelle delle maschere per ``llm``, costruendole alla prima chiamata."""
    masks = _MASK_CACHE.get(llm)
    if masks is None:
        masks = GrammarMasks(llm)
        _MASK_CACHE[llm] = masks
    return masks


def _trailing_repetition(text: str) -> tuple[int, int] | None:
    """Rileva un segmento finale ripetuto (loop di generazione degenerato).

    Ritorna ``(period, repetitions)`` quando il testo finisce con lo stesso
    segmento ripetuto abbastanza volte da indicare un loop, altrimenti None.
    Soglie: 5 ripetizioni per segmenti di 1-2 char (così sequenze brevi legittime
    come ``"aaa"`` sopravvivono), 3 per segmenti fino a 8 char, 2 per
    segmenti fino a 24 char (cicli di alternanza lunghi tipo
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

    Negli ultimi ``_STRING_CLOSE_WINDOW`` passi del budget solo i token che completano
    la stringa rimangono validi, il che forza la terminazione invece di affidarsi a
    euristiche di recupero post-hoc.

    Se l'output degenera in un loop ripetitivo, i segmenti finali duplicati vengono
    rollbackati (i loro token vengono rimossi dal contesto, tenendo una singola istanza)
    e la stringa viene chiusa forzatamente da lì.
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
            # Il rollback potrebbe aver spezzato una sequenza di escape; ricalcola
            # lo stato da zero.
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
                    # Dopo un loop degenerato, chiudi con la virgoletta semplice
                    # quando disponibile invece di lasciare che il modello
                    # riempia il valore con un token di chiusura decorativo
                    # (es. '..."').
                    bare = closing_mask & masks.bare_quote
                    if bare.any():
                        mask = bare
        if not mask.any():
            break
        best: int | None
        if int(mask.sum()) == 1:
            # Un solo token legale: scelta forzata, niente forward pass.
            best = int(mask.argmax())
        else:
            logits = llm.get_logits(ids)
            best = _argmax_masked_np(logits, mask)
        if best is None:
            break
        text = id_text[best]
        nxt = _step_string(state, text)
        if nxt is None:  # irraggiungibile: il token viene dalla maschera valida
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
            out.append(chr(code))
            i += 6
        else:
            out.append(_ESCAPE_MAP[nxt])
            i += 2
    return "".join(out)


# ---------------------------------------------------------------------------
# Scelta tra letterali (booleani)
# ---------------------------------------------------------------------------


def _choose_literal(
    llm: TokenizedLLM,
    input_ids: list[int],
    choices: tuple[str, ...],
    *,
    max_steps: int = 8,
) -> tuple[str, list[int]]:
    """Decodifica esattamente uno dei ``choices`` mascherando tutto il resto.

    Non viene consumato nessun terminatore: gli id restituiti terminano con il
    letterale stesso, quindi chi chiama controlla il separatore successivo.
    """
    accumulated = ""
    ids = list(input_ids)
    id_text = llm.id_to_text
    masks = _grammar_masks(llm)
    for _ in range(max_steps):
        if accumulated in choices:
            return accumulated, ids
        matching = [c for c in choices if c.startswith(accumulated)]
        if not matching:
            break
        if len(matching) == 1:
            # Scelta univoca: il resto del letterale è forzato, niente
            # ulteriori chiamate al modello.
            target = matching[0]
            ids.extend(llm.encode_cached(target[len(accumulated):]))
            return target, ids
        mask = masks.prefix_mask(accumulated, choices)
        if not mask.any():
            break
        logits = llm.get_logits(ids)
        best = _argmax_masked_np(logits, mask)
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


class _ValueResult(NamedTuple):
    """Valore del parametro generato insieme agli id di contesto aggiornati."""

    python_value: Any
    ids: list[int]


def _coerce_number(text: str, expected: str) -> float | int:
    """Converte il testo numerico decodificato nello scalare Python corrispondente."""
    if expected == "integer":
        return int(text)
    return float(text)


def default_value(expected: str) -> float | int | str | bool:
    """Ritorna un valore neutro corretto per tipo per un tipo di parametro.

    Usato solo come fallback di emergenza così l'output rimane sempre
    schema-valido anche se la decodifica di un singolo valore fallisce.
    """
    return _TYPE_DEFAULTS[expected]


def call_for_prompt(
    llm: TokenizedLLM,
    functions: list[FunctionDefinition],
    prompt: str,
    *,
    debug: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Trasforma un singolo prompt in linguaggio naturale in ``(nome, parametri)``."""
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

    # Inietta l'apertura strutturale JSON una volta noto il nome.
    ids = ids + llm.encode_cached('", "parameters": {')

    parameters: dict[str, Any] = {}
    items = list(chosen_fn.parameters.items())
    for index, (param_name, spec) in enumerate(items):
        is_last = index == len(items) - 1
        ids = ids + llm.encode_cached(f'"{param_name}": ')
        try:
            value = _generate_value(llm, ids, spec, is_last=is_last)
        except RuntimeError:
            # Mantieni l'output schema-valido: usa un valore neutro
            # solo per questo parametro.
            value = _ValueResult(
                python_value=default_value(spec.type), ids=ids
            )
        parameters[param_name] = value.python_value
        ids = value.ids
        if not is_last and spec.type in ("string", "boolean"):
            # la decodifica di number/integer ha già consumato il terminatore ",".
            ids = ids + llm.encode_cached(", ")
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
    """Decodifica il valore di un singolo parametro in base al suo tipo dichiarato."""
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
        ids_with_quote = ids + llm.encode_cached('"')
        text, new_ids = generate_string(llm, ids_with_quote)
        return _ValueResult(python_value=text, ids=new_ids)
    if spec.type == "boolean":
        literal, new_ids = _choose_literal(llm, ids, ("true", "false"))
        return _ValueResult(python_value=literal == "true", ids=new_ids)
    raise ValueError(f"Unsupported parameter type: {spec.type}")
