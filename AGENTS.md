# Repository Guidelines

## Project Structure & Module Organization
FastAPI application code lives in `src/paternologia/` with modules for routers, models, and the YAML-backed `Storage`. Server-rendered pages pull from `templates/`, while CSS/JS assets sit in `static/`. Authoritative data is stored in `data/devices.yaml` plus `data/songs/*.yaml`; use `scripts/backup_all.sh` and `scripts/restore_device.sh` to move those snapshots off the repo. Tests mirror runtime modules under `tests/`, and ad-hoc experiments belong in `workspace/`.

## Build, Test, and Development Commands
Bootstrap dependencies with `uv sync` so the Python 3.12 environment matches `uv.lock`. Launch the app with `uv run uvicorn paternologia.main:app --reload`, which serves the templates and `/api` routes. Run the suite via `uv run pytest`, or target loops such as `uv run pytest tests/test_storage.py -k save_song` when iterating on persistence. Before risky YAML edits, run `uv run scripts/backup_all.sh <target-dir>` to preserve current presets.

## Coding Style & Naming Conventions
Stick to typed, 4-space-indented Python and mirror the Pydantic patterns already in `models.py`. Keep routers slim, delegate file I/O to `storage.py`, and share helpers through `dependencies.py`. Use snake_case identifiers, kebab-case template filenames, and hyphenated lowercase `SongMetadata.id` slugs. Templates follow Jinja defaults—keep blocks small and reference static resources through `/static/...`.

## Testing Guidelines
Pytest plus `pytest-asyncio` drive verification. Every feature needs a unit test (`tests/test_models.py`, `tests/test_storage.py`) and, when HTTP behavior changes, a companion assertion inside `tests/test_api.py` or `tests/test_e2e.py`. Reuse fixtures such as `test_storage` and `client` so suites stay hermetic—filesystem work should rely on temporary directories instead of the real `data/`. Name files `test_<area>.py` and document each scenario with a short docstring.

## Commit & Pull Request Guidelines
History favors short Conventional-Commit-style subjects (`feat: future backup/restore`, `doc: pacer editor`). Keep commits scoped to one concern and include Polish context when it clarifies the musical workflow. Pull requests must explain what changed, list verification commands and outcomes, mention modified SPEC files, and attach screenshots or GIFs whenever templates or static assets change. Request reviewers who own the affected stack slice (API, storage, or UI).

## Security & Configuration Tips
Treat YAML data as user-owned: never commit real device presets or secrets. Ensure song IDs remain filesystem-safe by reusing the `SongMetadata` validators and rejecting slashes or whitespace. Inspect archives before sharing so `workspace/` artifacts and rehearsal notes do not leak. Environment variables should hold any production credentials, and backups stored elsewhere should be rotated regularly.
