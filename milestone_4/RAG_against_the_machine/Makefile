.PHONY: install run tui debug clean lint lint-strict

# 42 home quota is ~5GB: keep uv cache and HF model weights in the project
# (clone it on sgoinfre)
export UV_CACHE_DIR := $(CURDIR)/.cache/uv
export HF_HOME := $(CURDIR)/.cache/huggingface

install:
	uv sync --extra dev

run:
	uv run python -m src $(CMD)

tui:
	uv run python -m src tui

debug:
	uv run python -m pdb -c continue -m src $(CMD)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict
