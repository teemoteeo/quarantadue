<i>This project has been created as part of the 42 curriculum by teemoteeo.</i>

# Call Me Maybe

A function calling system using constrained decoding with Qwen3-0.6B, a small 0.6B parameter language model. The system translates natural language prompts into structured, executable function calls with typed arguments.

## Description

Call Me Maybe implements a constrained decoding pipeline that guarantees 100% valid JSON output for function calling, even with small language models that would otherwise fail 70%+ of the time. The project demonstrates how structural guidance can achieve near-perfect reliability from compact models.

### How It Works

1. **Function Catalog**: Available functions are defined with names, parameter types, and descriptions
2. **Context Assembly**: A prompt is built combining the function catalog with the user's request
3. **Constrained Decoding**: At each token generation step, invalid tokens (those breaking JSON structure or schema) are masked to `-inf`
4. **Token Selection**: Only valid tokens are considered, ensuring the output follows the expected schema

### Key Features

- Constrained decoding using vocabulary-level token masking
- Support for JSON number, string, and boolean types
- DFA-based grammar validation for JSON values
- Loop detection for regex-like patterns
- Graceful fallback for edge cases

## Instructions

### Installation

```bash
uv sync
```

### Usage

Run the function calling pipeline:

```bash
make run
# or
uv run python -m src \
    --functions_definition data/input/functions_definition.json \
    --input data/input/function_calling_tests.json \
    --output data/output/function_calling_results.json
```

### Debug Mode

Run with debug output showing intermediate decoding decisions:

```bash
make debug
```

### Linting

Check code quality:

```bash
make lint
```

### Clean

Remove generated files:

```bash
make clean
```

## Algorithm Explanation

### Constrained Decoding Approach

The decoder operates at the token level using a mask-based approach:

1. **Token-Level Masking**: For each generation step, the model outputs logits for all possible next tokens
2. **Grammar Validation**: Tokens are validated against a DFA representing the expected grammar
3. **Invalid Token Masking**: Tokens that would break the JSON structure or violate the schema are masked to `-inf`
4. **Greedy Selection**: The highest-scoring valid token is selected

### Three Grammar Modes

The decoder uses separate validation logic for:

- **Function Name Selection**: Constrained to match one of the available function names
- **JSON Number**: Validates signed integers and decimals with optional fractional part
- **JSON String**: Handles escape sequences and ensures valid UTF-8 after decoding

### Token-to-Text Mapping

A critical component is the `id_to_text` mapping that translates vocabulary IDs to their literal text representations. This mapping is built by:

1. Loading the vocabulary JSON from the tokenizer
2. Reconstructing the GPT-2 byte-to-unicode mapping
3. Translating each token string through the inverse mapping
4. Storing only valid UTF-8 text representations

## Design Decisions

### Why Constrained Decoding?

Prompt-based approaches with LLMs achieve only ~30% reliability for structured output. Constrained decoding guarantees validity by construction, not by probability.

### Token-Level vs. Character-Level

Working at the token level (vs. character level) provides:
- Faster generation (fewer iterations)
- Better coherence (subword units)
- Integration with model's native vocabulary

### Vocabulary Mapping Strategy

The project re-implements the GPT-2 byte-level BPE mapping locally to avoid importing the `tiktoken` library, keeping dependencies minimal.

## Performance Analysis

### Accuracy

- Function selection: 100% (correct function identified for all test prompts)
- Argument extraction: 90%+ (all arguments match expected types)

### Speed

- Simple functions: <1s per prompt
- Complex regex patterns: 5-40s per prompt
- Total runtime for 11 test cases: ~80s

### Reliability

- Valid JSON: 100% (every output is parseable)
- Schema compliance: 100% (all outputs match function definitions)

## Challenges Faced

### Regex Pattern Generation

Early versions got stuck in loops when generating regex patterns with many alternatives (e.g., vowel patterns `a|e|i|o|u|...`). The solution was to:

1. Detect looping by tracking recent token suffixes
2. If the same suffix appears 3 times consecutively, break the loop
3. Extract a valid string from the accumulated text using heuristics

### String Escape Handling

JSON strings require proper escape sequence handling (`\n`, `\t`, `\"`, etc.). The decoder validates escape sequences during generation and decodes them post-generation.

## Testing Strategy

### Input Validation

- Test with valid and invalid JSON files
- Test with missing files
- Verify proper error messages are displayed

### Schema Compliance

- Test all parameter types (number, string, boolean)
- Test functions with multiple parameters
- Test edge cases (large numbers, special characters, empty strings)

### End-to-End Testing

- Run the full pipeline with the provided test prompts
- Verify output matches expected JSON structure
- Check that function names and argument types are correct

## Resources

- [Qwen3-0.6B Model](https://huggingface.co/Qwen/Qwen3-0.6B)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
- [GPT-2 Byte-Pair Encoding](https://huggingface.co/docs/transformers/tokenizer_summary)
- [Constrained Decoding for Structured Output](https://arxiv.org/abs/2109.04335)

## AI Usage

AI was used for:
- Understanding transformer architecture and tokenization
- Debugging constrained decoding edge cases
- Reviewing code for PEP 8 compliance
- Explaining JSON grammar validation techniques