"""Wrapper around ``Small_LLM_Model`` exposing token-level utilities.

The wrapper keeps the project free of direct ``torch`` / ``transformers``
dependencies — every interaction goes through the public methods of the SDK
and works on plain Python lists.
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
    """Reproduce the GPT-2 / Qwen byte-to-unicode mapping.

    Identical to the canonical implementation shipped with the GPT-2 BPE
    tokenizer; we re-implement it locally so we do not need to import any
    third-party library at runtime.
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
    """Inverse of :func:`_bytes_to_unicode_map`."""
    return {v: k for k, v in _bytes_to_unicode_map().items()}


def _decode_vocab_token(token_str: str, u2b: dict[str, int]) -> str:
    """Translate a vocab.json token string into the literal text it represents.

    Tokens that cannot be mapped (special tokens, partial UTF-8 fragments)
    return an empty string so they are never selected by the masking logic.
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
    """Thin facade over :class:`Small_LLM_Model` with vocab utilities."""

    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B") -> None:
        """Load the model and build the ``id -> literal text`` table."""
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
        """Mapping of every base-vocabulary token id to its literal text."""
        return self._id_to_text

    @property
    def vocab_size(self) -> int:
        """Number of base vocab tokens (excl. added/special tokens)."""
        return self._vocab_size

    def encode(self, text: str) -> list[int]:
        """Encode a string into a flat list of token ids."""
        tensor = self._model.encode(text)
        nested = tensor.tolist()
        return [int(x) for x in nested[0]]

    def decode(self, ids: Sequence[int]) -> str:
        """Decode a token id sequence back to text via the SDK tokenizer."""
        return self._model.decode(list(ids))

    def get_logits(self, input_ids: Sequence[int]) -> list[float]:
        """Return the next-token logits for ``input_ids``."""
        return self._model.get_logits_from_input_ids(list(input_ids))
