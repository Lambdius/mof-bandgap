# mof-bandgap

----

<details>
<summary><strong>Project Commands</strong></summary>

| Command                                                                             | Makefile                       | Description                                         |
|-------------------------------------------------------------------------------------|--------------------------------|-----------------------------------------------------|
| **Infrastructure**                                                                  |                                |                                                     |
| `[ -f .env.example ] && cp -n .env.example .env \|\| echo '.env.example not found'` | `make env`                     | Generate `.env` from `.env.example` (if missing).   |
| `docker compose up -d`                                                              | `make up`                      | Start the app in detached mode.                     |
| `docker compose down`                                                               | `make down`                    | Stop and remove containers.                         |
| `docker compose build`                                                              | `make build`                   | Build the Docker image.                             |
| `docker compose logs -f`                                                            | `make logs`                    | Stream logs.                                        |
| `docker compose ps`                                                                 | `make ps`                      | Show container status.                              |
| **Development**                                                                     |                                |                                                     |
| `uv sync --all-extras --group dev`                                                  | `make sync`                    | Install all dependencies (incl. dev) via uv.        |
| `uv sync --extra scraper --group dev`                                               | `make sync-scraper`            | Install scraper and development dependencies.       |
| `uv sync --extra dataset --group dev`                                               | `make sync-dataset`            | Install dataset-build and development dependencies. |
| `uv sync --extra training --group dev`                                              | `make sync-training`           | Install training and development dependencies.      |
| `uv run ruff check .`                                                               | `make lint`                    | Run ruff checks.                                    |
| `uv run ruff check --fix . && uv run ruff format .`                                 | `make lint-fix`                | Auto-fix and format.                                |
| `uv run mypy src`                                                                   | `make typecheck`               | Run mypy --strict on src.                           |
| `uv run pytest`                                                                     | `make test`                    | Run pytest.                                         |
| `uv run alembic upgrade head`                                                       | `make migrate`                 | Apply all pending database migrations.              |
| `uv run alembic revision --autogenerate -m "..."`                                   | `make migration message="..."` | Generate a database migration.                      |
| `uv run alembic stamp 20260716_0001`                                                | `make migration-stamp`         | Mark a legacy `create_all` schema as migrated.      |
| `make sync && make lint && make typecheck && make test`                             | `make check`                   | Run the full verification chain.                    |

</details>

----
