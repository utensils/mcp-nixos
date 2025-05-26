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

**IMPORTANT: Always run commands through `nix develop -c <command>` to ensure proper environment setup!**

- **Enter development shell**: `nix develop`
- **Run the server**: `nix develop -c run`
- **Test commands**:
  - All tests: `nix develop -c run-tests`
  - Unit tests only: `nix develop -c run-tests -- --unit`
  - Integration tests only: `nix develop -c run-tests -- --integration`
  - Single test: `nix develop -c run-tests -- tests/path/to/test_file.py::TestClass::test_function -v`
  - With coverage: `nix develop -c run-tests -- --cov=mcp_nixos`
- **Code quality**:
  - Format code: `nix develop -c format`
  - Lint code: `nix develop -c lint`
  - Type check: `nix develop -c typecheck`
  - Pylint check: `nix develop -c check-pylint`
- **Package management**:
  - Build: `nix develop -c build`
  - Publish to PyPI: `nix develop -c publish`

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
- **Smart change detection**: Skips tests for documentation-only changes
  - Uses `paths-filter` to categorize changes: code, docs, website
  - Documentation changes (*.md, LICENSE) skip the entire test suite
  - Website changes only trigger deployment, not tests
- **Smart triggering** to prevent redundant runs:
  - PRs: Run tests when opened, synchronized, or reopened
  - Main branch: Skip CI on merge commits (already tested in PR)
  - Tags: Run full CI + publish on version tags (v*)
  - Concurrency: Cancel in-progress PR runs when new commits are pushed
- **Release workflow**: Two options to avoid duplicate runs
  - Automatic: Include `release: v1.0.0` in merge commit message
  - Manual: Create tag after merge completes
- **Jobs**:
  - `changes`: Detects what changed to determine which jobs to run
  - `test`: Runs all tests, linting, type checking, and coverage (skipped for docs-only)
  - `analyze`: Code complexity analysis (PRs only, skipped for docs-only)
  - `deploy-website`: Deploys to S3/CloudFront when website files change
  - `create-release`: Auto-creates release when merge commit contains `release:`
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
- **Local Development**: `run-tests` always includes eval tests (all tests run)
- **CI/CD Behavior**:
  - **Repository members**: All tests run including eval tests
  - **External contributors**: Eval tests are skipped to prevent API credit abuse
  - Detection is automatic based on GitHub permissions
- **Run Manually**: `python run_evals.py` or `pytest tests/test_evals_anthropic.py -v`
- **Scenarios**: Package installation, service configuration, Home Manager integration
- **Pass Criteria**: 80% of expected behaviors must be observed
- **Security**: Never commit API keys; use environment variables in CI/CD

### Key Implementation Improvements
- **Dynamic Channel Resolution**: Automatically discovers available channels and determines current stable
  - Resolves `stable` to current release (25.05 as of Jan 2025, not deprecated 24.11)
  - Future-proof: adapts to new releases without code changes
  - Caches results for performance
- **Enhanced Error Messages**: Option info functions now suggest similar options when exact match fails
  - Shows up to 5 suggestions with helpful tips
  - Guides users to use prefix browsing functions
- **v1.0.0 Fixes**:
  - NixOS Option Info: Fixed `option_name.keyword` → `option_name` field
  - Elasticsearch Queries: Added `minimum_should_match: 1`
  - Option Search: Uses wildcard queries for hierarchical names
  - HTML Stripping: Removes `<rendered-html>` tags
  - Home Manager Parsing: Extracts from anchor IDs
  - List Limits: 4000 for Home Manager, 2000 for Darwin
  - Flake Search: Added `nixos_flakes_search` with deduplication
  - Home Manager Stats: Now returns actual statistics instead of redirect
  - Darwin Stats: Now returns actual statistics instead of redirect
  - Channel Discovery: Added `nixos_channels` tool

## API Reference (v1.0.0 - Tools Only)

### NixOS Tools (Elasticsearch API)
- `nixos_search(query, type, channel)` - Search packages/options/programs
  - Returns: Plain text list with bullet points
  - Type "flakes" redirects to nixos_flakes_search
- `nixos_flakes_search(query, limit)` - Search NixOS flakes
  - Returns: Deduplicated list of unique flakes with aggregated packages
  - **Important**: Uses `latest-43-group-manual` index (not `group-43-manual-*`)
  - Filters by `type: package` to match web UI (894 packages from ~6 unique repositories)
- `nixos_flakes_stats()` - Get flake statistics
  - Shows "Available flakes: 894" to match what users see on search.nixos.org
  - Also shows "Unique repositories: X" for actual repository count
  - **Note**: The 894 number represents packages from flakes, not unique flakes
- `nixos_info(name, type, channel)` - Get package or option details  
  - Returns: Key-value pairs (Package:, Version:, etc.)
- `nixos_stats(channel)` - Get statistics
  - Returns: Formatted statistics with bullet points
- `nixos_channels()` - List available channels with status
  - Returns: Channel list with availability indicators
- Channels: unstable (default), stable (dynamically resolved), beta (alias for stable), version numbers

### Home Manager Tools (HTML Parsing)
- `home_manager_search(query)` - Search configuration options
- `home_manager_info(name)` - Get specific option details (requires exact name, provides suggestions)
- `home_manager_stats()` - Get Home Manager statistics
  - Returns: Total options, categories, and top 5 categories with percentages
- `home_manager_list_options()` - List all option categories (131 categories, 2129+ options)
- `home_manager_options_by_prefix(prefix)` - Get options under a prefix (use to find exact names)

### nix-darwin Tools (HTML Parsing)
- `darwin_search(query)` - Search macOS configuration options
- `darwin_info(name)` - Get specific option details (requires exact name, provides suggestions)
- `darwin_stats()` - Get nix-darwin statistics
  - Returns: Total options, categories, and top 5 categories
- `darwin_list_options()` - List all option categories (21 categories)
- `darwin_options_by_prefix(prefix)` - Get options under a prefix (use to find exact names)

### NixHub Tools (REST API)
- `nixhub_package_versions(package_name, limit)` - Get package version history
  - Returns: Version list with dates, platforms, and nixpkgs commit hashes
  - Limit: 1-50 versions (default 10)
  - Shows attribute paths when different from package name
  - Use higher limits to find older versions (e.g., Ruby 2.6 requires limit > 15)
- `nixhub_find_version(package_name, version)` - Smart search for specific version
  - Automatically tries increasing limits (10, 25, 50) to find exact version
  - Returns: Found version details or helpful alternatives
  - Example: `nixhub_find_version("ruby", "2.6.7")` finds the exact commit

All tools return human-readable plain text, not XML or JSON.

## System Requirements

### APIs & External Dependencies
- **NixOS**: Elasticsearch API at https://search.nixos.org/backend
  - Authenticated with hardcoded credentials (public API)
  - **Flakes Index Discovery**:
    - Web UI uses `latest-43-group-manual` alias (contains ~1,781 docs)
    - This index has packages (894), options (852), and apps (35)
    - Must filter by `type: package` to get the 894 flakes shown on website
    - The broader `group-43-manual-*` pattern contains 452K+ docs (too many)
    - Elasticsearch field `flake_resolved.url` is not mapped as keyword, preventing aggregations
    - Manual counting reveals only ~6-8 unique flake repositories providing all 894 packages
- **Home Manager**: HTML docs at https://nix-community.github.io/home-manager/options.xhtml
- **nix-darwin**: HTML docs at https://nix-darwin.github.io/nix-darwin/manual/index.html
- **NixHub**: REST API at https://www.nixhub.io/packages/{package}
  - Provides package version history with nixpkgs commit hashes
  - Created by Jetify (makers of Devbox)
  - Returns 500 errors for non-existent packages (API quirk)

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
- `test_flake_search.py` - Flake search functionality tests (10 tests)
- `test_fixes_comprehensive.py` - Tests for flake deduplication and stats improvements (12 tests)
- `test_dynamic_channels.py` - Dynamic channel resolution tests (16 tests)
- `test_option_info_improvements.py` - Option info error message tests (9 tests)
- `test_mcp_behavior_comprehensive.py` - Real-world usage patterns (13 tests)
- `test_real_world_scenarios.py` - Complete user workflows (10 tests)
- `test_channel_handling.py` - Channel validation and suggestions
- `test_flake_evals.py` - Flake search evaluation tests
- `test_flake_evals_anthropic.py` - Flake search Anthropic API tests (requires API key)
- `test_evals_anthropic.py` - Anthropic API evaluation tests (requires API key)

**Running Tests**
```bash
# IMPORTANT: Always use 'nix develop -c' to ensure proper environment!

# All tests (includes Anthropic evals in local development)
nix develop -c run-tests

# Specific test file
nix develop -c run-tests -- tests/test_plain_text_output.py -v

# Integration tests only
nix develop -c run-tests -- --integration

# Include Anthropic evaluation tests explicitly (requires API key)
nix develop -c run-tests -- -m "anthropic"

# With coverage
nix develop -c run-tests -- --cov=mcp_nixos
```

**Test Best Practices**
- Mock API responses, not MCP protocol
- Test plain text output format consistency
- Verify error handling returns proper format
- No filesystem dependencies (stateless)


### Dependency Management (v1.0.0 - Lean & Mean)
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
  - Run server: `nix develop -c run`
  - Tests: `nix develop -c run-tests`, `nix develop -c run-tests -- --unit`, `nix develop -c run-tests -- --integration`
  - Evaluation tests: `nix develop -c run-tests -- -m "anthropic"` (requires `ANTHROPIC_API_KEY`)
  - Code quality: `nix develop -c lint`, `nix develop -c typecheck`, `nix develop -c format`, `nix develop -c check-pylint`
  - Stats: `nix develop -c loc`
  - Package: `nix develop -c build`, `nix develop -c publish`
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

- **Critical Guideline**: Never bump our version unless explicitly requested