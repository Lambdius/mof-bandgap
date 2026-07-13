# Contributing

----

<details>
<summary><strong>Environment Setup</strong></summary>

> The application requires `Python >=3.12` and `uv`; other versions are not
> guaranteed to work (see `.python-version`, `requires-python` in `pyproject.toml`).

[VSCode](https://code.visualstudio.com/) is the recommended editor for development.

#### VSCode Setup
Install the following extensions for proper [Ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy-lang.org/), and [EditorConfig](https://editorconfig.org/) integration:
1. `charliermarsh.ruff`
2. `ms-python.python`
3. `ms-python.mypy-type-checker`
4. `EditorConfig.EditorConfig`

</details>

----

<details>
<summary><strong>Git Hooks</strong></summary>

*Enable git hooks:*
```sh
chmod +x .githooks/*
git config core.hooksPath .githooks
```

`pre-commit` runs `mypy --strict` and `ruff check`.
`commit-msg` and `pre-push` enforce the naming rules below.

#### Allowed prefixes for commits and branches:
`feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

#### Commit message format:
```text
<type>(<scope>)?[!]: <subject>
```

*Where:*
 - `<type>`    — one of the allowed prefixes above.
 - `<scope>`   — optional scope in parentheses, alphanumeric/`-`.
 - `!`         — optional breaking change marker.
 - `: `        — colon + space are required.
 - `<subject>` — short description.
> Total commit message length is limited to 70 characters.

*Valid commit examples:*
 - `feat: add band gap parsing stage`
 - `fix(scraper): handle 429 responses`
 - `refactor(config)!: drop legacy env keys`
 - `docs: update commands table`
 - `chore(ci): tweak lint step`

#### Branch naming format:
```text
<type>/<slug>
<type>/<scope-or-id>/<slug>
```

*Where:*
 - `<type>`         — one of the prefixes listed above.
 - `/<scope-or-id>` — optional part, alphanumeric/`-`.
 - `/<slug>`        — short description, alphanumeric/`_`/`-`.

*Valid branch examples:*
 - `feat/add-scraper-cache`
 - `fix/parse-empty-bandgap`
 - `refactor/config-cleanup`

> Exceptions: `dev`, `main`, `master`.

</details>

----
