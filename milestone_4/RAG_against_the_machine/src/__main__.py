"""CLI: uv run python -m src <command> [options]."""

import sys
from pathlib import Path

import fire
from tqdm import tqdm

from src.models import (
    AnsweredQuestion, MinimalAnswer, MinimalSearchResults, MinimalSource,
    RagDataset, StudentSearchResults, StudentSearchResultsAndAnswer,
)
from src.retriever import Retriever, build_index

PROCESSED_DIR = "data/processed"


def _query(query: object) -> str:
    """Validate a query. Fire parses `search 42` as an int, hence object."""
    text = str(query).strip()
    if not text:
        raise ValueError("query is empty")
    return text


def _positive(value: object, name: str = "k") -> int:
    """Validate a positive int argument (bool is an int, reject it too)."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return value


def _save(model: StudentSearchResults | StudentSearchResultsAndAnswer,
          save_directory: str, name: str) -> Path:
    """Write model as JSON to save_directory/name."""
    out = Path(save_directory) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return out


def _print_sources(sources: list[MinimalSource]) -> None:
    """Print one `path [first:last]` line per source."""
    if not sources:
        print("No matching sources.")
    for s in sources:
        print(f"{s.file_path} "
              f"[{s.first_character_index}:{s.last_character_index}]")


def index(max_chunk_size: int = 2000, *, raw_dir: str = "data/raw",
          processed_dir: str = PROCESSED_DIR) -> None:
    """Chunk the corpus and build the BM25 index.

    Args:
        max_chunk_size: Maximum chunk span, 1 to 2000.
        raw_dir: Corpus root.
        processed_dir: Where the index is written.
    """
    size = _positive(max_chunk_size, "max_chunk_size")
    n = build_index(raw_dir, processed_dir, size)
    print(f"Ingestion complete! Indexed {n} chunks under {processed_dir}/")


def search(query: str, k: int = 5, *,
           processed_dir: str = PROCESSED_DIR) -> None:
    """Print the top-k sources for one query.

    Args:
        query: The question.
        k: Number of sources.
        processed_dir: Where the index lives.
    """
    text, k = _query(query), _positive(k)
    _print_sources(Retriever(processed_dir).search(text, k))


def search_dataset(dataset_path: str, save_directory: str, k: int = 10, *,
                   processed_dir: str = PROCESSED_DIR) -> None:
    """Search every question of a dataset, save StudentSearchResults.

    Args:
        dataset_path: RagDataset JSON.
        save_directory: Output directory; the file keeps the dataset name.
        k: Number of sources per question.
        processed_dir: Where the index lives.
    """
    k = _positive(k)
    dataset = RagDataset.model_validate_json(
        Path(dataset_path).read_text(encoding="utf-8"))
    retriever = Retriever(processed_dir)
    results = StudentSearchResults(k=k, search_results=[
        MinimalSearchResults(
            question_id=q.question_id, question=q.question,
            retrieved_sources=retriever.search(q.question, k))
        for q in tqdm(dataset.rag_questions, desc="Searching", unit="q")
    ])
    out = _save(results, save_directory, Path(dataset_path).name)
    print(f"Saved student_search_results to {out}")


def answer(query: str, k: int = 5, *,
           processed_dir: str = PROCESSED_DIR) -> None:
    """Retrieve k sources for one query and answer it with the LLM.

    Args:
        query: The question.
        k: Number of sources given to the model.
        processed_dir: Where the index lives.
    """
    from src.generator import Generator  # torch import is slow

    text, k = _query(query), _positive(k)
    sources = Retriever(processed_dir).search(text, k)
    _print_sources(sources)
    print("\n" + Generator().answer(text, sources))


def answer_dataset(student_search_results_path: str,
                   save_directory: str) -> None:
    """Answer every question of a search results file.

    Args:
        student_search_results_path: StudentSearchResults JSON.
        save_directory: Output directory; the file keeps the input name.
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
    """True if a retrieved source is in the same file with IoU >= 0.05."""
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
    """Print recall@1/3/5/10 of search results against a ground truth.

    Args:
        student_search_results_path: StudentSearchResults JSON.
        dataset_path: RagDataset JSON with AnsweredQuestions.
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


def main() -> None:
    """Run the CLI; any error becomes a one-line message, not a trace."""
    try:
        fire.Fire({
            "index": index, "search": search,
            "search_dataset": search_dataset, "answer": answer,
            "answer_dataset": answer_dataset, "evaluate": evaluate,
        })
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # the subject forbids tracebacks at the CLI
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
