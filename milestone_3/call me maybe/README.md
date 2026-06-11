<i>This project has been created as part of the 42 curriculum by tcostant.</i>

# Call Me Maybe

Hey, I just met you, and this is crazy, but here's my number, so...

A function-calling system using constrained decoding with Qwen3-0.6B, a small
0.6B-parameter language model. The system translates natural-language prompts
into structured, executable function calls with typed arguments.

## Description

Call Me Maybe implements a constrained-decoding pipeline that guarantees 100%
valid JSON output for function calling, even with small language models that
would otherwise fail well over half of the time. The project demonstrates how
structural guidance achieves near-perfect reliability from compact models.

### How It Works

1. **Function Catalog**: Available functions are defined with names, parameter
   types, and descriptions
2. **Context Building**: A prompt is built combining the function catalog with
   the user's request
3. **Constrained Decoding**: At every token-generation step, invalid tokens
   (those that would break the JSON structure or the schema) are masked to
   `-inf`
4. **Token Selection**: Only valid tokens are considered, so the output
   respects the expected schema by construction

### Key Features

- Constrained decoding via vocabulary-level token masking
- Support for JSON number, integer, string, and boolean types
- DFA-based grammar validation for JSON values
- Cached boolean masks over the vocabulary (per DFA state for numbers and
  strings, per accumulated prefix for names and literals): each decoding
  step is a mask lookup plus a vectorized argmax, never a vocabulary scan
- Forward passes only where the grammar leaves a real choice: once a
  partial name or literal is unambiguous the remainder is injected
  verbatim, and steps with a single legal token skip the model call
- Guaranteed termination: near the step budget, the string grammar only
  admits tokens that close the value (no recovery heuristics needed)
- Logit-arbitrated selection between catalog names that share a prefix
  (e.g. `fn_add` vs `fn_add_numbers`)
- Graceful degradation: a failed value decode falls back to a type-correct
  neutral value, so the output file is always schema-valid

## Instructions

### Installation

```bash
uv sync
```

### Usage

Run the function-calling pipeline (all arguments are optional and default to
the subject paths):

```bash
uv run python -m src
# equivalent to
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

### Debug Modes

Step through the program with Python's built-in debugger:

```bash
make debug        # runs under pdb
```

Print intermediate decoding decisions:

```bash
make debug-trace  # runs with --debug
```

### Linting

```bash
make lint         # flake8 + mypy with the subject's flags
make lint-strict  # flake8 + mypy --strict
```

### Cleaning

```bash
make clean
```

## Algorithm Explanation

### Constrained Decoding Approach

The decoder works at token level with a mask-based approach:

1. **Token-Level Masking**: For every generation step the model produces
   logits for all possible next tokens
2. **Grammar Validation**: Tokens are validated against a DFA representing
   the expected grammar; validity is precomputed into cached boolean masks
   over the vocabulary (one per DFA state or accumulated prefix)
3. **Invalid-Token Masking**: Tokens that would break the JSON structure or
   violate the schema are masked to `-inf`
4. **Greedy Selection**: The highest-scoring valid token is selected

### Grammar Modes

The decoder uses separate validation logic for:

- **Function-Name Selection**: Constrained to match one of the catalog
  names. When the accumulated text is both a complete name and a prefix of
  a longer one, the model's logits arbitrate between stopping (closing
  quote) and continuing.
- **JSON Number**: Validates signed integers and decimals. For parameters
  declared `integer`, the decimal point is excluded from the grammar, so
  fractional values can never be decoded and silently truncated.
- **JSON String**: Handles escape sequences and guarantees valid UTF-8
  after decoding. Within the last few steps of the generation budget only
  string-closing tokens remain legal, which forces termination by
  construction.
- **Boolean**: A constrained choice between the literals `true` and
  `false`.

### Token-to-Text Mapping

A crucial component is the `id_to_text` mapping that translates vocabulary
ids into their literal text representation. It is built by:

1. Loading the tokenizer's vocabulary JSON
2. Rebuilding the GPT-2 byte-to-unicode mapping locally
3. Translating every token string through the inverse mapping
4. Keeping only valid UTF-8 text representations

A pre-filtered `clean_vocab` list (text present, no control characters) is
computed once at load time; the decoder iterates it only to build the
boolean masks, so the per-step cost is a mask lookup plus a vectorized
argmax rather than a scan of the vocabulary.

## Design Decisions

### Why Constrained Decoding?

Prompt-only approaches with small LLMs reach roughly 30% reliability for
structured output. Constrained decoding guarantees validity by
construction, not by probability.

### Token Level vs. Character Level

Working at token level (instead of character level) provides:

- Faster generation (fewer iterations)
- Better coherence (subword units)
- Native integration with the model's vocabulary

### Forced Closure Instead of Recovery Heuristics

Earlier designs detected generation loops after the fact and recovered a
usable string with heuristics. The current design prevents the problem
instead: near the step budget the mask only admits tokens that complete
the value, so every decode either finishes or raises -- no post-hoc
guessing. If the output degenerates into a repeating cycle (e.g.
``cat.*cat.*cat.*``), the duplicate trailing segments are rolled back by
popping their tokens from the decoding context -- keeping exactly one
instance -- and the string is closed with the plain quote token from
there. Legitimate short runs such as ``"aaa"`` are preserved by requiring
more repetitions before short segments count as a loop.

### Vocabulary Mapping Strategy

The project reimplements the GPT-2 byte-level BPE mapping locally to avoid
importing third-party tokenizer libraries, keeping dependencies minimal.

### About the `torch` entry in pyproject.toml

`src/` never imports torch or transformers (both are forbidden by the
subject). Torch is required by the **provided** `llm_sdk` package; it is
declared in the project's dependencies only because `uv` applies
`[tool.uv.sources]` index pins (CPU wheels) to direct dependencies.

## Performance Analysis

### Accuracy

- Function selection: 100% on the provided test prompts
- Argument extraction: 90%+ (arguments match the expected types)

### Speed

The cost of a decode is dominated by the model forward passes (one full
recomputation of the context per generated token, as the SDK exposes no
incremental decoding), so runtime scales with the number of value tokens
the model actually has to choose:

- Simple prompts (numbers, short strings): about 3-7 s per prompt on CPU
- Long string arguments (e.g. regex patterns): about 15-40 s, bounded by
  the 64-token budget with forced closure
- Total time for the 11 provided test cases: about 2 minutes on CPU

### Reliability

- Valid JSON: 100% (every output parses)
- Schema compliance: 100% (a failed value decode degrades to a neutral
  typed value instead of producing invalid output)

## Challenges Faced

### Regex-Pattern Generation

Early versions stalled in loops when generating regex patterns with many
alternations (e.g. vowel patterns `a|e|i|o|u|...`). The first fix detected
loops and recovered heuristically; the final design replaces detection
with prevention: the string grammar is forced shut near the budget, which
removed about 100 lines of recovery code.

### Prefix-Overlapping Function Names

With catalogs containing names where one is a prefix of another, a naive
decoder always stops at the shorter name. The fix lets the model's logits
arbitrate between the closing-quote token and the best continuation token.

### String Escape Handling

JSON strings require correct escape handling (`\n`, `\t`, `\"`, `\uXXXX`).
The decoder validates escape sequences during generation and resolves them
afterwards.

## Testing Strategy

Manual validation, executed before every submission:

- **Input validation**: valid and invalid JSON files, missing files,
  verifying clear error messages and nonzero exit codes
- **Schema compliance**: all parameter types (number, integer, string,
  boolean), multi-parameter functions, edge cases (large numbers, special
  characters, empty strings)
- **CLI contract**: bare `uv run python -m src` must work using the
  default subject paths
- **Failure modes**: invalid model id must produce a clear error message,
  not a traceback
- **End-to-end**: full pipeline on the provided prompts, validating the
  output JSON structure, function names, and argument types

## Resources

- [Qwen3-0.6B model](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [GPT-2 Byte-Pair Encoding](https://huggingface.co/docs/transformers/tokenizer_summary)
- [Constrained Decoding for Structured Output](https://arxiv.org/abs/2109.04335)

## AI Usage

AI was used for:

- Understanding transformer architecture and tokenization
- Debugging constrained-decoding edge cases
- Reviewing code for PEP 8 / flake8 / mypy compliance
- Explaining JSON grammar validation techniques
- Auditing the project against the subject requirements
