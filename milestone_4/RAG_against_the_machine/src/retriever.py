"""BM25 index: build it from the corpus, persist it, query it."""

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
    """Split text into lowercase BM25 terms.

    Every identifier is kept whole (to match a verbatim quote) and also
    split into its snake_case/camelCase parts (to match a paraphrase).

    Args:
        text: Question or chunk text.

    Returns:
        Terms, stopwords removed.
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
    """Chunk the corpus, build BM25 over it and pickle it.

    The file path is tokenized with each chunk: a question about LoRA
    should favour docs/features/lora.md.

    Args:
        raw_dir: Corpus root.
        processed_dir: Where index.pkl is written.
        max_chunk_size: Maximum chunk span, 1 to 2000.

    Returns:
        Number of indexed chunks.

    Raises:
        ValueError: If max_chunk_size is out of range or the corpus is
            empty.
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


class Retriever:
    """A loaded index, reused across queries."""

    def __init__(self, processed_dir: str) -> None:
        """Load index.pkl.

        Args:
            processed_dir: Directory holding index.pkl.

        Raises:
            ValueError: If there is no index yet.
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
        """Return the k best-scoring chunks for query.

        Args:
            query: Natural-language question.
            k: Number of results wanted, >= 1.

        Returns:
            Up to k sources, best first. Chunks sharing no term with the
            query are never returned, so a nonsense query gives [].
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
