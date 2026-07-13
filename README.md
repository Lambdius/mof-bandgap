# mof-bandgap

----

<details>
<summary><strong>Project Commands</strong></summary>

| Command                                                                           | Makefile         | Description                                       |
|-----------------------------------------------------------------------------------|------------------|---------------------------------------------------|
| **Infrastructure**                                                                |                  |                                                   |
| `[ -f .env.example ] && cp -n .env.example .env || echo '.env.example not found'` | `make env`       | Generate `.env` from `.env.example` (if missing). |
| `docker compose up -d`                                                            | `make up`        | Start the app in detached mode.                   |
| `docker compose down`                                                             | `make down`      | Stop and remove containers.                       |
| `docker compose build`                                                            | `make build`     | Build the Docker image.                           |
| `docker compose logs -f`                                                          | `make logs`      | Stream logs.                                      |
| `docker compose ps`                                                               | `make ps`        | Show container status.                            |
| **Development**                                                                   |                  |                                                   |
| `uv sync --all-extras --group dev`                                                | `make sync`      | Install all dependencies (incl. dev) via uv.      |
| `uv run ruff check .`                                                             | `make lint`      | Run ruff checks.                                  |
| `uv run ruff check --fix . && uv run ruff format .`                               | `make lint-fix`  | Auto-fix and format.                              |
| `uv run mypy src`                                                                 | `make typecheck` | Run mypy --strict on src.                         |
| `uv run pytest`                                                                   | `make test`      | Run pytest.                                       |
| `make sync && make lint && make typecheck && make test`                           | `make check`     | Run the full verification chain.                  |

</details>

----
