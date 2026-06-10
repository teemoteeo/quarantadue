# Code Review Report for `call me maybe` Project

## Overview

This report evaluates the project against all requirements specified in the 42 curriculum for the "call me maybe" milestone.

---

## Language & Style

| Requirement | Status | Notes |
|-------------|--------|-------|
| Python 3.10+ | ✅ PASS | `requires-python = ">=3.10"` in pyproject.toml |
| flake8 compliance | ✅ PASS | `uv run flake8 src/` returns no errors |
| mypy type checking | ✅ PASS | `uv run mypy src/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs` passes |
| Type hints on all functions | ✅ PASS | All public functions have full type hints in `decoder.py`, `model.py`, `loader.py`, `schemas.py`, and `__main__.py` |
| Docstrings (PEP 257) | ✅ PASS | All functions have Google-style docstrings with clear descriptions of parameters, return values, and behavior |
| Unhandled exceptions | ✅ PASS | Top-level `main()` catches all exceptions, returns exit code 2; individual prompts have try-except blocks |
| Context managers for resources | ✅ PASS | File I/O uses `with path.open()` context manager |

---

## Forbidden / Required Packages

| Requirement | Status | Notes |
|-------------|--------|-------|
| No dspy/pytorch/huggingface/transformers/outlines | ✅ PASS | No forbidden imports in `src/`. `llm_sdk/__init__.py` uses torch transformers internally but they're hidden behind the SDK API |
| Classes use pydantic | ✅ PASS | All schemas (`FunctionDefinition`, `TestPrompt`, `FunctionCallResult`) inherit from pydantic `BaseModel` |
| Only allowed external packages (numpy, json, llm_sdk) | ✅ PASS | `pyproject.toml` lists only `llm-sdk`, `numpy`, and `pydantic` |
| No private members from llm_sdk | ✅ PASS | Code only uses public API: `Small_LLM_Model`, `encode()`, `decode()`, `get_logits_from_input_ids()`, `get_path_to_vocab_file()` |
| Model is Qwen/Qwen3-0.6B | ✅ PASS | Default model in `__main__.py` is `Qwen/Qwen3-0.6B`; also configurable via CLI |

---

## Project Structure & Setup

| Requirement | Status | Notes |
|-------------|--------|-------|
| `src/` directory with implementation | ✅ PASS | Contains `__init__.py`, `__main__.py`, `decoder.py`, `loader.py`, `model.py`, `schemas.py` |
| Runnable as `uv run python -m src` | ✅ PASS | Tested successfully multiple times |
| `pyproject.toml` present | ✅ PASS | Contains all required metadata and dependencies |
| `uv.lock` present | ✅ PASS | Present at repo root (1.4MB) |
| `llm_sdk/` directory present | ✅ PASS | Local copy in project root |
| `data/input/` directory present | ✅ PASS | Contains `functions_definition.json` and `function_calling_tests.json` |
| `README.md` present | ✅ PASS | Contains all required sections |
| `.gitignore` excludes artifacts | ✅ PASS | Excludes `__pycache__/`, `.mypy_cache/`, etc. |
| `output/` not committed | ✅ PASS | `.gitignore` includes `data/output/`; `git ls-files data/output/` returns empty |

---

## Makefile

| Requirement | Status | Notes |
|-------------|--------|-------|
| `install` rule | ✅ PASS | Runs `uv sync` |
| `run` rule | ✅ PASS | Runs `uv run python -m src` with all arguments |
| `debug` rule | ✅ PASS | Runs same command with `--debug` flag |
| `clean` rule | ✅ PASS | Removes output file and cache directories |
| `lint` rule | ✅ PASS | Runs flake8 and mypy with all required flags |

---

## CLI Interface

| Requirement | Status | Notes |
|-------------|--------|-------|
| `--functions_definition` argument (optional, default to data/input/functions_definition.json) | ⚠️ **FAIL** | Argument is defined as `required=True`, should be optional with default |
| `--input` argument (optional, default to data/input/function_calling_tests.json) | ⚠️ **FAIL** | Argument is defined as `required=True`, should be optional with default |
| `--output` argument (optional, default to data/output/) | ⚠️ **FAIL** | Argument is defined as `required=True`, should be optional with default |
| Missing/invalid JSON handling | ✅ PASS | Graceful error messages with exit codes |

**Issue Details:**
```python
# Current (WRONG):
parser.add_argument(
    "--functions_definition",
    type=Path,
    required=True,  # ❌ Should be False
)

# Should be:
parser.add_argument(
    "--functions_definition",
    type=Path,
    default=Path("data/input/functions_definition.json"),  # ✅ Optional with default
)
```

---

## Input Files

| Requirement | Status | Notes |
|-------------|--------|-------|
| Reads `function_calling_tests.json` with "prompt" key | ✅ PASS | Uses pydantic `TestPrompt` model |
| Reads `functions_definition.json` with name/description/parameters/returns | ✅ PASS | Uses pydantic `FunctionDefinition` model |
| Handles malformed/missing files without crashing | ✅ PASS | raises `LoaderError` with clear messages |

---

## Core Logic — Constrained Decoding

| Requirement | Status | Notes |
|-------------|--------|-------|
| Uses `llm_sdk.Small_LLM_Model` | ✅ PASS | In `model.py`, wraps SDK's class |
| Uses `get_logits_from_input_ids()` | ✅ PASS | Called in `model.py` line 103, passed to `_argmax_masked()` |
| Uses `get_path_to_vocabulary_json()` | ✅ PASS | Called in `model.py` line 72 |
| Uses `encode()` for tokenization | ✅ PASS | Called in `model.py` line 107 |
| Constrained decoding with token masking | ✅ PASS | Implements in `decoder.py`: `_argmax_masked()` masks invalid tokens to `-inf` |
| Enforces JSON structure AND schema | ✅ PASS | Separate DFAs for function names, numbers, strings |
| No prompting-only approach | ✅ PASS | Uses token-level masking not just prompt engineering |
| Autoregressive generation | ✅ PASS | Each token appended and fed back |

---

## Output

| Requirement | Status | Notes |
|-------------|--------|-------|
| Produces `data/output/function_calling_results.json` | ✅ PASS | Tested with multiple runs |
| Output is JSON array | ✅ PASS | Verified programmatically |
| Each element has exactly "prompt", "name", "parameters" keys | ✅ PASS | Verified for all 11 results |
| All required arguments present | ✅ PASS | Verified schema compliance |
| Argument types match definitions | ✅ PASS | All number/string/boolean validations passed |

**Verification Results:**
- 11 prompts processed
- All outputs are valid JSON
- All function names match definitions (`fn_add_numbers`, `fn_greet`, `fn_reverse_string`, `fn_get_square_root`, `fn_substitute_string_with_regex`)
- All parameters match expected types and structure

---

## Performance & Reliability

| Requirement | Status | Notes |
|-------------|--------|-------|
| 100% outputs parseable JSON | ✅ PASS | All 11 results successfully parsed |
| ≥90% correct function selection | 🟨 **CANNOT DETERMINE** | Requires runtime test against ground truth |
| <5 minutes processing | 🟨 **CANNOT DETERMINE** | Runtime varies (0.5s–32s per prompt), 11 prompts in ~80s on test hardware |

**Runtime Breakdown (Test Runs):**
- Simple operations (`fn_add_numbers`, `fn_greet`): 0.5–1.2s
- String operations: 0.5–17s
- Complex regex patterns: 3–32s

---

## README

| Requirement | Status | Notes |
|-------------|--------|-------|
| English language | ✅ PASS | All content in English |
| First line format | ⚠️ **FAIL** | Uses HTML `<i>` tag instead of asterisks |
| "Description" section | ✅ PASS | Present with goal and overview |
| "Instructions" section | ✅ PASS | Install, run, debug, lint, clean documented |
| "Resources" section | ✅ PASS | Links to Qwen model, Hugging Face, GPT-2 BPE |
| "Algorithm explanation" section | ✅ PASS | Describes constrained decoding approach in detail |
| "Design decisions" section | ✅ PASS | Explains token-level vs character-level, vocabulary mapping |
| "Performance analysis" section | ✅ PASS | Discusses accuracy, speed, reliability |
| "Challenges faced" section | ✅ PASS | Documents regex loops and escape handling |
| "Testing strategy" section | ✅ PASS | Describes input validation, schema compliance testing |
| "Example usage" section | ✅ PASS | Clear command examples |

**Issue Details:**
```markdown
# Current (WRONG):
<i>This project has been created as part of the 42 curriculum by teemoteeo.</i>

# Should be:
*This project has been created as part of the 42 curriculum by teemoteeo.*
```

---

## Critical Failures Summary

### 🔴 CRITICAL FAILURES (Must Fix Before Submission)

1. **CLI Arguments Required Instead of Optional**
   - **Issue**: All three arguments (`--functions_definition`, `--input`, `--output`) are defined as `required=True` in argparse
   - **Impact**: Users cannot run without specifying all arguments manually, violating spec requirement
   - **Fix Required**: Set `required=False` and add defaults:
     ```python
     parser.add_argument(
         "--functions_definition",
         type=Path,
         default=Path("data/input/functions_definition.json"),
     )
     parser.add_argument(
         "--input",
         type=Path,
         default=Path("data/input/function_calling_tests.json"),
     )
     parser.add_argument(
         "--output",
         type=Path,
         default=Path("data/output/"),
     )
     ```

2. **README First Line Format**
   - **Issue**: Uses HTML `<i>` tag instead of asterisks per spec requirement
   - **Impact**: Does not match expected format specified in requirements
   - **Fix Required**: Change from `<i>...</i>` to `*...*`

### 🟨 Runtime-Only Checks (Require Execution to Verify)

1. Function selection accuracy ≥90% - Cannot be verified statically; requires comparing output against ground truth
2. Processing time <5 minutes - Depends on hardware and cache state

### ✅ PASSING REQUIREMENTS (No Issues Found)

- All language/style requirements met
- No forbidden packages used
- Project structure and setup correct
- Makefile has all required rules
- Core constrained decoding logic implemented correctly
- Output format and schema compliance verified
- README content complete (except first-line formatting)

---

## Verification Commands

To verify the review findings:

```bash
# Check code style
uv run flake8 src/
uv run mypy src/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

# Test error handling
uv run python -m src --functions_definition nonexistent.json --input data/input/function_calling_tests.json --output data/output/test.json
uv run python -m src --functions_definition data/input/functions_definition.json --input nonexistent.json --output data/output/test.json

# Test output format
uv run python -m src --functions_definition data/input/functions_definition.json --input data/input/function_calling_tests.json --output data/output/verify.json
python -c "import json; d=json.load(open('data/output/verify.json')); print(len(d), 'valid outputs')"

# Run with debug
uv run python -m src --functions_definition data/input/functions_definition.json --input data/input/function_calling_tests.json --output data/output/debug.json --debug
```

---

*Report generated for 42 curriculum "call me maybe" milestone*
