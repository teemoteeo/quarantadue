"""Risposta con Qwen3 (la "G" di RAG) usando il testo delle fonti.

Il modello non conosce vLLM: legge le fonti nel prompt e risponde solo
da quelle. Importato solo quando serve, perché `torch` è lento.
"""

from collections.abc import Iterator
from threading import Thread
from typing import Any

import torch
from transformers import (
    AutoModelForCausalLM, AutoTokenizer, BatchEncoding, TextIteratorStreamer,
)

from src.models import MinimalSource
from src.retriever import read_source

MODEL_NAME = "Qwen/Qwen3-0.6B"
# ponytail: a char budget, not a token one; 5 sources of 2000 chars is
# ~3-4k tokens, far under Qwen3's 32k window. Count tokens if k grows.
MAX_CONTEXT_CHARS = 12000
GENERATE_KWARGS: dict[str, Any] = {"max_new_tokens": 256, "do_sample": False,
                                   "repetition_penalty": 1.1}
SYSTEM_PROMPT = (
    "You answer questions about the vLLM codebase using only the context "
    "snippets provided. Be concise and precise: name the exact functions, "
    "classes, flags or endpoints the context shows. If the context does "
    "not contain the answer, say you could not find it in the sources."
)
NO_CONTEXT_ANSWER = "I could not find the answer in the sources."


class Generator:
    """Modello caricato una volta e riusato per tutte le domande."""

    def __init__(self) -> None:
        """Carica tokenizer e pesi (scaricati in cache al primo uso).

        `float32` perché su CPU `bfloat16` è circa 6 volte più lento.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME, dtype=torch.float32)  # bf16 is ~6x slower on CPU

    @staticmethod
    def _context(sources: list[MinimalSource]) -> list[str]:
        """Testo delle fonti, ognuna preceduta dal suo percorso.

        Le fonti entrano dalla migliore finché stanno in `MAX_CONTEXT_CHARS`.
        Una fonte illeggibile (file sparito, percorso a mano in un JSON) si
        salta: non deve far perdere tutto un `answer_dataset`.
        """
        context: list[str] = []
        used = 0
        for s in sources:
            try:
                text = f"--- {s.file_path}\n{read_source(s)}"
            except OSError:
                continue
            if used + len(text) > MAX_CONTEXT_CHARS:
                break
            context.append(text)
            used += len(text)
        return context

    def _inputs(self, question: str, context: list[str]) -> BatchEncoding:
        """Prompt di chat tokenizzato per `stream`.

        Messaggio di sistema (`SYSTEM_PROMPT`) + messaggio utente con il
        contesto (vedi `_context`) e la domanda.
        `enable_thinking=False`: niente ragionamento, molto più veloce su CPU.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Context:\n" + "\n\n".join(context)
             + f"\n\nQuestion: {question}"},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        inputs: BatchEncoding = self.tokenizer(str(prompt),
                                               return_tensors="pt")
        return inputs

    def answer(self, question: str, sources: list[MinimalSource]) -> str:
        """Risposta intera, per i comandi `answer` e `answer_dataset`.

        Raccoglie i pezzi di `stream`. `do_sample=False`: stessa domanda,
        stessa risposta.
        """
        return "".join(self.stream(question, sources)).strip()

    def stream(self, question: str,
               sources: list[MinimalSource]) -> Iterator[str]:
        """Restituisce la risposta a pezzi. Usata dalla TUI e da `answer`.

        `generate` gira in un thread e scrive in un `TextIteratorStreamer`, da
        cui si leggono i pezzi. Un errore nel thread viene salvato, lo
        streamer chiuso (se no si aspetterebbe per sempre) e l'errore
        rilanciato alla fine.
        Senza contesto il modello non parte: risponderebbe a memoria
        (inventando), quindi si restituisce `NO_CONTEXT_ANSWER`.
        """
        context = self._context(sources)
        if not context:
            yield NO_CONTEXT_ANSWER
            return
        inputs = self._inputs(question, context)
        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        errors: list[Exception] = []

        def run() -> None:
            try:
                self.model.generate(  # type: ignore[misc]
                    **inputs, **GENERATE_KWARGS, streamer=streamer)
            except Exception as e:  # re-raised below, in the caller
                errors.append(e)
                # what streamer.end() does, minus its untyped signature
                streamer.text_queue.put(streamer.stop_signal)

        thread = Thread(target=run, daemon=True)
        thread.start()
        yield from streamer
        thread.join()
        if errors:
            raise errors[0]
