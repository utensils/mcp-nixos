# AGENTS.md (Guidance for AI Assistants)

This file provides guidance to Claude Code (claude.ai/code) and other AI agents when working with code in this repository. It combines general repository guidelines with specific implementation details for the MCP server.

## Project Overview

MCP-NixOS is a Model Context Protocol (MCP) server that provides accurate, real-time information about NixOS packages, configuration options, Home Manager, nix-darwin, and flakes. It prevents AI assistants from hallucinating about NixOS package names and configurations by querying official APIs and documentation.

## Project Structure & Module Organization

- `mcp_nixos/` - Contains the MCP server implementation.
  - `mcp_nixos/server.py` - Single file containing all MCP tools, API interactions, and helper functions (~970 lines).
- `tests/` - Holds pytest unit and integration tests; markers live in `pytest.ini` and `tests/conftest.py`.
- `website/` - The Next.js site; static assets live in `website/public/`.
- `flake.nix` - Defines the Nix dev shell and build instructions.
- `pyproject.toml` - Defines Python packaging and dependencies.
- `dist/`, `htmlcov/`, and `result/` are generated artifacts; do not edit by hand.

## Key Architecture

The project is a FastMCP 2.x server (async) with a single main module (Python 3.11+).

Only **2 MCP tools** are exposed (consolidated from 17 in v1.0):
- `nix` - Unified query tool for search/info/stats/options/channels across all sources.
- `nix_versions` - Package version history from NixHub.io.

### Data Sources
- NixOS packages/options: Elasticsearch API at search.nixos.org
- Home Manager options: HTML parsing from official docs
- nix-darwin options: HTML parsing from official docs
- Package versions: NixHub.io API (search.devbox.sh)
- Flakes: search.nixos.org flake index

All responses are formatted as plain text for optimal LLM consumption.

## Build, Test, and Development Commands

This project uses Nix flakes exclusively for development and building.

### With Nix Development Shell (Recommended)

```bash
# Enter dev shell (auto-activates Python venv)
nix develop

# Core commands (available via menu):
run           # Start the MCP server
run-tests     # Run all tests (with coverage in CI)
lint          # Check code with ruff
format        # Format code with ruff  
typecheck     # Run mypy type checker
build         # Build the package/distributions
```

### Python-only Development

```bash
# Install with development dependencies
uv pip install -e ".[dev]"  # or pip install -e ".[dev]"

# Run server
uv run mcp-nixos  # or python -m mcp_nixos.server
```

## Testing Guidelines

- Pytest with `pytest-asyncio` (auto mode enabled, function-scoped event loops); async tests are standard.
- Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`.
- Integration tests hit real APIs (no mocks).
- Coverage is enabled by default (`--cov=mcp_nixos`).
- For flaky integration tests, use `@pytest.mark.flaky(reruns=3)`.
- Tests ensure plain text output (no XML/JSON leakage).

### Running Specific Tests

```bash
# Run a single test file
pytest tests/test_server.py

# Run a single test function
pytest tests/test_server.py::test_nixos_search -v

# Run tests matching a pattern
pytest tests/ -k "nixos" -v
```

## Coding Style & Naming Conventions

- Python 3.11+; 4-space indentation; max line length 120 (ruff enforces).
- Use `snake_case` for functions/vars, `PascalCase` for classes; tests named `test_*.py`.
- Keep MCP responses plain text (no raw JSON) to match server behavior.

## Installation & Configuration

### As a Nix Package

```nix
# In your flake.nix
{
  inputs.mcp-nixos.url = "github:utensils/mcp-nixos";

  outputs = { nixpkgs, mcp-nixos, ... }: {
    # Use the overlay to add pkgs.mcp-nixos
    nixpkgs.overlays = [ mcp-nixos.overlays.default ];

    # Then use in your config:
    # environment.systemPackages = [ pkgs.mcp-nixos ];  # NixOS
    # home.packages = [ pkgs.mcp-nixos ];               # Home Manager
  };
}
```

### MCP Client Configuration (Claude Desktop, etc.)

```json
{
  "mcpServers": {
    "nixos": {
      "type": "stdio",
      "command": "nix",
      "args": ["run", "github:utensils/mcp-nixos"]
    }
  }
}
```

## Important Implementation Notes

1. **Channel Resolution**: The server dynamically discovers available NixOS channels on startup. "stable" always maps to the current stable release.
2. **Error Handling**: All tools return helpful plain text error messages. API failures gracefully degrade.
3. **No Caching**: Version 1.0+ removed all caching for simplicity. All queries hit live APIs.
4. **Async Everything**: Version 1.0.1 migrated to FastMCP 2.x. All tools are async functions.
5. **Plain Text Output**: All responses are formatted as human-readable plain text. Never return raw JSON or XML to users.
6. **Environment Variables**: `ELASTICSEARCH_URL` overrides the NixOS search backend for local testing.

## Commit, PR, & Release Guidelines

- Commit messages follow `type: summary` (e.g., `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- **CI**: Runs on all PRs - flake check, Nix build, Python distribution build, package validation (twine), linting, type checking, tests.
- **Publish**: Automated PyPI releases on version tags (v*), multi-arch Docker images to GHCR and Docker Hub.
- **Release Process**: Use the `/release` skill to automate version releases. This handles version bumps in `pyproject.toml`, changelog updates in `RELEASE_NOTES.md`, and Git tagging.
- Release merges include `release: vX.Y.Z` in the merge commit message.