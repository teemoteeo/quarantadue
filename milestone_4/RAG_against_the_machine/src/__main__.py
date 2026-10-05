"""CLI del progetto: `uv run python -m src <comando>` (Python Fire).

Ogni funzione pubblica è un comando; i suoi argomenti diventano opzioni.
I comandi collegano solo i pezzi: ricerca in `retriever`, risposta in
`generator`, formati JSON in `models`.
Ordine: `index`, `search_dataset`, moulinette, `answer_dataset`.
"""

import sys
from pathlib import Path

import fire
from pydantic import ValidationError
from tqdm import tqdm

from src.models import (
    AnsweredQuestion, MinimalAnswer, MinimalSearchResults, MinimalSource,
    RagDataset, StudentSearchResults, StudentSearchResultsAndAnswer,
)
from src.retriever import RETRIEVAL_CHOICES, RETRIEVAL_MODES, Retriever, \
    build_index

PROCESSED_DIR = "data/processed"


def _query(query: object) -> str:
    """Controlla che la domanda non sia vuota e la restituisce come testo.

    Tipo `object`: Fire converte da solo, `search 42` arriva come int.
    """
    text = str(query).strip()
    if not text:
        raise ValueError("query is empty")
    return text


def _positive(value: object, name: str = "k") -> int:
    """Controlla che un argomento sia un intero >= 1 (es. `k=0` rifiutato).

    `bool` escluso a parte: `True` è un int, e `--k` senza valore arriva
    da Fire proprio come `True`.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return value


def _retrieval(value: object) -> str:
    """Controlla la modalità di ricerca (bm25/hybrid/embeddings)."""
    if value not in RETRIEVAL_MODES:
        raise ValueError(
            f"retrieval must be one of {RETRIEVAL_CHOICES}, got {value!r}")
    return str(value)


def _save(model: StudentSearchResults | StudentSearchResultsAndAnswer,
          save_directory: str, name: str) -> Path:
    """Salva il modello in JSON in `save_directory/name` (crea la cartella)."""
    out = Path(save_directory) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return out


def _print_sources(sources: list[MinimalSource]) -> None:
    """Stampa una riga `percorso [inizio:fine]` per fonte."""
    if not sources:
        print("No matching sources.")
    for s in sources:
        print(f"{s.file_path} "
              f"[{s.first_character_index}:{s.last_character_index}]")


def index(max_chunk_size: int = 2000, *, embeddings: bool = False,
          incremental: bool = False, raw_dir: str = "data/raw",
          processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `index`: crea l'indice BM25 (vedi `build_index`), una volta.

    Args:
        max_chunk_size: Lunghezza massima di un chunk, da 1 a 2000.
        embeddings: Bonus 1+2: salva anche la matrice dei vettori
            all-MiniLM (embeddings.pkl); serve a `--retrieval embeddings`
            e `hybrid`. Il default (False) lascia il comportamento
            d'origine.
        incremental: Bonus 3: con un indice precedente, ricrea solo i
            file nuovi o cambiati.
        raw_dir: Cartella del corpus.
        processed_dir: Dove scrivere l'indice.
    """
    size = _positive(max_chunk_size, "max_chunk_size")
    n = build_index(raw_dir, processed_dir, size, embeddings=embeddings,
                    incremental=incremental)
    print(f"Ingestion complete! Indexed {n} chunks under {processed_dir}/")


def search(query: str, k: int = 5, *, retrieval: str = "bm25",
           no_cache: bool = False,
           processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `search`: stampa le k fonti migliori per una domanda.

    Args:
        query: La domanda.
        k: Fonti da stampare.
        retrieval: `bm25` (default), `hybrid` o `embeddings` (bonus 1+2).
        no_cache: Bonus 4: ignora e non scrive `query_cache.json`.
        processed_dir: Dove si trova l'indice.
    """
    text, k, retrieval = _query(query), _positive(k), _retrieval(retrieval)
    retriever = Retriever(processed_dir, retrieval=retrieval,
                          cache=not no_cache)
    _print_sources(retriever.search(text, k))
    retriever.save_cache()


def search_dataset(dataset_path: str, save_directory: str, k: int = 10, *,
                   retrieval: str = "bm25", no_cache: bool = False,
                   processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `search_dataset`: cerca le fonti di ogni domanda.

    Scrive il file valutato dalla moulinette, col nome del dataset.
    Un solo `Retriever` per tutte le domande: caricarlo è la parte lenta.

    Args:
        dataset_path: Dataset JSON (`RagDataset`).
        save_directory: Cartella di uscita.
        k: Fonti per domanda.
        retrieval: `bm25` (default), `hybrid` o `embeddings` (bonus 1+2).
        no_cache: Bonus 4: ignora e non scrive `query_cache.json`.
        processed_dir: Dove si trova l'indice.
    """
    k, retrieval = _positive(k), _retrieval(retrieval)
    dataset = RagDataset.model_validate_json(
        Path(dataset_path).read_text(encoding="utf-8"))
    retriever = Retriever(processed_dir, retrieval=retrieval,
                          cache=not no_cache)
    results = StudentSearchResults(k=k, search_results=[
        MinimalSearchResults(
            question_id=q.question_id, question=q.question,
            retrieved_sources=retriever.search(q.question, k))
        for q in tqdm(dataset.rag_questions, desc="Searching", unit="q")
    ])
    retriever.save_cache()
    out = _save(results, save_directory, Path(dataset_path).name)
    print(f"Saved student_search_results to {out}")


def answer(query: str, k: int = 5, *, retrieval: str = "bm25",
           no_cache: bool = False,
           processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `answer`: tutta la pipeline RAG su una domanda.

    Stampa fonti e risposta. `Generator` si importa qui e non in cima:
    porta `torch`, lento, e i comandi senza generazione restano veloci.

    Args:
        query: La domanda.
        k: Fonti da usare come contesto.
        retrieval: `bm25` (default), `hybrid` o `embeddings` (bonus 1+2).
        no_cache: Bonus 4: ignora e non scrive `query_cache.json`.
        processed_dir: Dove si trova l'indice.
    """
    from src.generator import Generator  # torch import is slow

    text, k, retrieval = _query(query), _positive(k), _retrieval(retrieval)
    retriever = Retriever(processed_dir, retrieval=retrieval,
                          cache=not no_cache)
    sources = retriever.search(text, k)
    retriever.save_cache()
    _print_sources(sources)
    print("\n" + Generator().answer(text, sources))


def answer_dataset(student_search_results_path: str,
                   save_directory: str) -> None:
    """Comando `answer_dataset`: risponde a ogni domanda di un file.

    Usa le fonti già trovate da `search_dataset` (nessuna nuova ricerca)
    e un solo `Generator` per tutto il file.

    Args:
        student_search_results_path: File scritto da `search_dataset`.
        save_directory: Cartella di uscita.
    """
    from src.generator import Generator  # torch import is slow

    path = Path(student_search_results_path)
    results = StudentSearchResults.model_validate_json(
        path.read_text(encoding="utf-8"))
    print(f"Loaded {len(results.search_results)} questions")
    generator = Generator()
    answers = StudentSearchResultsAndAnswer(k=results.k, search_results=[
        MinimalAnswer(**r.model_dump(),
                      answer=generator.answer(r.question,
                                              r.retrieved_sources))
        for r in tqdm(results.search_results, desc="Answering", unit="q")
    ])
    out = _save(answers, save_directory, path.name)
    print(f"Saved student_search_results_and_answer to {out}")


def _found(truth: MinimalSource, got: list[MinimalSource]) -> bool:
    """True se una fonte vera è stata trovata (stessa regola della moulinette).

    Conta se è nello stesso file con IoU >= 0.05, dove IoU = caratteri in
    comune / caratteri coperti da almeno una delle due.
    """
    for s in got:
        if s.file_path != truth.file_path:
            continue
        inter = (min(s.last_character_index, truth.last_character_index)
                 - max(s.first_character_index,
                       truth.first_character_index))
        union = (s.last_character_index - s.first_character_index
                 + truth.last_character_index
                 - truth.first_character_index - inter)
        if inter > 0 and inter / union >= 0.05:
            return True
    return False


def evaluate(student_search_results_path: str, dataset_path: str) -> None:
    """Comando `evaluate`: stampa recall@1/3/5/10 per test locali.

    Il punteggio ufficiale è della moulinette, che non possiamo chiamare:
    la sua regola è rifatta in `_found`. Recall@k = quota di fonti vere
    trovate nei primi k, media sulle domande.

    Args:
        student_search_results_path: File scritto da `search_dataset`.
        dataset_path: Dataset con le risposte vere.
    """
    results = StudentSearchResults.model_validate_json(
        Path(student_search_results_path).read_text(encoding="utf-8"))
    dataset = RagDataset.model_validate_json(
        Path(dataset_path).read_text(encoding="utf-8"))
    got = {r.question_id: r.retrieved_sources
           for r in results.search_results}
    truths = [(q.question_id, q.sources) for q in dataset.rag_questions
              if isinstance(q, AnsweredQuestion) and q.sources]
    if not truths:
        raise ValueError(f"no answered questions in {dataset_path}")
    print(f"Questions evaluated: {len(truths)}")
    for k in (1, 3, 5, 10):
        recall = sum(
            sum(_found(t, got.get(qid, [])[:k]) for t in sources)
            / len(sources)
            for qid, sources in truths) / len(truths)
        print(f"Recall@{k}: {recall:.3f} ({recall:.1%})")


def tui(*, processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `tui`: interfaccia interattiva (extra, non nel subject)."""
    from src.tui import run_tui

    run_tui(processed_dir)


def api(port: int = 8000, *, host: str = "127.0.0.1",
        retrieval: str = "bm25", no_cache: bool = False,
        processed_dir: str = PROCESSED_DIR) -> None:
    """Comando `api` (bonus 5): serve /search e /answer su un HTTP locale.

    Il modello Qwen3 si carica pigro alla prima richiesta /answer.
    Ctrl+C ferma il server.

    Args:
        port: Porta da ascoltare.
        host: Interfaccia da ascoltare (default: solo la macchina locale).
        retrieval: `bm25` (default), `hybrid` o `embeddings`.
        no_cache: Bonus 4: ignora e non scrive `query_cache.json`.
        processed_dir: Dove si trova l'indice.
    """
    from src.api import Api, serve

    _positive(port, "port")
    _retrieval(retrieval)
    server = Api(processed_dir, retrieval=retrieval, cache=not no_cache)
    serve(server, host, port)


def main() -> None:
    """Avvia Fire; ogni errore diventa una riga `Error: ...`, mai un traceback.

    Solo le funzioni nel dizionario sono comandi. Ctrl+C esce con 130.
    """
    try:
        fire.Fire({
            "index": index, "search": search,
            "search_dataset": search_dataset, "answer": answer,
            "answer_dataset": answer_dataset, "evaluate": evaluate,
            "tui": tui, "api": api,
        })
    except KeyboardInterrupt:
        sys.exit(130)
    except ValidationError as e:  # pydantic's own dump is several lines
        first = e.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "input"
        print(f"Error: invalid {e.title} JSON ({e.error_count()} error(s)),"
              f" first at {where}: {first['msg']}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # the subject forbids tracebacks at the CLI
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
