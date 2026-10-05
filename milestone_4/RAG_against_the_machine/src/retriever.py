"""Indice BM25 (la "R" di RAG): costruirlo, salvarlo, interrogarlo.

Tre modalità di ricerca:
- `bm25` (default): BM25Okapi sui termini dei chunk;
- `embeddings`: similarità coseno con all-MiniLM-L6-v2 (bonus 1);
- `hybrid`: le due classifiche fuse con RRF (bonus 2).

Senza il flag e senza `embeddings.pkl` il comportamento è quello
originale, bit per bit: la moulinette non deve mai vedere un cambio.
"""

import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm

from src.embedder import EMBED_CHARS, Embedder
from src.indexer import Chunk, read_file_text, walk
from src.models import MinimalSource

INDEX_FILE = "index.pkl"
EMBEDDINGS_FILE = "embeddings.pkl"
RETRIEVAL_MODES = ("bm25", "hybrid", "embeddings")
RETRIEVAL_CHOICES = "/".join(RETRIEVAL_MODES)
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
# pieces of an identifier: HTTPServer -> HTTP, Server; get_kv2 -> get, kv, 2
PART_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it its of "
    "on or that the this to was what when where which who why will with "
    "you your vllm".split()
)
# RRF constant (Robertson's 60): smooths 1/(k+rank) so the two ranking
# scales never fight.
RRF_K = 60
# min per-variant list size for the hybrid fusion (grows with k)
FUSION_K = 15


def tokenize(text: str, part_identifiers: bool = True) -> list[str]:
    """Trasforma un testo nei termini per BM25.

    Usata sia sui chunk (`build_index`) sia sulle domande (`search`): BM25
    confronta solo termini identici, quindi qui si decide cosa combacia.
    - Identificatori interi (`get_kv_cache`) per le citazioni esatte, più
      le parti snake/camelCase (`get`, `kv`, `cache`) per le parafrasi,
      se `part_identifiers`.
    - Tutto minuscolo; via le `STOPWORDS` (parole ovunque, inclusa "vllm").
    """
    terms: list[str] = []
    for word in WORD_RE.findall(text):
        terms.append(word.lower())
        if part_identifiers:
            parts = PART_RE.findall(word)
            if len(parts) > 1:
                terms += [p.lower() for p in parts]
    return [t for t in terms if t not in STOPWORDS]


def _chunk_terms(chunk: Chunk) -> list[str]:
    """Termini di un chunk: il percorso conta (una domanda su LoRA
    favorisce `docs/features/lora.md`)."""
    return tokenize(chunk.file_path + "\n" + chunk.content)


def _file_info(paths: list[str]) -> dict[str, tuple[float, int]]:
    """(mtime, size) per file, il sigillo dell'indice incrementale."""
    info: dict[str, tuple[float, int]] = {}
    for path in paths:
        try:
            stat = Path(path).stat()
        except OSError:
            continue
        info[path] = (stat.st_mtime, stat.st_size)
    return info


def build_index(
    raw_dir: str, processed_dir: str, max_chunk_size: int,
    *, embeddings: bool = False, incremental: bool = False,
) -> int:
    """Taglia il corpus, costruisce BM25 e lo salva in `index.pkl`.

    Cuore del comando `index`; dopo, ogni ricerca ricarica l'indice pronto.
    - Si salvano i termini per chunk (`terms`) e, per file, (mtime, size)
      (`file_info`): `incremental` non deve rileggere i file invariati.
    - Limite 2000: oltre, la moulinette rifiuta le fonti.

    Args:
        raw_dir: Cartella del corpus.
        processed_dir: Dove scrivere gli indici.
        max_chunk_size: Da 1 a 2000, la dimensione massima di un chunk.
        embeddings: Codifica anche ogni chunk (testo tagliato a
            `EMBED_CHARS`) in un vettore all-MiniLM normalizzato,
            salvato in `embeddings.pkl` accanto all'indice (bonus 1+2).
        incremental: Se un indice precedente con lo stesso
            `max_chunk_size` esiste, i file invariati (stesso mtime e
            size) riusano i chunk e i termini già calcolati: si
            ricreano solo i file nuovi o cambiati (bonus 3).

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

    previous: dict[str, Any] | None = None
    if incremental:
        previous = _load_index_pkl(Path(processed_dir) / INDEX_FILE)
        if previous is not None and previous.get("max_chunk_size") \
                != max_chunk_size:
            tqdm.write("max_chunk_size changed: full re-index")
            previous = None

    chunks = walk(raw_dir, max_chunk_size)
    if not chunks:
        raise ValueError(f"no .py/.md/.txt files under {raw_dir}")

    corpus: list[list[str]]
    if previous is None:
        corpus = [_chunk_terms(c)
                  for c in tqdm(chunks, desc="Tokenizing", unit="chunk")]
        changed: list[str] = []
    else:
        chunks, corpus, changed = _merge_incremental(previous, chunks)
        tqdm.write(
            f"Incremental: re-indexed {len(changed)} file(s), "
            f"reused {len({c.file_path for c in chunks}) - len(changed)}")

    index: dict[str, Any] = {
        "sources": [(c.file_path, c.first_character_index,
                     c.last_character_index) for c in chunks],
        "terms": corpus,
        "bm25": BM25Okapi(corpus),
        "max_chunk_size": max_chunk_size,
        "file_info": _file_info(sorted({c.file_path for c in chunks})),
    }
    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    with open(Path(processed_dir) / INDEX_FILE, "wb") as f:
        pickle.dump(index, f)
    if embeddings:
        _save_embeddings(processed_dir, previous, chunks, changed)
    return len(chunks)


def _load_index_pkl(path: Path) -> dict[str, Any] | None:
    """Carica un `index.pkl` precedente per `incremental` (None se assente).

    Un file corrotto non deve far crollare `index`: si riparte da zero.
    """
    if not path.is_file():
        return None
    try:
        with open(path, "rb") as f:
            index: Any = pickle.load(f)
    except (OSError, pickle.UnpicklingError, EOFError) as e:
        tqdm.write(f"ignoring unreadable index {path}: {e}")
        return None
    return index if isinstance(index, dict) and "sources" in index else None


def _merge_incremental(
    previous: dict[str, Any],
    chunks: list[Chunk],
) -> tuple[list[Chunk], list[list[str]], list[str]]:
    """(Bonus 3) Riusa chunk e termini dei file invariati.

    "Invariato" = stesso (mtime, size) in `file_info` per il file;
    `max_chunk_size` è già stato paragonato in `build_index`, quindi
    stessi confini = stesso file. I `terms` si riusano da `index.pkl`.
    Le liste restano ordinate come da `walk` (file in ordine
    alfabetico), quindi gli indici combaciano con `sources` e con la
    matrice degli embedding.

    Returns:
        (chunk riassemblati, termini per chunk, file ricreati).
    """
    old_sources = previous.get("sources", [])
    old_terms = previous.get("terms", [])
    old_info = previous.get("file_info", {})
    reusable: dict[str, list[tuple[tuple[int, int], list[str]]]] = {}
    for i, (fp, a, b) in enumerate(old_sources):
        if i < len(old_terms):
            reusable.setdefault(fp, []).append(((a, b), old_terms[i]))

    out: list[Chunk] = []
    terms: list[list[str]] = []
    changed: set[str] = set()
    # group chunks by file, walk() yields a file's chunks contiguously
    file_groups: list[tuple[str, list[Chunk]]] = []
    for c in chunks:
        if file_groups and file_groups[-1][0] == c.file_path:
            file_groups[-1][1].append(c)
        else:
            file_groups.append((c.file_path, [c]))
    for fp, file_chunks in file_groups:
        pairs = reusable.get(fp, [])
        info = _file_info([fp]).get(fp)
        same_bounds = [p for p, _ in pairs] == [
            (c.first_character_index, c.last_character_index)
            for c in file_chunks]
        if len(pairs) == len(file_chunks) and same_bounds \
                and info is not None and info == old_info.get(fp):
            out += file_chunks
            terms += [t for _, t in pairs]
        else:
            changed.add(fp)
            for c in file_chunks:
                out.append(c)
                terms.append(_chunk_terms(c))
    return out, terms, sorted(changed)


def _save_embeddings(
    processed_dir: str,
    previous: dict[str, Any] | None,
    chunks: list[Chunk],
    changed: list[str],
) -> None:
    """(Bonus 1+2) Codifica i chunk in `embeddings.pkl`.

    Senza indice precedente (o matrice) codifica tutto il corpus;
    con `incremental` ricodifica solo i chunk dei file in `changed`, gli
    altri riprendono la loro riga dalla matrice precedente cercandola per
    (percorso, inizio, fine): file aggiunti o tolti spostano le righe.
    Righe = chunk, nell'ordine di `sources`; vettori normalizzati, così
    il coseno è un dot product.
    """
    old: Any = None
    old_rows: dict[tuple[str, int, int], int] = {}
    old_path = Path(processed_dir) / EMBEDDINGS_FILE
    if previous is not None and old_path.is_file():
        with open(old_path, "rb") as f:
            old = pickle.load(f)
        old_rows = {s: i for i, s in enumerate(previous["sources"])}
        if not isinstance(old, np.ndarray) or old.shape[0] != len(old_rows):
            old = None
    stale = set(changed)
    keys = [(c.file_path, c.first_character_index, c.last_character_index)
            for c in chunks]
    todo = [i for i, key in enumerate(keys)
            if old is None or key[0] in stale]
    fresh = iter(Embedder().encode(
        [chunks[i].content[:EMBED_CHARS] for i in todo],
        show_progress_bar=True)) if todo else iter([])
    todo_set = set(todo)
    matrix = np.stack([next(fresh) if i in todo_set else old[old_rows[key]]
                       for i, key in enumerate(keys)])
    with open(old_path, "wb") as f:
        pickle.dump(matrix.astype(np.float32), f)


def read_source(source: MinimalSource) -> str:
    """Rilegge dal disco il testo `file[first:last]` di una fonte.

    Usata da `Generator` (contesto per Qwen3) e dalla TUI.
    """
    return read_file_text(source.file_path)[
        source.first_character_index:source.last_character_index]


class Retriever:
    """Indice caricato una volta e riusato per tutte le domande.

    Attributes:
        sources: (percorso, inizio, fine) per chunk; l'indice nella lista
            è il numero del chunk in BM25.
        bm25: Il modello BM25.
        retrieval: modalità di ricerca di default (`bm25`).
        _embeddings: matrice (n_chunk, 384) di vettori normalizzati,
            caricata a prima ricerca che ne ha bisogno.
        _cache: (modalità, domanda, k) -> indici; le query ripetute nello
            stesso processo non ricomputano (bonus 4).
    """

    def __init__(self, processed_dir: str,
                 retrieval: str = "bm25", *, cache: bool = True) -> None:
        """Carica `index.pkl` (e, a uso, `embeddings.pkl`).

        Args:
            processed_dir: Cartella dell'indice.
            retrieval: `bm25` (default), `hybrid` o `embeddings`.
            cache: Abilita la cache in memoria dei risultati (bonus 4).

        Raises:
            ValueError: Indice assente; il messaggio dice di lanciare
                `index`.
        """
        if retrieval not in RETRIEVAL_MODES:
            raise ValueError(f"retrieval must be one of "
                             f"{RETRIEVAL_CHOICES}, got {retrieval!r}")
        path = Path(processed_dir) / INDEX_FILE
        if not path.is_file():
            raise ValueError(f"no index at {path}, run `index` first")
        # ponytail: pickle trusts the file; fine, only `index` writes it
        with open(path, "rb") as f:
            index: dict[str, Any] = pickle.load(f)
        self.sources: list[tuple[str, int, int]] = index["sources"]
        self.bm25: BM25Okapi = index["bm25"]
        self.retrieval = retrieval
        self._cache_enabled = cache
        self._cache: dict[tuple[str, str, int], list[int]] = {}
        self._processed_dir = processed_dir
        self._embeddings: np.ndarray | None = None
        self._embeddings_loaded = False
        self._embedder: Embedder | None = None

    def _load_embed_matrix(self) -> np.ndarray | None:
        """Carica `embeddings.pkl` una volta; None se non esiste (o non
        combacia col numero di chunk: indice parzialmente ricostruito)."""
        if not self._embeddings_loaded:
            self._embeddings_loaded = True
            path = Path(self._processed_dir) / EMBEDDINGS_FILE
            if path.is_file():
                with open(path, "rb") as f:
                    matrix: Any = pickle.load(f)
                if isinstance(matrix, np.ndarray) \
                        and matrix.shape[0] == len(self.sources):
                    self._embeddings = matrix
        return self._embeddings

    def _bm25_ranking(self, query: str, k: int) -> list[int]:
        """Indici dei k chunk BM25 migliori.

        `np.argsort` su tutti i punteggi: semplice e rapido su ~14k chunk.
        I chunk a punteggio 0 non hanno parole in comune con la domanda e
        si scartano: una domanda senza senso dà [] e non k fonti a caso.
        """
        terms = tokenize(query)
        if not terms:
            return []
        scores = self.bm25.get_scores(terms)
        return [int(i) for i in np.argsort(-scores)[:k] if scores[i] > 0]

    def _embedding_ranking(self, query: str, k: int) -> list[int]:
        """Indici dei k chunk più simili; [] se la matrice non c'è.

        Coseno = dot product: i vettori sono normalizzati alla
        codifica. La domanda non si taglia: è corta per natura.
        """
        matrix = self._load_embed_matrix()
        if matrix is None:
            return []
        if self._embedder is None:
            self._embedder = Embedder()
        vector = self._embedder.encode([query])[0]
        return [int(i) for i in np.argsort(-(matrix @ vector))[:k]]

    @staticmethod
    def _fuse(rankings: list[list[int]]) -> list[int]:
        """Fusione RRF di più classifiche: score = Σ 1/(RRF_K + rank).

        I punteggi BM25 e i coseni non sono mai sulla stessa scala, ma il
        rango sì: RRF (k=60, Robertson) rende la fusione immune ai
        problemi di scala. Rank 0-based: la prima posizione vale
        1/(RRF_K+1).
        """
        scores: dict[int, float] = {}
        for ranking in rankings:
            for rank, i in enumerate(ranking):
                scores[i] = scores.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        return sorted(scores, key=lambda i: scores[i], reverse=True)

    def search(self, query: str, k: int,
               retrieval: str | None = None) -> list[MinimalSource]:
        """Restituisce le k fonti migliori nella modalità `retrieval`.

        Usata da `search`, `search_dataset`, `answer`, `api` e dalla TUI.
        `retrieval` None usa quello del costruttore (default `bm25`).
        - `bm25`: la via d'origine, stessi risultati di prima.
        - `embeddings`: top-k per similarità coseno; senza
          `embeddings.pkl` cade su `bm25` con un avviso, mai un crash.
        - `hybrid`: RRF sulle due classifiche (stessa caduta).
        I risultati passano per la cache in memoria (bonus 4).

        Returns:
            Fino a k fonti, la migliore per prima.

        Raises:
            ValueError: `k < 1` o `retrieval` non valida.
        """
        mode = retrieval if retrieval is not None else self.retrieval
        if mode not in RETRIEVAL_MODES:
            raise ValueError(
                f"retrieval must be one of {RETRIEVAL_CHOICES}, got {mode!r}")
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        key = (mode, query, k)
        cached = self._cache.get(key) if self._cache_enabled else None
        if cached is not None:
            return self._to_sources(cached)
        n = max(k, FUSION_K)
        semantic = [] if mode == "bm25" else self._embedding_ranking(query, n)
        if not semantic:
            if mode != "bm25":
                tqdm.write("no embeddings index, using bm25 only "
                           "(run `index --embeddings`)")
            indices = self._bm25_ranking(query, k)
        elif mode == "embeddings":
            indices = semantic[:k]
        else:
            indices = self._fuse(
                [self._bm25_ranking(query, n), semantic])[:k]
        if self._cache_enabled:
            self._cache[key] = indices
        return self._to_sources(indices)

    def _to_sources(self, indices: list[int]) -> list[MinimalSource]:
        """Indici dei chunk -> fonti (stesso ordine)."""
        return [MinimalSource(file_path=p, first_character_index=a,
                              last_character_index=b)
                for p, a, b in (self.sources[i] for i in indices)]


if __name__ == "__main__":
    assert tokenize("How does HTTPServer call get_kv2?") == [
        "httpserver", "http", "server", "call", "get_kv2", "get", "kv", "2"]
    assert tokenize("the of ???") == []
    assert tokenize("get_kv2", part_identifiers=False) == ["get_kv2"]
    print("ok")
