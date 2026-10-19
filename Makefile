.PHONY: check lint typecheck test firewall install

install:
	uv sync --all-extras

lint:
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts

typecheck:
	uv run mypy --strict src/exodus/common src/exodus/scoring

test:
	uv run pytest -q

firewall:
	uv run python scripts/verify_firewall.py

check: lint typecheck test firewall
	@echo "make check: OK"
