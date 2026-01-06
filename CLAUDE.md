# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-NixOS is a Model Context Protocol (MCP) server that provides accurate, real-time information about NixOS packages, configuration options, Home Manager, nix-darwin, and flakes. It prevents AI assistants from hallucinating about NixOS package names and configurations by querying official APIs and documentation.

## Key Architecture

The project is a FastMCP 2.x server (async) with a single main module (Python 3.11+):

- `mcp_nixos/server.py` - Single file containing all MCP tools, API interactions, and helper functions (~970 lines)

Only **2 MCP tools** are exposed (consolidated from 17 in v1.0):

- `nix` - Unified query tool for search/info/stats/options/channels across all sources
- `nix_versions` - Package version history from NixHub.io

Data sources:

- NixOS packages/options: Elasticsearch API at search.nixos.org
- Home Manager options: HTML parsing from official docs
- nix-darwin options: HTML parsing from official docs
- Package versions: NixHub.io API (search.devbox.sh)
- Flakes: search.nixos.org flake index

All responses are formatted as plain text for optimal LLM consumption.

## Development Commands

### With Nix Development Shell (Recommended)

```bash
# Enter dev shell (auto-activates Python venv)
nix develop

# Show all available commands
menu

# Core commands:
run           # Start the MCP server
run-tests     # Run all tests (with coverage in CI)
run-tests --unit        # Unit tests only
run-tests --integration # Integration tests only
lint          # Check code with ruff
format        # Format code with ruff
typecheck     # Run mypy type checker
build         # Build package distributions
publish       # Upload to PyPI
setup         # Recreate .venv from scratch and reinstall dependencies

# Analysis commands:
loc                     # Count lines of code
complexity build        # Build wily cache for complexity analysis
complexity rank         # Rank files by complexity
complexity diff         # Compare complexity changes against previous commit

# Website development (separate Node.js shell):
web-dev       # Launch Node.js shell, then use: install, dev, build, lint
```

### Without Nix

```bash
# Install with development dependencies
uv pip install -e ".[dev]"  # or pip install -e ".[dev]"

# Run server
uv run mcp-nixos  # or python -m mcp_nixos.server

# Testing
pytest tests/
pytest tests/ --unit
pytest tests/ --integration

# Linting and formatting
ruff format mcp_nixos/ tests/
ruff check mcp_nixos/ tests/
mypy mcp_nixos/
```

## Testing Approach

- Async tests using pytest-asyncio (auto mode enabled, function-scoped event loops)
- Real API calls (no mocks) for integration tests
- Unit tests marked with `@pytest.mark.unit`
- Integration tests marked with `@pytest.mark.integration`
- Flaky integration tests use `@pytest.mark.flaky(reruns=3)` for retry handling
- Tests ensure plain text output (no XML/JSON leakage)
- Test markers defined in both `pytest.ini` and `tests/conftest.py`

### Running Specific Tests

```bash
# Run a single test file
pytest tests/test_server.py

# Run a single test function
pytest tests/test_server.py::test_nixos_search -v

# Run tests matching a pattern
pytest tests/ -k "nixos" -v
```

## Local Development with MCP Clients

Create `.mcp.json` in project root (already gitignored):

```json
{
  "mcpServers": {
    "nixos": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mcp-nixos",
        "mcp-nixos"
      ]
    }
  }
}
```

## Important Implementation Notes

1. **Channel Resolution**: The server dynamically discovers available NixOS channels on startup. "stable" always maps to the current stable release.

2. **Error Handling**: All tools return helpful plain text error messages. API failures gracefully degrade with user-friendly messages.

3. **No Caching**: Version 1.0+ removed all caching for simplicity. All queries hit live APIs.

4. **Async Everything**: Version 1.0.1 migrated to FastMCP 2.x. All tools are async functions.

5. **Plain Text Output**: All responses are formatted as human-readable plain text. Never return raw JSON or XML to users.

## CI/CD Workflows

- **CI**: Runs on all PRs - tests (unit + integration), linting, type checking
- **Publish**: Automated PyPI releases on version tags (v*)
- **Claude Code Review**: Reviews PRs using Claude
- **Claude PR Assistant**: Helps with PR creation

## Environment Variables

- `ELASTICSEARCH_URL`: Override NixOS API endpoint (default: https://search.nixos.org/backend)

## Release Process

Use the `/release` skill to automate version releases. This handles:

- Version bump in `pyproject.toml`
- Changelog update in `RELEASE_NOTES.md`
- Git tag and GitHub release creation
- Triggers CI/CD for PyPI and Docker publishing
