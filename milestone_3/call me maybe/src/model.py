"""wrapper attorno a ``Small_LLM_Model`` che tira fuori roba a livello di token.

il wrapper tiene il progetto pulito dalle dipendenze dirette di ``torch`` /
``transformers`` — ogni botta passa per i metodi pubblici dell'SDK e
lavora su liste Python normali.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

try:
    from llm_sdk.llm_sdk import Small_LLM_Model
except ImportError:  # installed flat as the ``llm_sdk`` package
    from llm_sdk import Small_LLM_Model  # type: ignore[attr-defined,no-redef]


def _bytes_to_unicode_map() -> dict[int, str]:
    """rifà la mappa byte-to-unicode di GPT-2 / Qwen.

    uguale spiccicata a quella ufficiale che gira col tokenizer BPE di GPT-2;
    qua la rifacciamo in casa così a runtime non ci tocca importare
    librerie di terzi.
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


def _unicode_to_bytes_map() -> dict[str, int]:
    """inversa di :func:`_bytes_to_unicode_map`."""
    return {v: k for k, v in _bytes_to_unicode_map().items()}


def _decode_vocab_token(token_str: str, u2b: dict[str, int]) -> str:
    """traduce una stringa token di vocab.json nel testo letterale che rappresenta.

    i token che non si riescono a mappare (token speciali, pezzi di UTF-8
    monchi) ritornano una stringa vuota, così la logica di mascheramento
    non li becca mai.
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
    """facciata snella sopra :class:`Small_LLM_Model` con utility per il vocab."""

    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B") -> None:
        """carica il modello e si costruisce la tabella ``id -> testo letterale``."""
        self._model = Small_LLM_Model(model_name=model_name)
        self._id_to_text: dict[int, str] = {}
        self._vocab_size: int = 0
        self._load_vocab()

    def _load_vocab(self) -> None:
        vocab_path = Path(self._model.get_path_to_vocab_file())
        with vocab_path.open(encoding="utf-8") as handle:
            raw_vocab: dict[str, int] = json.load(handle)
        u2b = _unicode_to_bytes_map()
        max_id = -1
        for token_str, token_id in raw_vocab.items():
            text = _decode_vocab_token(token_str, u2b)
            self._id_to_text[token_id] = text
            if token_id > max_id:
                max_id = token_id
        self._vocab_size = max_id + 1

    @property
    def id_to_text(self) -> dict[int, str]:
        """mappatura di ogni id di token del vocab base al suo testo letterale."""
        return self._id_to_text

    @property
    def vocab_size(self) -> int:
        """numero di token del vocab base (esclusi quelli aggiunti/speciali)."""
        return self._vocab_size

    def encode(self, text: str) -> list[int]:
        """codifica una stringa in una lista piatta di id di token."""
        tensor = self._model.encode(text)
        nested = tensor.tolist()
        return [int(x) for x in nested[0]]

    def decode(self, ids: Sequence[int]) -> str:
        """decodifica una sequenza di id di token in testo passando per il tokenizer dell'SDK."""
        return self._model.decode(list(ids))

    def get_logits(self, input_ids: Sequence[int]) -> list[float]:
        """ritorna i logit del prossimo token per ``input_ids``."""
        return self._model.get_logits_from_input_ids(list(input_ids))
