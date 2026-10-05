"""Embedding model for the vector index (bonus: semantic search).

all-MiniLM-L6-v2 is a small BERT-style model: 384-dim vectors, a few hundred
MB of weights, comfortable on a CPU-only machine. It is the semantic half
of hybrid retrieval: it matches a paraphrased question to code that uses
different words.
"""

from collections.abc import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

# ponytail: 500 chars ~= 300 tokens < the 512 limit, and a chunk beyond that
# is already mostly its neighbours' business (overlap windows).
EMBED_CHARS = 500


class Embedder:
    """Carica il modello una volta e trasforma testo in vettori."""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self) -> None:
        """Carica il modello (~90 MB, scaricati al primo uso)."""
        self.model = SentenceTransformer(self.MODEL_NAME)

    def encode(
        self, texts: Sequence[str], *, show_progress_bar: bool = False
    ) -> np.ndarray:
        """Vettori normalizzati (float32, una riga per testo).

        Normalizzati: la somiglianza diventa un semplice prodotto scalare.
        La barra di avanzamento è off di default: a ogni query, una riga
        di tqdm in più avrebbe sepolto l'output. `index` la riattiva.
        """
        matrix = self.model.encode(
            list(texts),  # texts arrive already truncated by the callers
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=show_progress_bar,
        )
        return np.asarray(matrix, dtype=np.float32)
