import fire
import sys

from pathlib import Path

from .chunkdexing import index
from .golden_retrieving import search, search_dataset
from .generating import answer, answer_dataset
from .models import (MinimalSource, StudentSearchResults,
                     RagDataset, AnsweredQuestion)


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
    ks = (1, 3, 5, 10)
    total = {k: 0.0 for k in ks}
    for q_id, sources in truths:
        mine = got.get(q_id, [])
        for k in ks:
            found = sum(_found(s, mine[:k]) for s in sources)
            total[k] += found / len(sources)
    for k in ks:
        print(f"Recall@{k}: {total[k] / len(truths):.3f}")


if __name__ == "__main__":
    try:
        fire.Fire({"index": index, "search": search,
                   "search_dataset": search_dataset,
                   "answer": answer,
                   "answer_dataset": answer_dataset,
                   "evaluate": evaluate})
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
