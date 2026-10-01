.PHONY: install lock lint format typecheck deadcode security audit comments test check

PYTHON ?= python

install:
	$(PYTHON) -m pip install --require-hashes -r requirements-dev.txt

lock:
	pip-compile --generate-hashes --strip-extras -o requirements.txt requirements.in
	pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements-dev.txt requirements-dev.in

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

typecheck:
	mypy .

deadcode:
	vulture

security:
	bandit -q -c pyproject.toml -r .

audit:
	pip-audit -r requirements.txt --no-deps --disable-pip

comments:
	$(PYTHON) scripts/check_comments.py

test:
	pytest --cov --cov-report=term-missing:skip-covered

# Run every gate that CI runs, locally
check: lint typecheck deadcode security comments test
