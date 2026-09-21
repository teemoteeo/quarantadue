.PHONY: install run debug clean lint lint-strict

PY := uv run python
SRC := src
MAP ?= maps/easy/01_linear_path.txt
VISUAL ?= false

install:
	uv sync

run:
ifeq ($(VISUAL),true)
	$(PY) -m $(SRC) $(MAP) --visual
else
	$(PY) -m $(SRC) $(MAP)
endif

debug:
	$(PY) -m pdb -m $(SRC) $(MAP)

clean:
	rm -rf $(SRC)/__pycache__
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

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
