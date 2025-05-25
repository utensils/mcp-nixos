# MCP-NixOS Project Guidelines (v1.0.0)

## 🚀 Project Philosophy
This project underwent a massive refactoring in v1.0.0, reducing the codebase from 9,755 lines to ~500 lines (94.6% reduction) while maintaining 100% functionality. We proved that most "enterprise" code is just complexity for complexity's sake.

## 📝 Documentation Guidelines
- **NO ONE-OFF DOCUMENTATION FILES**: Do not create temporary or one-off documentation files (e.g., CHANGES.md, NOTES.md, etc.)
- All documentation belongs in:
  - `CLAUDE.md` - Primary source of truth for development guidelines
  - `README.md` - User-facing documentation
  - Code comments - Only when absolutely necessary
  - Commit messages - For change history
- If you need to document something, update the appropriate existing file

## 🛠️ Essential Development Commands (Quick Reference)

- **Develop environment**: `nix develop`
- **Run the server**: `run` (in nix shell)
- **Test commands**:
  - All tests: `run-tests`
  - Unit tests only: `run-tests -- --unit`
  - Integration tests only: `run-tests -- --integration`
  - Single test: `run-tests -- tests/path/to/test_file.py::TestClass::test_function -v`
  - With coverage: `run-tests -- --cov=mcp_nixos`
- **Code quality**:
  - Format code: `format`
  - Lint code: `lint`
  - Type check: `typecheck`
- **Package management**:
  - Build: `build`
  - Publish to PyPI: `publish`

## 🔧 MCP Development Setup

### Local Development with Claude Code
The project includes a `.mcp.json` file that configures Claude Code to use the local development version of the MCP server:

```json
{
  "mcpServers": {
    "nixos": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "-m", "mcp_nixos"],
      "env": {}
    }
  }
}
```

This configuration:
- **Automatically activates** when Claude Code is launched from the project directory
- **Uses uv** to run the local development code directly
- **Overrides** any global nixos MCP server configuration
- **Enables real-time testing** of code changes without reinstalling

### Testing MCP Tools in Claude Code
1. Make code changes to `server.py`
2. Restart Claude Code (changes require restart)
3. Test your changes using the MCP tools (they'll use your local code)
4. Example queries:
   - "Search for git packages in nixos"
   - "Get info about the neovim option in home manager"
   - "List darwin options"

### Switching Between Local and Production
- **Local dev**: Simply open Claude Code from the project directory
- **Production**: Open Claude Code from any other directory (uses global config)
- **Note**: The `.mcp.json` file is project-specific and only applies when Claude Code is launched from this directory

## ⚠️ CRITICAL: Testing and Implementation Changes ⚠️

**NEVER MODIFY IMPLEMENTATION CODE WITHOUT VALIDATING YOUR APPROACH**

- **TEST BEHAVIOR, NOT IMPLEMENTATION**: Ensure tests validate expected behaviors, not internal details
- **UNDERSTAND BEFORE CHANGING**: Thoroughly understand existing patterns and architecture before modifying
- **ROOT CAUSES, NOT SYMPTOMS**: Address fundamental issues instead of adding workarounds
- **VERIFY ALL CONTEXTS**: Test in all usage contexts (direct code, API calls, MCP interface, CLI)
- **IMPLEMENTATION CHANGES REQUIRE EVIDENCE**: Provide clear evidence that implementation changes are correct
- **CHANGES MUST BE REVERSIBLE**: Ensure you can roll back if a change causes regressions

Implementing quick fixes without understanding the architecture can completely break functionality, especially with context-sensitive code. Always validate your approach with robust tests that cover all usage scenarios.

## Source of Truth & Code Patterns

- CLAUDE.md is the primary source of truth for coding rules
- Always follow existing code patterns and module structure
- Maintain architectural boundaries and consistency

## Project Overview

MCP-NixOS provides MCP tools for searching and querying:
- **NixOS**: packages, options, and programs via Elasticsearch API
- **Home Manager**: configuration options via HTML documentation parsing  
- **nix-darwin**: macOS configuration options via HTML documentation parsing

All responses are formatted as human-readable plain text (no XML).

Official repository: [https://github.com/utensils/mcp-nixos](https://github.com/utensils/mcp-nixos)

## Branch Management

- Main branch is `main` (protected)
- Branch protection rules are enforced:
  - `main`: Requires PR review (1 approval), admin enforcement, no deletion, no force push
- PRs are created from feature branches to `main`
- Branch deletion on merge is disabled to preserve branch history

## CI/CD Configuration

- **Single workflow file**: `.github/workflows/ci.yml` handles all CI/CD operations
- **Testing**: Uses Nix flake environment on Linux only (no matrix tests)
- **Dependency Management**: Nix flake includes all dev and eval dependencies for isolated environment
- **Smart triggering** to prevent redundant runs:
  - PRs: Run tests when opened, synchronized, or reopened
  - Main branch: Skip CI on merge commits (already tested in PR)
  - Tags: Run full CI + publish on version tags (v*)
  - Concurrency: Cancel in-progress PR runs when new commits are pushed
- **Jobs**:
  - `test`: Runs all tests, linting, type checking, and coverage in one job
  - `analyze`: Code complexity analysis (PRs only)
  - `deploy-website`: Deploys to S3/CloudFront when website files change (main branch only)
  - `publish`: Publishes to PyPI on version tags
- **Test Exclusions**: Anthropic evaluation tests excluded via `-m "not anthropic"` marker
- **Codecov integration**: Uploads coverage and test results
- **No redundant runs**: Smart conditions prevent the PR→merge→tag triple-run issue

## Architecture

### Core Components (Just 2 Files!)
- **server.py**: All 13 MCP tools in ~500 lines of direct, functional code
- **__main__.py**: Simple entry point (28 lines)

### What We Removed (And Don't Miss)
- ❌ Cache layer - Stateless operation, no cache corruption
- ❌ Client abstractions - Direct API calls are clearer
- ❌ Context managers - No state to manage
- ❌ Resource definitions - Tools-only approach is simpler
- ❌ Utility modules - Inline what's needed
- ❌ 45+ files of complexity - Less is more

### Key Design Principles
- **Direct API Integration**: No abstraction layers between tools and APIs
- **Plain Text Output**: Human-readable responses, no XML parsing needed
- **Stateless Operation**: Each request is independent, no side effects
- **Minimal Dependencies**: Only 3 core dependencies (mcp, requests, beautifulsoup4)

### Implementation Guidelines (v1.0.0)

**Tools Only (No Resources)**
- Direct FastMCP tool decorators (`@mcp.tool()`)
- All tools return plain text strings (NOT XML)
- Consistent format with bullet points and clear hierarchy
- No dependency injection needed (stateless)

**Plain Text Output Format**
- Human-readable responses with consistent formatting
- Errors: `Error (CODE): Description`
- Search results: Bullet points (•) with indented details
- Info results: Key-value pairs with clear labels

**Direct API Integration**
- Elasticsearch for NixOS (with auth credentials)
  - Correct field names: `package_pname`, `option_name`, etc.
- HTML parsing for Home Manager and Darwin
  - Parse dt/dd elements for option documentation
- No abstraction layers or client classes
- Handle timeouts and errors gracefully

**Best Practices**
- Type annotations (Optional, Union, List, Dict)
- Strict null safety with defensive programming
- Detailed error logging and user-friendly messages
- Support wildcard searches and handle empty results
- Cross-platform compatibility:
  - Use pathlib.Path for platform-agnostic path handling
  - Check sys.platform before using platform-specific features
  - Handle file operations with appropriate platform-specific adjustments
  - Use os.path.join() instead of string concatenation for paths
  - For Windows compatibility:
    - Use os.path.normcase() for case-insensitive path comparisons
    - Never use os.path.samefile() in Windows tests (use normcase comparison instead)
    - Provide robust fallbacks for environment variables like LOCALAPPDATA
    - Properly clean up file handles with explicit close or context managers
  - Use platform-specific test markers (@pytest.mark.windows, @pytest.mark.skipwindows)
  - Ensure tests work consistently across Windows, macOS, and Linux

## Testing Guidelines

### Evaluation Testing with Anthropic API
- **Purpose**: Test MCP tools with real AI behavior to ensure practical usability
- **Setup**: Copy `.env.example` to `.env` and add your Anthropic API key
- **Run**: `python run_evals.py` or `pytest tests/test_evals_anthropic.py -v`
- **Scenarios**: Package installation, service configuration, Home Manager integration
- **Pass Criteria**: 80% of expected behaviors must be observed
- **Security**: Never commit API keys; use environment variables in CI/CD

### Key Implementation Fixes (v1.0.1)
- **NixOS Option Info**: Fixed `option_name.keyword` → `option_name` field for exact matches
- **Elasticsearch Queries**: Added `minimum_should_match: 1` to prevent unrelated results
- **Option Search**: Uses wildcard queries (`*{query}*`) for hierarchical option names
- **HTML Stripping**: Removes `<rendered-html>` tags and nested HTML from descriptions
- **Home Manager Parsing**: Extracts option names from anchor IDs (format: `opt-programs.git.enable`)
- **List Limits**: Increased to 4000 for Home Manager and 2000 for Darwin to see all categories

## API Reference (v1.0.0 - Tools Only)

### NixOS Tools (Elasticsearch API)
- `nixos_search(query, type, channel)` - Search packages/options/programs
  - Returns: Plain text list with bullet points
- `nixos_info(name, type, channel)` - Get package or option details  
  - Returns: Key-value pairs (Package:, Version:, etc.)
- `nixos_stats(channel)` - Get statistics
  - Returns: Formatted statistics with bullet points
- Channels: unstable (default), stable/24.11, beta/25.05

### Home Manager Tools (HTML Parsing)
- `home_manager_search(query)` - Search configuration options
- `home_manager_info(name)` - Get specific option details
- `home_manager_stats()` - Returns informational message
- `home_manager_list_options()` - List all option categories
- `home_manager_options_by_prefix(prefix)` - Get options under a prefix

### nix-darwin Tools (HTML Parsing)
- `darwin_search(query)` - Search macOS configuration options
- `darwin_info(name)` - Get specific option details  
- `darwin_stats()` - Returns informational message
- `darwin_list_options()` - List all option categories
- `darwin_options_by_prefix(prefix)` - Get options under a prefix

All tools return human-readable plain text, not XML or JSON.

## System Requirements

### APIs & External Dependencies
- **NixOS**: Elasticsearch API at https://search.nixos.org/backend
  - Authenticated with hardcoded credentials (public API)
- **Home Manager**: HTML docs at https://nix-community.github.io/home-manager/options.xhtml
- **nix-darwin**: HTML docs at https://nix-darwin.github.io/nix-darwin/manual/index.html

### Configuration (v1.0.0 - Minimal)
- `ELASTICSEARCH_URL` - Override default NixOS API URL (optional)
- That's it! No cache config, no log levels, no complex settings.

## Development


### C Extension Compilation Support
- Fully supports building C extensions via native libffi support
- Environment setup managed by flake.nix for build tools and headers

### Testing (v1.0.0 - Simplified)

**Test Organization**
- Unit tests validate individual functions with mocked APIs
- Integration tests verify real API responses
- Plain text output tests ensure no XML leakage

**Key Test Files**
- `test_plain_text_output.py` - Validates all outputs are plain text
- `test_real_integration.py` - Tests against real APIs
- `test_server_comprehensive.py` - Comprehensive unit tests
- `test_main.py` - Entry point tests
- `test_nixos_option_info.py` - NixOS option lookup tests
- `test_nixos_info_option_evals.py` - Option evaluation tests
- `test_evals_anthropic.py` - Anthropic API evaluation tests (requires API key)

**Running Tests**
```bash
# All tests (excludes Anthropic evals)
run-tests

# Specific test file
run-tests -- tests/test_plain_text_output.py -v

# Integration tests only
run-tests -- --integration

# Include Anthropic evaluation tests (requires API key)
run-tests -m "anthropic"

# With coverage
run-tests -- --cov=mcp_nixos
```

**Test Best Practices**
- Mock API responses, not MCP protocol
- Test plain text output format consistency
- Verify error handling returns proper format
- No filesystem dependencies (stateless)


### Dependency Management (v1.0.1 - Lean & Mean)
- Project uses `pyproject.toml` for dependency specification (PEP 621)
- Core dependencies (reduced from 5 to 3):
  - `mcp>=1.6.0`: Base MCP framework
  - `requests>=2.32.3`: HTTP client for API interactions
  - `beautifulsoup4>=4.13.3`: HTML parsing for documentation
- Optional dependencies defined in `[project.optional-dependencies]`:
  - `dev`: Development tools (pytest, black, flake8, etc.)
  - `evals`: Evaluation testing (anthropic, python-dotenv)
  - `win`: Windows-specific dependencies (pywin32)
- Nix flake installs both `dev` and `evals` dependencies for complete development environment

### Installation & Usage
- Install: `pip install mcp-nixos`, `uv pip install mcp-nixos`, `uvx mcp-nixos`
- Claude Code configuration: Add to `~/.config/claude/config.json`
- Docker deployment:
  - Standard use: `docker run --rm ghcr.io/utensils/mcp-nixos`
  - Build: `docker build -t mcp-nixos .`
  - Deployed on Smithery.ai as a hosted service
- Development:
  - Environment: `nix develop` (includes all dev and eval dependencies)
  - Run server: `run`
  - Tests: `run-tests`, `run-tests --unit`, `run-tests --integration`
  - Evaluation tests: `run-tests -m "anthropic"` (requires `ANTHROPIC_API_KEY`)
  - Code quality: `lint`, `typecheck`, `format`
  - Stats: `loc`
  - Package: `build`, `publish`
  - GitHub operations: Use `gh` tool for repository management and troubleshooting

### Code Style
- Python 3.11+ with strict type hints
- PEP 8 naming conventions:
  - Classes: `CamelCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private attributes/methods: `_leading_underscore`
  - Module-level names should be descriptive and avoid abbreviations
- Imports organization:
  - Standard library imports first
  - Third-party imports second
  - Local application imports third
  - Alphabetical order within each section
  - No star imports (`from module import *`)
- Google-style docstrings for all public functions and classes
- Black formatting, 120 char line limit (enforced by CI)
- Strict null safety practices (all `None` returns must be typed with `Optional`)
- Zero-tolerance for type errors
- Error handling using typed exceptions with descriptive messages
- Context managers for resource management

### Licensing and Attribution
- Project code is licensed under MIT License
- The NixOS snowflake logo is used with attribution to the NixOS project

## Quick Implementation Reference

**File Structure (v1.0.0)**
```
mcp_nixos/
├── server.py      # ~500 lines - All 13 MCP tools
└── __main__.py    # 28 lines - Entry point

tests/
├── test_plain_text_output.py     # Plain text validation
├── test_real_integration.py      # Real API tests
├── test_server_comprehensive.py  # Unit tests
├── test_nixos_option_info.py     # NixOS option lookup tests
└── test_nixos_info_option_evals.py  # Option eval tests
```

**Adding a New Tool**
1. Add function with `@mcp.tool()` decorator in server.py
2. Return plain text string (no XML!)
3. Use consistent formatting (bullets, key-value pairs)
4. Add tests for plain text output

**Key URLs**
- NixOS API: https://search.nixos.org/backend
- Home Manager: https://nix-community.github.io/home-manager/options.xhtml
- Darwin: https://nix-darwin.github.io/nix-darwin/manual/index.html

Remember: Less code = fewer bugs. Keep it simple!