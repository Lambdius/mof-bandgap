.PHONY: env sync lint typecheck test up down build logs ps check clean-db clean-minio clean build-dataset train dev-infra dev

# Infrastructure
env:
	[ -f .env.example ] && cp -n .env.example .env || echo '.env.example not found'
up:
	docker compose up -d
down:
	docker compose down
build:
	docker compose build
restart: down up
clean-db:
	docker compose exec postgres psql -U postgres -d mof_bandgap -c "TRUNCATE TABLE mof_structures"
clean-minio:
	docker compose exec minio sh -c 'mc alias set local http://localhost:9000 "$$MINIO_ROOT_USER" "$$MINIO_ROOT_PASSWORD" && mc rm --recursive --force local/mof-cif'
clean: clean-db clean-minio
dev-infra:
	docker compose up -d postgres minio
dev:
	DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mof_bandgap \
	MINIO_ENDPOINT=localhost:9000 \
	SCRAPER_HEADLESS=false \
	DEV_MODE=true \
	RUN_TRAINING=false \
	uv run mof-bandgap

# Development
sync:
	uv sync --all-extras --group dev
lint:
	uv run ruff check .
typecheck:
	uv run mypy src
test:
	uv run pytest
check: sync lint typecheck test
