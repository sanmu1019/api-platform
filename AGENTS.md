# Repository Guidelines

## Project Structure & Module Organization
This repository is a FastAPI-based API portal with a small static frontend.

- `main.py`: application entrypoint.
- `apis/`: built-in API modules grouped by feature (`demo/`, `tools/`, `word/`, `douyin/`, etc.).
- `admin/`: admin routes and management endpoints.
- `core/`: shared configuration, database access, middleware, auth dependencies, and exceptions.
- `frontend/`: static HTML pages and browser-side assets.
- `static/`: public static resources.
- `tests/`: pytest suite, currently centered in `tests/test_app.py`.
- `scripts/`: smoke tests and release helpers.
- `deploy/`: deployment examples such as service and nginx config.

## Build, Test, and Development Commands
- `python -m venv .venv` then `.venv\Scripts\activate`: create and activate a local virtual environment on Windows.
- `pip install -r requirements.txt`: install FastAPI, Uvicorn, pytest, and related dependencies.
- `copy config.json.example config.json`: bootstrap local configuration.
- `python main.py`: start the app locally, defaulting to `http://127.0.0.1:8000`.
- `python -m pytest -q`: run the automated test suite.
- `python scripts/smoke_test.py`: run basic endpoint smoke checks.
- `python scripts/smoke_spider_apis.py`: exercise spider-related APIs.
- `docker compose up -d --build`: build and run the stack in Docker.

## Coding Style & Naming Conventions
Use 4-space indentation in Python. Keep modules small and feature-oriented under `apis/`. Follow existing naming patterns: route handlers live in `route.py`, shared helpers belong in `core/`, and files/functions use `snake_case`. Prefer explicit, descriptive endpoint names such as `tool_hash` or `history_today`. Keep frontend assets in `frontend/assets/` and match names to page purpose (`app.js`, `doc.js`, `admin.js`).

## Testing Guidelines
Add or update pytest coverage for any backend behavior change. Place tests in `tests/` and name files `test_*.py`; name test functions `test_*`. For new endpoints, cover both success and failure paths, especially auth, rate-limit, and config-sensitive behavior. Run `python -m pytest -q` before submitting changes, then use the smoke scripts when API surface changes.

## Commit & Pull Request Guidelines
Git history is not available in this checkout, so use short, imperative commit messages such as `add admin login rate limit` or `fix tool hash response`. Keep each commit focused. Pull requests should include: a concise summary, affected routes/files, config changes, test results, and screenshots for frontend/admin page updates.

## Security & Configuration Tips
Do not commit secrets in `config.json`. Replace default admin and API keys outside local development. Review `ADMIN_PUBLIC_PATH`, self-registration, allowlists, and rate-limit settings before deployment.
