"""Terzo e ultimo passaggio della pipeline. La G in 'RAG'.
Si prendono i k chunk con punteggio bm25 piu' alto e li si
danno in pasto a Qwen 0.6B, dopo l'opportuno setup."""

import sys

from tqdm import tqdm
from pathlib import Path
from .models import (MinimalSource, MinimalAnswer, StudentSearchResults,
                     StudentSearchResultsAndAnswer)
from .chunkdexing import ROOT
from .golden_retrieving import search

MODEL_NAME = "Qwen/Qwen3-0.6B"
SYSTEM_PROMPT = (
    "You answer questions about the vLLM codebase using only the context "
    "snippets provided. Be concise and precise: name the exact functions, "
    "classes, flags or endpoints the context shows. If the context does "
    "not contain the answer, say you could not find it in the sources."
)
NO_CONTEXT_ANSWER = "I could not find the answer in the sources."
MAX_CONTENT_CHARS = 12000


def source_text(source: MinimalSource) -> str:
    file = ROOT / source.file_path
    try:
        result = file.read_text(encoding="utf-8")[
                source.first_character_index:source.last_character_index]
    except (OSError, UnicodeDecodeError) as e:
        print(f"SKIP {source.file_path}: {e!r}", file=sys.stderr)
        return ""
    return result


class Generator:
    """Classe Generator per gestire la generazione della risposta di
    Qwen-0.6B."""
    def __init__(self) -> None:
        import torch  # import lazy: torch costa ~15s
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME, dtype=torch.float32)

    def build_prompt(self,
                     question: str,
                     sources: list[MinimalSource]) -> str:
        context = ""
        for source in sources:
            text = source_text(source)
            if text == "":
                continue
            context += source.file_path + "\n" + text + "\n\n"
        context += "\nQuestion: " + question
        if len(context) > MAX_CONTENT_CHARS:
            context = context[:MAX_CONTENT_CHARS]
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context}]
        return str(self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False))

    def generate(self, question: str, sources: list[MinimalSource]) -> str:
        import torch

        if not sources:
            return NO_CONTEXT_ANSWER
        prompt = self.build_prompt(question, sources)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=128,
                                         do_sample=False)
        new = output[0][inputs["input_ids"].shape[1]:]
        return str(self.tokenizer.decode(new,
                                         skip_special_tokens=True)).strip()


def answer(question: str, k: int = 5) -> None:
    if not question.strip():
        raise ValueError("Empty query!")
    if not isinstance(k, int) or k <= 0:
        raise ValueError("k must be > 0")
    sources = search(question, k)
    generator = Generator()
    qwen_reply = generator.generate(question, sources)
    print(qwen_reply)


def answer_dataset(student_search_results_path: str,
                   save_directory: str) -> None:
    search_results = StudentSearchResults.model_validate_json(
                Path(student_search_results_path).read_text(
                    encoding="utf-8"))
    generator = Generator()
    answers: list[MinimalAnswer] = []
    for r in tqdm(search_results.search_results, desc="Answering",
                  unit="q"):
        answers.append(MinimalAnswer(
            question_id=r.question_id,
            question=r.question,
            retrieved_sources=r.retrieved_sources,
            answer=generator.generate(r.question, r.retrieved_sources)))
    result = StudentSearchResultsAndAnswer(search_results=answers,
                                           k=search_results.k)
    output = result.model_dump_json(indent=2)
    output_path = Path(save_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / Path(student_search_results_path).name
    output_file.write_text(output, encoding="utf-8")
    print(f"Saved student_result_and_answer to {output_file}")
