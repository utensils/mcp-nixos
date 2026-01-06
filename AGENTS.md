# Repository Guidelines

## Project Structure & Module Organization
- `mcp_nixos/` contains the MCP server implementation (main entry point: `mcp_nixos/server.py`).
- `tests/` holds pytest unit and integration tests; markers live in `pytest.ini` and `tests/conftest.py`.
- `website/` is the Next.js site; static assets live in `website/public/`.
- `flake.nix` defines the Nix dev shell; `pyproject.toml` defines Python packaging.
- `dist/`, `htmlcov/`, and `result/` are generated artifacts; do not edit by hand.

## Build, Test, and Development Commands
- Nix dev shell: `nix develop`, then `menu`, `run`, `run-tests`, `lint`, `format`, `typecheck`.
- Python-only dev: `uv pip install -e ".[dev]"`, then `uv run mcp-nixos` (or `python -m mcp_nixos.server`).
- Tests: `pytest tests/`, `pytest tests/ --unit`, `pytest tests/ --integration`.
- Lint/format/types: `ruff format mcp_nixos/ tests/`, `ruff check mcp_nixos/ tests/`, `mypy mcp_nixos/`.
- Website: `nix develop .#web` then `dev`/`build`, or `cd website && npm run dev`.

## Coding Style & Naming Conventions
- Python 3.11+; 4-space indentation; max line length 120 (ruff enforces).
- Use `snake_case` for functions/vars, `PascalCase` for classes; tests named `test_*.py`.
- Keep MCP responses plain text (no raw JSON) to match server behavior.

## Testing Guidelines
- Pytest with `pytest-asyncio` (auto mode); async tests are standard.
- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`; integration tests hit real APIs.
- Coverage is enabled by default (`--cov=mcp_nixos`).
- For flaky integration tests, use `@pytest.mark.flaky(reruns=3)`.

## Commit & Pull Request Guidelines
- Commit messages generally follow `type: summary` (e.g., `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Release merges include `release: vX.Y.Z` in the merge commit message (see `RELEASE_WORKFLOW.md`).
- PRs should include a clear summary and testing notes; link related issues when applicable.

## Configuration & Agent Notes
- `ELASTICSEARCH_URL` overrides the NixOS search backend for local testing.
- Automation details and deeper architectural notes live in `CLAUDE.md`; follow them when using coding agents.
