# GitHub Copilot Instructions for MCP-NixOS

## Project Context

MCP-NixOS is a Model Context Protocol (MCP) server providing real-time information about NixOS packages, options, Home Manager, nix-darwin, and flakes. The server prevents AI hallucination by querying official APIs and documentation sources.

**Architecture:** Modular FastMCP 2.x async server exposing only 2 MCP tools (consolidated from 17 in v1.0 to reduce context window usage).

**Key Modules:**
- `mcp_nixos/server.py` - MCP tools, routing, and entry point
- `mcp_nixos/sources/` - Per-source modules (nixos, home_manager, darwin, flakehub, wiki, etc.)
- `mcp_nixos/config.py` - Configuration constants
- `mcp_nixos/caches.py` - Cache implementations
- `mcp_nixos/utils.py` - Shared utilities

## Core Development Workflows

### Build & Test Commands (Nix Flake Required)

```bash
nix develop              # Enter dev shell with Python venv
run                      # Start MCP server
run-tests               # Run all tests with coverage
lint                    # Check code with ruff
format                  # Format code with ruff
typecheck               # Run mypy type checker
build                   # Build package distributions
```

**Python-only alternative:** `uv pip install -e ".[dev]"` then `uv run mcp-nixos`

### Testing Strategy

- **Markers:** `@pytest.mark.unit` or `@pytest.mark.integration` (defined in [tests/conftest.py](../tests/conftest.py))
- **Integration tests hit real APIs** - no mocks, use `@pytest.mark.flaky(reruns=3)` for flaky network calls
- **Async everywhere:** pytest-asyncio auto mode enabled, function-scoped event loops
- **Coverage:** Always enabled (`--cov=mcp_nixos`)
- **Output validation:** All tests verify plain text output (no XML/JSON leakage)

Run specific tests: `pytest tests/test_server.py::test_nixos_search -v`

## Project-Specific Patterns

### 1. Plain Text Output Only

**Critical:** All MCP tool responses must return plain text formatted for LLM consumption. Never return raw JSON or XML to users.

```python
# ✅ Correct - Plain text formatting
return f"Package: {name}\nVersion: {version}\nDescription: {desc}"

# ❌ Wrong - Raw JSON
return json.dumps({"name": name, "version": version})
```

### 2. Channel Resolution System

Channels are dynamically discovered on startup by probing Elasticsearch generations (43-46) across versions (unstable, 25.05, 25.11, etc.). The `ChannelCache` class maintains this state.

- `"stable"` always maps to current stable release (e.g., "latest-44-nixos-25.11")
- `FALLBACK_CHANNELS` dict used when API discovery fails
- Override via `ELASTICSEARCH_URL` environment variable for local testing

### 3. Data Source Patterns

Each source has its own query implementation:

- **NixOS:** Elasticsearch API at search.nixos.org with HTTP basic auth
- **Home Manager/nix-darwin:** HTML parsing from official docs (BeautifulSoup)
- **FlakeHub:** REST API at api.flakehub.com with pagination
- **Nixvim:** Paginated JSON chunks from NuschtOS search (cached in `NixvimCache`)
- **Flake inputs:** Direct Nix store access via `nix flake archive --json` (requires local nix)

### 4. Error Handling Convention

Use the `error()` helper function for all tool errors:

```python
return error("Query required for search", "INVALID_INPUT")
```

Errors must be plain text, human-readable, and actionable.

### 5. Async Tool Implementation

All MCP tools use FastMCP 2.x async decorators:

```python
@mcp.tool()
async def nix(...) -> str:
    # For async HTTP calls, use async patterns
    result = await _search_nixhub(query, limit)
    return result
```

## Key Files

- [mcp_nixos/server.py](../mcp_nixos/server.py) - MCP tool definitions and routing
- [mcp_nixos/sources/](../mcp_nixos/sources/) - Data source implementations (one module per source)
- [mcp_nixos/config.py](../mcp_nixos/config.py) - API URLs, auth credentials, constants
- [mcp_nixos/caches.py](../mcp_nixos/caches.py) - Channel, Nixvim, Noogle, nix.dev caches
- [mcp_nixos/utils.py](../mcp_nixos/utils.py) - HTML parsing, formatting, file utilities
- [flake.nix](../flake.nix) - Nix dev shell and build configuration
- [pyproject.toml](../pyproject.toml) - Python packaging (Hatchling), dependencies, version source
- [tests/conftest.py](../tests/conftest.py) - Pytest configuration, markers, and test filtering

## CI/CD & Release Process

- **CI runs on all PRs:** flake check, Nix build, Python distribution build, package validation (twine), lint, typecheck, tests
- **Automated PyPI releases:** Version tags (v*) trigger publish workflow
- **Commit convention:** `type: summary` format (feat:, fix:, docs:, refactor:, test:, chore:)
- **Use `/release` skill:** Automates version bumps in pyproject.toml, changelog updates in RELEASE_NOTES.md, and Git tagging

## Common Pitfalls

1. **Don't add caching:** Version 1.0+ removed all caching for simplicity - always query live APIs
2. **Never batch unrelated tool calls in server.py:** Each MCP tool must be independent
3. **Flake inputs security:** Always validate paths stay within `/nix/store/` (see `_validate_nix_store_path()`)
4. **Line limits:** flake-inputs read allows 1-2000, all other actions limited to 1-100
5. **Generated artifacts:** Never manually edit `dist/`, `htmlcov/`, or `result/` directories
6. **Never bypass linting:** Do not use `# noqa`, `# type: ignore`, `# pylint: disable`, or similar comments to suppress warnings. Fix the underlying issue instead. If a rule is wrong for the project, update configuration in `pyproject.toml`.

## Documentation References

- **AGENTS.md:** Comprehensive guide for AI assistants (imported by Claude)
- **README.md:** User-facing quick start, tool usage examples, installation options
- **RELEASE_NOTES.md:** Changelog maintained for each version release
