"""Modelli Pydantic: la forma di ogni file JSON letto o scritto.

Il formato è imposto dal subject (la moulinette rifiuta file sbagliati).
`model_validate_json` controlla i file letti, `model_dump_json` scrive
sempre la forma giusta.
"""

import uuid
from typing import List, Union

from pydantic import BaseModel, Field

__all__ = [
    "MinimalSource",
    "UnansweredQuestion",
    "AnsweredQuestion",
    "RagDataset",
    "MinimalSearchResults",
    "MinimalAnswer",
    "StudentSearchResults",
    "StudentSearchResultsAndAnswer",
]


class MinimalSource(BaseModel):
    """Un pezzo di file del corpus: `file[first:last]`. È una "fonte".

    Creata da `Retriever.search`; per la moulinette è giusta se sta nello
    stesso file della fonte vera e si sovrappone con IoU >= 0.05.
    """

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """Una domanda; senza `question_id` ne riceve uno casuale (UUID)."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """Una domanda con fonti e risposta vere. Usata da `evaluate`."""

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """Un file di dataset; la `Union` accetta domande con o senza risposta."""

    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    """Le k fonti migliori trovate per una domanda, in ordine."""

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Risultati della ricerca più la risposta di Qwen3."""

    answer: str


class StudentSearchResults(BaseModel):
    """File scritto da `search_dataset`, valutato dalla moulinette.

    Ogni fonte deve stare sotto i 2000 caratteri, altrimenti la moulinette
    rifiuta tutto il file.
    """

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """File scritto da `answer_dataset`: fonti più risposta per domanda."""

    search_results: List[MinimalAnswer]
    k: int
