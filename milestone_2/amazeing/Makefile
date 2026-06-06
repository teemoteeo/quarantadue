.PHONY: install run debug clean lint test package

install:
	pip install -r requirements.txt

run:
	python3 a_maze_ing.py config.txt

debug:
	python3 -m pdb a_maze_ing.py config.txt

clean:
	rm -rf __pycache__ .mypy_cache *.pyc

lint:
	flake8 . && mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

test:
	python3 -m pytest tests/ -v

package:
	python3 -m build
	cp dist/mazegen-1.0.0-py3-none-any.whl .
	cp dist/mazegen-1.0.0.tar.gz .
