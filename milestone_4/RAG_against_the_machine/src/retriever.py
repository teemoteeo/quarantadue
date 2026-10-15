"""Indice BM25 (la "R" di RAG): costruirlo, salvarlo, interrogarlo.

BM25 e non embedding: veloce su CPU, nessun modello da scaricare, e
premia le parole rare come i nomi di funzioni che le domande citano.
"""

import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm

from src.indexer import walk
from src.models import MinimalSource

INDEX_FILE = "index.pkl"
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
# pieces of an identifier: HTTPServer -> HTTP, Server; get_kv2 -> get, kv, 2
PART_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it its of "
    "on or that the this to was what when where which who why will with "
    "you your vllm".split()
)


def tokenize(text: str) -> list[str]:
    """Trasforma un testo nei termini per BM25.

    Usata sia sui chunk (`build_index`) sia sulle domande (`search`): BM25
    confronta solo termini identici, quindi qui si decide cosa combacia.
    - Identificatori interi (`get_kv_cache`) per le citazioni esatte, più
      le parti snake/camelCase (`get`, `kv`, `cache`) per le parafrasi.
    - Tutto minuscolo; via le `STOPWORDS` (parole ovunque, inclusa "vllm").
    """
    terms: list[str] = []
    for word in WORD_RE.findall(text):
        terms.append(word.lower())
        parts = PART_RE.findall(word)
        if len(parts) > 1:
            terms += [p.lower() for p in parts]
    return [t for t in terms if t not in STOPWORDS]


def build_index(
    raw_dir: str, processed_dir: str, max_chunk_size: int
) -> int:
    """Taglia il corpus, costruisce BM25 e lo salva in `index.pkl`.

    Cuore del comando `index`; dopo, ogni ricerca ricarica l'indice pronto.
    - Il percorso si tokenizza col chunk: una domanda su LoRA favorisce
      `docs/features/lora.md`.
    - Si salvano solo (percorso, inizio, fine), non il testo: `read_source`
      lo rilegge quando serve.
    - Limite 2000: oltre, la moulinette rifiuta le fonti.

    Returns:
        Numero di chunk indicizzati.

    Raises:
        ValueError: `max_chunk_size` fuori da 1-2000, cartella assente o
            senza file da indicizzare.
    """
    if not 1 <= max_chunk_size <= 2000:
        raise ValueError("max_chunk_size must be between 1 and 2000")
    if not Path(raw_dir).is_dir():
        raise ValueError(f"corpus directory not found: {raw_dir}")
    chunks = walk(raw_dir, max_chunk_size)
    if not chunks:
        raise ValueError(f"no .py/.md/.txt files under {raw_dir}")
    corpus = [tokenize(c.file_path + "\n" + c.content)
              for c in tqdm(chunks, desc="Tokenizing", unit="chunk")]
    index = {
        "sources": [(c.file_path, c.first_character_index,
                     c.last_character_index) for c in chunks],
        "bm25": BM25Okapi(corpus),
    }
    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(processed_dir) / INDEX_FILE, "wb") as f:
        pickle.dump(index, f)
    return len(chunks)


def read_source(source: MinimalSource) -> str:
    """Rilegge dal disco il testo `file[first:last]` di una fonte.

    Usata da `Generator` (contesto per Qwen3) e dalla TUI. Stesse opzioni
    di apertura di `walk`, altrimenti gli indici non combacerebbero.
    """
    with open(source.file_path, encoding="utf-8", errors="replace",
              newline="") as f:
        return f.read()[source.first_character_index:
                        source.last_character_index]


class Retriever:
    """Indice caricato una volta e riusato per tutte le domande.

    Attributes:
        sources: (percorso, inizio, fine) per chunk; l'indice nella lista
            è il numero del chunk in BM25.
        bm25: Il modello BM25.
    """

    def __init__(self, processed_dir: str) -> None:
        """Carica `index.pkl`.

        Raises:
            ValueError: Indice assente; il messaggio dice di lanciare `index`.
        """
        path = Path(processed_dir) / INDEX_FILE
        if not path.is_file():
            raise ValueError(f"no index at {path}, run `index` first")
        # ponytail: pickle trusts the file; fine, only `index` writes it
        with open(path, "rb") as f:
            index: dict[str, Any] = pickle.load(f)
        self.sources: list[tuple[str, int, int]] = index["sources"]
        self.bm25: BM25Okapi = index["bm25"]

    def search(self, query: str, k: int) -> list[MinimalSource]:
        """Restituisce le k fonti con il punteggio BM25 più alto.

        Usata da `search`, `search_dataset`, `answer` e dalla TUI.
        `np.argsort` su tutti i punteggi: semplice e rapido su ~14k chunk.
        I chunk a punteggio 0 non hanno parole in comune con la domanda e si
        scartano: una domanda senza senso dà [] e non k fonti a caso.

        Returns:
            Fino a k fonti, la migliore per prima.
        """
        terms = tokenize(query)
        if not terms:
            return []
        scores = self.bm25.get_scores(terms)
        best = np.argsort(-scores)[:k]
        return [MinimalSource(file_path=p, first_character_index=a,
                              last_character_index=b)
                for p, a, b in (self.sources[i] for i in best
                                if scores[i] > 0)]


if __name__ == "__main__":
    assert tokenize("How does HTTPServer call get_kv2?") == [
        "httpserver", "http", "server", "call", "get_kv2", "get", "kv", "2"]
    assert tokenize("the of ???") == []
    print("ok")
