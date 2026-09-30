.PHONY: install run debug clean lint lint-strict

install:
	uv sync --extra dev

run:
	uv run python -m src $(CMD)

debug:
	uv run python -m pdb -c continue -m src $(CMD)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .venv -prune -o -type f -name "*.pyc" -delete 2>/dev/null || true

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict
