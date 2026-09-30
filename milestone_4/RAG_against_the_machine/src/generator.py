"""Answer generation with Qwen3 over retrieved sources."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.models import MinimalSource

MODEL_NAME = "Qwen/Qwen3-0.6B"
# ponytail: a char budget, not a token one; 5 sources of 2000 chars is
# ~3-4k tokens, far under Qwen3's 32k window. Count tokens if k grows.
MAX_CONTEXT_CHARS = 12000
SYSTEM_PROMPT = (
    "You answer questions about the vLLM codebase using only the context "
    "snippets provided. Be concise and precise: name the exact functions, "
    "classes, flags or endpoints the context shows. If the context does "
    "not contain the answer, say you could not find it in the sources."
)


def read_source(source: MinimalSource) -> str:
    """Return the text a source points to.

    Args:
        source: File path and character span.

    Returns:
        file[first:last], read exactly as the indexer read it.
    """
    with open(source.file_path, encoding="utf-8", errors="replace",
              newline="") as f:
        return f.read()[source.first_character_index:
                        source.last_character_index]


class Generator:
    """A loaded model, reused across questions."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        """Load tokenizer and weights (downloaded on first use).

        Args:
            model_name: Hugging Face model id.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, dtype=torch.float32)  # bf16 is ~6x slower on CPU

    def answer(self, question: str, sources: list[MinimalSource]) -> str:
        """Answer question from the sources' text.

        Args:
            question: The user question.
            sources: Retrieved sources, best first.

        Returns:
            The model's answer.
        """
        context, used = [], 0
        for s in sources:
            text = f"--- {s.file_path}\n{read_source(s)}"
            if used + len(text) > MAX_CONTEXT_CHARS:
                break
            context.append(text)
            used += len(text)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Context:\n" + "\n\n".join(context)
             + f"\n\nQuestion: {question}"},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        inputs = self.tokenizer(str(prompt), return_tensors="pt")
        # transformers 5 types from_pretrained() as a class its own
        # generate() rejects as self; the runtime object is fine
        output = self.model.generate(  # type: ignore[misc]
            **inputs, max_new_tokens=256, do_sample=False,
            repetition_penalty=1.1)
        prompt_len = inputs["input_ids"].shape[1]
        return str(self.tokenizer.decode(
            output[0][prompt_len:], skip_special_tokens=True)).strip()
