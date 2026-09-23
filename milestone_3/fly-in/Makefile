.PHONY: install run tui debug clean lint lint-strict test

PY := uv run python
SRC := src
MAP ?= data/maps/hard/03_ultimate_challenge.txt
# Set VISUAL_FLAG= (empty) for plain, uncolored output.
VISUAL_FLAG ?= --visual

install:
	uv sync --frozen

run:
	$(PY) -m $(SRC) $(MAP) $(VISUAL_FLAG)

tui:
	$(PY) -m $(SRC) $(MAP) --tui

debug:
	$(PY) -m pdb -m $(SRC) $(MAP)

clean:
	rm -rf .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest tests/ -v
