.PHONY: env sync lint lint-fix typecheck test up down build logs ps check clean-db clean-minio clean-data

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
clean-db:
	docker compose exec postgres psql -U postgres -d mof_bandgap -c "TRUNCATE TABLE mof_structures"
clean-minio:
	docker compose exec minio sh -c 'mc alias set local http://localhost:9000 "$$MINIO_ROOT_USER" "$$MINIO_ROOT_PASSWORD" && mc rm --recursive --force local/mof-cif'
clean: clean-db clean-minio

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
