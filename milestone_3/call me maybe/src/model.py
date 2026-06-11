"""Wrapper attorno a ``Small_LLM_Model`` che espone utility a livello di token.

Il wrapper mantiene il progetto libero da dipendenze dirette ``torch`` / ``transformers``
-- ogni chiamata passa attraverso i metodi pubblici dell'SDK e lavora
su liste Python semplici.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

try:
    from llm_sdk.llm_sdk import Small_LLM_Model
except ImportError:  # installed flat as the ``llm_sdk`` package
    from llm_sdk import Small_LLM_Model  # type: ignore[attr-defined,no-redef]

# Tutto ciò che è sotto 0x20 (tranne il tab) non è sicuro all'interno di una stringa JSON e
# indica anche fortemente che un token rappresenta byte di controllo/speciali.
_FORBIDDEN_CHAR_ORDS = frozenset(range(0, 0x20)) - {0x09}


def _has_forbidden_chars(text: str) -> bool:
    """Restituisce True se il testo contiene un carattere di controllo diverso dal tab."""
    return any(ord(c) in _FORBIDDEN_CHAR_ORDS for c in text)


def _bytes_to_unicode_map() -> dict[int, str]:
    """Ricrea la mappatura byte-to-unicode di GPT-2 / Qwen.

    Identica alla mappatura ufficiale fornita con il tokenizer BPE di GPT-2;
    reimplementata localmente in modo che nessuna libreria tokenizer di terze parti
    venga importata a runtime.
    """
    bs: list[int] = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    cs: list[int] = list(bs)
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


def _decode_vocab_token(token_str: str, u2b: dict[str, int]) -> str:
    """Traduce una stringa token di vocab.json nel testo letterale che codifica.

    I token che non possono essere mappati (token speciali, sequenze UTF-8 parziali)
    restituiscono una stringa vuota in modo che la logica di masking non li selezioni mai.
    """
    try:
        byte_values = bytes(u2b[c] for c in token_str)
    except KeyError:
        return ""
    try:
        return byte_values.decode("utf-8")
    except UnicodeDecodeError:
        return ""


class TokenizedLLM:
    """Facade leggera su :class:`Small_LLM_Model` con utility per il vocabolario."""

    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B") -> None:
        """Carica il modello e costruisce la tabella ``id -> testo letterale``."""
        self._model = Small_LLM_Model(model_name=model_name)
        self._id_to_text: dict[int, str] = {}
        self._clean_vocab: list[tuple[int, str]] = []
        self._vocab_size: int = 0
        self._load_vocab()

    def _load_vocab(self) -> None:
        """Legge vocab.json e precalcola le tabelle per il decoder."""
        vocab_path = Path(self._model.get_path_to_vocab_file())
        with vocab_path.open(encoding="utf-8") as handle:
            raw_vocab: dict[str, int] = json.load(handle)
        b2u = _bytes_to_unicode_map()
        u2b = {v: k for k, v in b2u.items()}
        max_id = -1
        for token_str, token_id in raw_vocab.items():
            text = _decode_vocab_token(token_str, u2b)
            self._id_to_text[token_id] = text
            if token_id > max_id:
                max_id = token_id
        self._vocab_size = max_id + 1
        # Precalcolata una volta: token con testo letterale utilizzabile. Il decoder
        # itera questa lista ad ogni passo invece di rifiltrare l'intero
        # vocabolario.
        self._clean_vocab = [
            (tid, text)
            for tid, text in self._id_to_text.items()
            if text and not _has_forbidden_chars(text)
        ]

    @property
    def id_to_text(self) -> dict[int, str]:
        """Mappatura di ogni id del token del vocabolario base al suo testo letterale."""
        return self._id_to_text

    @property
    def clean_vocab(self) -> list[tuple[int, str]]:
        """Coppie ``(id, text)`` prefiltrate sicure per il decoding vincolato."""
        return self._clean_vocab

    @property
    def vocab_size(self) -> int:
        """Numero di token del vocabolario base (token aggiunti/speciali esclusi)."""
        return self._vocab_size

    def encode(self, text: str) -> list[int]:
        """Codifica una stringa in una lista piatta di id dei token."""
        tensor = self._model.encode(text)
        nested = tensor.tolist()
        return [int(x) for x in nested[0]]

    def decode(self, ids: Sequence[int]) -> str:
        """Decodifica una sequenza di id dei token tornando al testo tramite l'SDK."""
        return self._model.decode(list(ids))

    def get_logits(self, input_ids: Sequence[int]) -> list[float]:
        """Restituisce i logit del prossimo token per ``input_ids``."""
        return self._model.get_logits_from_input_ids(list(input_ids))
