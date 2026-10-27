"""Secondo passo del processo, la 'R' in RAG. Dopo aver
creato l'indice di tutti i chunk, li devo preparare allo
scoring BM25. Creo una funzione tokenize() da applicare
sia ai chunk sia alle domande e poi uso la libreria importata
per selezionare i k chunk con i punteggi BM25 piu' alti"""

import re
import json

import numpy as np
from tqdm import tqdm
from pathlib import Path
from rank_bm25 import BM25Okapi

from .models import MinimalSearchResults, MinimalSource,\
        RagDataset, StudentSearchResults
from .chunkdexing import Chunk, INDEX_PATH


STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it its of "
    "on or that the this to was what when where which who why will with "
    "you your vllm".split()
    )
# Prendi ogni sequenza di lettere, cifre e underscore. Tutto il resto
# e' separatore
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
# Dentro una parola, prendi in ordine le sigle, le parole con al
# massimo l'iniziale maiuscola e i numeri
PART_RE = re.compile(r"[A-Z]+s?(?![a-z])|[A-Z]?[a-z]+|\d+")


def tokenize(content: str) -> list[str]:
    """Tokenizza sia tutti i chunk sia le domande e tiene
    per ognuno solo i token rilevanti, scarta direttamente il
    resto dalla lista"""
    tokens: list[str] = []
    for word in WORD_RE.findall(content):
        parts = PART_RE.findall(word)
        if parts != [word]:
            tokens += [p.lower() for p in parts]
        tokens.append(word.lower())
    return [t for t in tokens if t not in STOPWORDS]


def to_source(chunk: Chunk) -> MinimalSource:
    """Converto oggetti Chunk in MinimalSource come richiesto
    da subject."""
    return MinimalSource(file_path=chunk.file_path,
                         first_character_index=chunk.first_index,
                         last_character_index=chunk.last_index)


class GoldenRetriever:
    """La classe verra' costruita intorno all'idea del
    comportamento di un cane che sente parole trigger,
    un golden retriever in questo caso.
    La classe viene inizializzata con il path dell'indice e
    crea una sola volta un oggetto bm25 che poi attraversoo
    il metodo retrieve() viene usata confrontando una query
    qualsiasi e l'intero corpus di vLLM senza bisogno di
    caricarlo ogni volta"""

    def __init__(self, index_path: Path = INDEX_PATH) -> None:
        with open(index_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        self.chunks = [Chunk(**x) for x in d]
        self.bm25 = BM25Okapi([tokenize(s.content) for s in self.chunks])

    def retrieve(self, query: str, k: int) -> list[Chunk]:
        """Torna le posizioni dei k chunk con il punteggio più alto, scartando
        quelli con punteggio zero, come int Python"""
        if not isinstance(k, int) or k <= 0:
            raise ValueError("k value invalid in retrieving (<= 0 or not int)")
        scores = self.bm25.get_scores(tokenize(query))
        top_k = [int(i) for i in np.argsort(-scores)[:k] if scores[i] > 0]
        return [self.chunks[i] for i in top_k]


def search(query: str, k: int = 5) -> list[MinimalSource]:
    """Metodo di modulo per essere usato nel Fire() nel main.
    Torna le k sources con punteggio bm25 piu' alto."""
    if not query.strip():
        raise ValueError("Empty query!")
    golden = GoldenRetriever()
    return [to_source(source) for source in golden.retrieve(query, k)]


def search_dataset(dataset_path: str,
                   save_directory: str,
                   k: int = 5) -> None:
    """Legge un datasete e applica e cerca k sources per ogni query
    del dataset."""
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be > 0")
    dataset = RagDataset.model_validate_json(
            Path(dataset_path).read_text(encoding="utf-8"))
    golden = GoldenRetriever()
    result = StudentSearchResults(
            search_results=[
                MinimalSearchResults(
                    question_id=q.question_id, question=q.question,
                    retrieved_sources=[
                        to_source(source)
                        for source in golden.retrieve(q.question, k)
                        ])
                for q in tqdm(dataset.rag_questions,
                              desc="Searching", unit="q")],
            k=k)
    output = result.model_dump_json(indent=2)
    output_path = Path(save_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / Path(dataset_path).name
    output_file.write_text(output, encoding="utf-8")
    print(f"Saved student_search_result to {output_file}")
