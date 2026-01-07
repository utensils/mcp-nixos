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

## Development (Nix Flake)

This project uses Nix flakes exclusively for development and building.

```bash
# Enter development shell
nix develop

# Build the package
nix build

# Run the server directly
nix run

# Run tests
pytest tests/
pytest tests/ -m unit        # Unit tests only
pytest tests/ -m integration # Integration tests only

# Linting and formatting
ruff check mcp_nixos/ tests/
ruff format mcp_nixos/ tests/
mypy mcp_nixos/
```

### Running Specific Tests

```bash
# Run a single test file
pytest tests/test_server.py

# Run a single test function
pytest tests/test_server.py::test_nixos_search -v

# Run tests matching a pattern
pytest tests/ -k "nixos" -v
```

## Installation

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

## MCP Client Configuration

For use with Claude Desktop or other MCP clients:

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

Or if installed via Nix:

```json
{
  "mcpServers": {
    "nixos": {
      "type": "stdio",
      "command": "mcp-nixos"
    }
  }
}
```

## Testing Approach

- Async tests using pytest-asyncio (auto mode enabled, function-scoped event loops)
- Real API calls (no mocks) for integration tests
- Unit tests marked with `@pytest.mark.unit`
- Integration tests marked with `@pytest.mark.integration`
- Flaky integration tests use `@pytest.mark.flaky(reruns=3)` for retry handling
- Tests ensure plain text output (no XML/JSON leakage)

## Important Implementation Notes

1. **Channel Resolution**: The server dynamically discovers available NixOS channels on startup. "stable" always maps to the current stable release.

2. **Error Handling**: All tools return helpful plain text error messages. API failures gracefully degrade with user-friendly messages.

3. **No Caching**: Version 1.0+ removed all caching for simplicity. All queries hit live APIs.

4. **Async Everything**: Version 1.0.1 migrated to FastMCP 2.x. All tools are async functions.

5. **Plain Text Output**: All responses are formatted as human-readable plain text. Never return raw JSON or XML to users.

## CI/CD Workflows

- **CI**: Runs on all PRs - flake check, Nix build, Python distribution build, package validation (twine), linting, type checking, tests
- **Publish**: Automated PyPI releases on version tags (v*), multi-arch Docker images to GHCR and Docker Hub

## Environment Variables

- `ELASTICSEARCH_URL`: Override NixOS API endpoint (default: https://search.nixos.org/backend)

## Release Process

Use the `/release` skill to automate version releases. This handles:

- Version bump in `pyproject.toml`
- Changelog update in `RELEASE_NOTES.md`
- Git tag and GitHub release creation
- Triggers CI/CD for PyPI and Docker publishing
