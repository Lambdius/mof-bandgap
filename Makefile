.PHONY: env sync lint lint-fix typecheck test up down build logs ps check

# Infrastructure
env:
	[ -f .env.example ] && cp -n .env.example .env || echo '.env.example not found'
up:
	docker compose up -d
down:
	docker compose down
build:
	docker compose build
logs:
	docker compose logs -f
ps:
	docker compose ps

# Development
sync:
	uv sync --all-extras --group dev
lint:
	uv run ruff check .
lint-fix:
	uv run ruff check --fix . && uv run ruff format .
typecheck:
	uv run mypy src
test:
	uv run pytest
check: sync lint typecheck test
