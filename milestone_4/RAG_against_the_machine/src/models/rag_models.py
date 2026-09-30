"""Pydantic data models for the RAG pipeline."""

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
    """A span of a corpus file, as file[first:last]."""

    file_path: str
    first_character_index: int
    last_character_index: int


class UnansweredQuestion(BaseModel):
    """A question, with a random UUID when none is given."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str


class AnsweredQuestion(UnansweredQuestion):
    """A question with its ground-truth sources and answer."""

    sources: List[MinimalSource]
    answer: str


class RagDataset(BaseModel):
    """A dataset file: answered and/or unanswered questions."""

    rag_questions: List[Union[AnsweredQuestion, UnansweredQuestion]]


class MinimalSearchResults(BaseModel):
    """The top-k sources retrieved for one question."""

    question_id: str
    question: str
    retrieved_sources: List[MinimalSource]


class MinimalAnswer(MinimalSearchResults):
    """Search results plus the generated answer."""

    answer: str


class StudentSearchResults(BaseModel):
    """Output of search_dataset, read by the moulinette."""

    search_results: List[MinimalSearchResults]
    k: int


class StudentSearchResultsAndAnswer(BaseModel):
    """Output of answer_dataset."""

    search_results: List[MinimalAnswer]
    k: int
