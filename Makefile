.PHONY: install test lint typecheck security format check all clean run

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

security:
	uv run bandit -r src/ -c pyproject.toml
	uv run safety check

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

check: lint typecheck security test

all: install check

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

run:
	uv run uvicorn src.main:app --reload --port 8000
