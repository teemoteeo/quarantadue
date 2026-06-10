.PHONY: install run debug debug-trace clean lint lint-strict

export UV_CACHE_DIR ?= /sgoinfre/tcostant/uv-cache
export HF_HOME ?= /sgoinfre/tcostant/hf-cache

PY := uv run python
SRC := src
INPUT_FUNCTIONS := data/input/functions_definition.json
INPUT_TESTS := data/input/function_calling_tests.json
OUTPUT := data/output/function_calling_results.json

install:
	uv sync

run:
	$(PY) -m $(SRC) \
		--functions_definition $(INPUT_FUNCTIONS) \
		--input $(INPUT_TESTS) \
		--output $(OUTPUT)

debug:
	$(PY) -m pdb -m $(SRC) \
		--functions_definition $(INPUT_FUNCTIONS) \
		--input $(INPUT_TESTS) \
		--output $(OUTPUT)

debug-trace:
	$(PY) -m $(SRC) \
		--functions_definition $(INPUT_FUNCTIONS) \
		--input $(INPUT_TESTS) \
		--output $(OUTPUT) \
		--debug

clean:
	rm -rf $(OUTPUT)
	rm -rf $(SRC)/__pycache__
	rm -rf .mypy_cache
	find $(SRC) -type d -name __pycache__ -exec rm -rf {} +

lint:
	uv run flake8 $(SRC)
	uv run mypy $(SRC) \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 $(SRC)
	uv run mypy $(SRC) --strict