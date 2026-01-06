# MCP-NixOS: v1.0.3 Release Notes - Encoding Fix

## Overview

MCP-NixOS v1.0.3 fixes encoding errors when parsing Home Manager and nix-darwin documentation, ensuring robust operation with various HTML encodings from CDN edge servers.

## Changes in v1.0.3

### 🔧 Bug Fixes

- **HTML Encoding Support**: Fixed parsing errors with non-UTF-8 encodings (windows-1252, ISO-8859-1, UTF-8 with BOM) in documentation (#58)
- **CDN Resilience**: Enhanced robustness when fetching docs from different CDN edge nodes with varying configurations
- **Test Coverage**: Added comprehensive encoding tests for all HTML parsing functions

### 🛠️ Development Experience

- **Release Workflow**: Improved release command documentation with clearer formatting
- **Test Suite**: Updated 26 tests to properly handle byte content in mock responses

### 📦 Dependencies

- No changes from previous version
- Maintained compatibility with FastMCP 2.x

## Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.3

# Install with uv
uv pip install mcp-nixos==1.0.3

# Install with uvx
uvx mcp-nixos==1.0.3
```

## Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:1.0.3

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:1.0.3
```

## Migration Notes

This is a drop-in replacement for v1.0.2 with no user-facing changes. The fix resolves intermittent "unknown encoding: windows-1252" errors when fetching documentation.

## Contributors

- James Brink (@utensils) - Fixed encoding handling in HTML parser

---

# MCP-NixOS: v1.0.2 Release Notes - Infrastructure Improvements

## Overview

MCP-NixOS v1.0.2 is a maintenance release focused on CI/CD improvements, security fixes, and enhanced Docker support. This release adds manual workflow dispatch capabilities, GHCR package visibility automation, and improves the deployment pipeline.

## Changes in v1.0.2

### 🚀 CI/CD Enhancements

- **Manual Workflow Dispatch**: Added ability to manually trigger Docker builds for specific tags
- **GHCR Package Visibility**: Automated setting of GitHub Container Registry packages to public visibility
- **Continuous Docker Builds**: Docker images now build automatically on main branch pushes
- **FlakeHub Publishing**: Integrated automated FlakeHub deployment workflow
- **Workflow Separation**: Split website deployment into dedicated workflow for better CI/CD organization

### 🔧 Bug Fixes

- **Tag Validation**: Fixed regex character class in Docker tag validation
- **API Resilience**: Added fallback channels when NixOS API discovery fails (#52, #54)
- **Documentation Fixes**: Escaped quotes in usage page to fix ESLint errors
- **Security**: Patched PrismJS DOM Clobbering vulnerability

### 🛠️ Development Experience

- **Code Review Automation**: Enhanced Claude Code Review with sticky comments
- **Agent Support**: Added MCP and Python development subagents
- **CI Optimization**: Skip CI builds on documentation-only changes
- **Improved Docker Support**: Better multi-architecture builds (amd64, arm64)

### 📦 Dependencies

- All dependencies remain unchanged from v1.0.1
- Maintained compatibility with FastMCP 2.x

## Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.2

# Install with uv
uv pip install mcp-nixos==1.0.2

# Install with uvx
uvx mcp-nixos==1.0.2
```

## Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:1.0.2

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:1.0.2
```

## Migration Notes

This is a drop-in replacement for v1.0.1 with no user-facing changes. All improvements are infrastructure and workflow related.

## Contributors

- James Brink (@utensils) - Chief Infrastructure Engineer

---

# MCP-NixOS: v1.0.1 Release Notes - FastMCP 2.x Migration

## Overview

MCP-NixOS v1.0.1 completes the migration to FastMCP 2.x, bringing modern async/await patterns and improved MCP protocol compliance. This release maintains all existing functionality while modernizing the codebase for better performance and maintainability.

## Changes in v1.0.1

### 🚀 Major Updates

- **FastMCP 2.x Migration**: Migrated from MCP SDK to FastMCP 2.x for better async support
- **Async/Await Patterns**: All tools now use proper async/await patterns throughout
- **Improved Type Safety**: Enhanced type annotations with FastMCP's built-in types
- **Test Suite Overhaul**: Fixed all 334 tests to work with new async architecture
- **CI/CD Modernization**: Updated to use ruff for linting/formatting (replacing black/flake8/isort)

### 🔧 Technical Improvements

- **Tool Definitions**: Migrated from `@server.call_tool()` to `@mcp.tool()` decorators
- **Function Extraction**: Added `get_tool_function` helper for test compatibility
- **Mock Improvements**: Enhanced mock setup for async function testing
- **Channel Resolution**: Fixed channel cache mock configurations in tests
- **Error Messages**: Removed "await" from user-facing error messages for clarity

### 🧪 Testing Enhancements

- **Test File Consolidation**: Removed duplicate test classes from merged files
- **Async Test Support**: All tests now properly handle async/await patterns
- **Mock JSON Responses**: Fixed mock setup to return proper dictionaries instead of Mock objects
- **API Compatibility**: Updated test expectations to match current NixHub API data
- **Coverage Maintained**: All 334 tests passing with comprehensive coverage

### 🛠️ Development Experience

- **Ruff Integration**: Consolidated linting and formatting with ruff
- **Simplified Toolchain**: Removed black, flake8, and isort in favor of ruff
- **Faster CI/CD**: Improved CI pipeline efficiency with better caching
- **Type Checking**: Enhanced mypy configuration for FastMCP compatibility

### 📦 Dependencies

- **FastMCP**: Now using `fastmcp>=2.11.0` for modern MCP support
- **Other Dependencies**: Maintained compatibility with all existing dependencies
- **Development Tools**: Streamlined dev dependencies with ruff

## Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.1

# Install with uv
uv pip install mcp-nixos==1.0.1

# Install with uvx
uvx mcp-nixos==1.0.1
```

## Migration Notes

This is a drop-in replacement for v1.0.1 with no user-facing changes. The migration to FastMCP 2.x is entirely internal and maintains full backward compatibility.

## Technical Details

The migration involved:

1. **Async Architecture**: Converted all tool functions to async with proper await usage
2. **Import Updates**: Changed from `mcp.server.Server` to `fastmcp.FastMCP`
3. **Decorator Migration**: Updated all tool decorators to FastMCP's `@mcp.tool()` pattern
4. **Test Compatibility**: Added function extraction helpers for test suite compatibility
5. **Mock Enhancements**: Improved mock setup for async testing patterns

## Contributors

- James Brink (@utensils) - Chief Modernizer

---

# MCP-NixOS: v1.0.0 Release Notes - The Great Simplification

## Overview

MCP-NixOS v1.0.0 is a complete rewrite that proves less is more. We've drastically simplified the codebase while maintaining 100% functionality and adding new features. This isn't just a refactor—it's a masterclass in minimalism.

## Changes in v1.0.0

### 🎯 The Nuclear Option

- **Complete Rewrite**: Drastically simplified the entire codebase
- **Stateless Operation**: No more cache directories filling up your disk
- **Direct API Calls**: Removed all abstraction layers—now it's just functions doing their job
- **Simplified Dependencies**: Reduced from 5 to 3 core dependencies (40% reduction)
- **Two-File Implementation**: Everything you need in just `server.py` and `__main__.py`
- **Resolves #22**: Completely eliminated pickle usage and the entire cache layer

### 🚀 Major Improvements

- **Plain Text Output**: All responses now return human-readable plain text (no XML!)
- **NixHub Integration**: Added package version history tools
  - `nixhub_package_versions`: Get version history with nixpkgs commits
  - `nixhub_find_version`: Smart search for specific versions
- **Dynamic Channel Resolution**: Auto-discovers current stable channel
- **Enhanced Error Messages**: Suggestions when exact matches fail
- **Flake Search**: Added deduplicated flake package search
- **Better Stats**: Accurate statistics for all tools
- **Zero Configuration**: Removed all the config options you weren't using anyway
- **Faster Startup**: No cache initialization, no state management, just pure functionality
- **100% Test Coverage**: Comprehensive test suite ensures everything works as advertised

### 💥 Breaking Changes

- **No More Caching**: All operations are now stateless (your internet better be working)
- **Environment Variables Removed**: Only `ELASTICSEARCH_URL` remains
- **No Pre-Cache Option**: The `--pre-cache` flag is gone (along with the cache itself)
- **No Interactive Shell**: The deprecated CLI has been completely removed

### 🧹 What We Removed

- `cache/` directory - Complex caching that nobody understood
- `clients/` directory - Abstract interfaces that abstracted nothing
- `contexts/` directory - Context managers for contexts that didn't exist
- `resources/` directory - MCP resource definitions (now inline)
- `tools/` directory - Tool implementations (now in server.py)
- `utils/` directory - "Utility" functions that weren't
- 45 files of over-engineered complexity

### 📊 The Numbers

- **Before**: Many files with layers of abstraction
- **After**: Just 2 core files that matter
- **Result**: Dramatically less code, zero reduction in functionality, more features added

## Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.0

# Install with uv
uv pip install mcp-nixos==1.0.0

# Install with uvx
uvx mcp-nixos==1.0.0
```

## Migration Guide

If you're upgrading from v0.x:

1. **Remove cache-related environment variables** - They don't do anything anymore
2. **Remove `--pre-cache` from any scripts** - It's gone
3. **That's it** - Everything else just works

## Why This Matters

This release demonstrates that most "enterprise" code is just complexity for complexity's sake. By removing abstractions, caching layers, and "design patterns," we've created something that:

- Is easier to understand
- Has fewer bugs (less code = less bugs)
- Starts faster
- Uses less memory
- Is more reliable

Sometimes the best code is the code you delete.

## Contributors

- James Brink (@utensils) - Chief Code Deleter

---

# MCP-NixOS: v0.5.1 Release Notes

## Overview

MCP-NixOS v0.5.1 is a minor release that updates the Elasticsearch index references to ensure compatibility with the latest NixOS search API. This release updates the index references from `latest-42-` to `latest-43-` to maintain functionality with the NixOS search service.

## Changes in v0.5.1

### 🔧 Fixes & Improvements

- **Updated Elasticsearch Index References**: Fixed the Elasticsearch index references to ensure proper connectivity with the NixOS search API
- **Version Bump**: Bumped version from 0.5.0 to 0.5.1

## Installation

```bash
# Install with pip
pip install mcp-nixos==0.5.1

# Install with uv
uv pip install mcp-nixos==0.5.1

# Install with uvx
uvx mcp-nixos==0.5.1
```

## Configuration

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

## Contributors

- James Brink (@utensils)

# MCP-NixOS: v0.5.0 Release Notes

## Overview

MCP-NixOS v0.5.0 introduces support for the NixOS 25.05 Beta channel, enhancing the flexibility and forward compatibility of the tool. This release adds the ability to search and query packages and options from the upcoming NixOS 25.05 release while maintaining backward compatibility with existing channels.

## Changes in v0.5.0

### 🚀 Major Enhancements

- **NixOS 25.05 Beta Channel Support**: Added support for the upcoming NixOS 25.05 release
- **New "beta" Alias**: Added a "beta" alias that maps to the current beta channel (currently 25.05)
- **Comprehensive Channel Documentation**: Updated all docstrings to include information about the new beta channel
- **Enhanced Testing**: Added extensive tests to ensure proper channel functionality

### 🛠️ Implementation Details

- **Channel Validation**: Extended channel validation to include the new 25.05 Beta channel
- **Cache Management**: Ensured cache clearing behavior works correctly with the new channel
- **Alias Handling**: Implemented proper handling of the "beta" alias similar to the "stable" alias
- **Testing**: Comprehensive test suite to verify all aspects of channel switching and alias resolution

## Technical Details

The release implements the following key improvements:

1. **25.05 Beta Channel**: Added the Elasticsearch index mapping for the upcoming NixOS 25.05 release using the index name pattern `latest-43-nixos-25.05`

2. **Beta Alias**: Implemented a "beta" alias that will always point to the current beta channel, similar to how the "stable" alias points to the current stable release

3. **Extended Documentation**: Updated all function and parameter docstrings to include the new channel options, ensuring users know about the full range of available channels

4. **Future-Proofing**: Designed the implementation to make it easy to add new channels in the future when new NixOS releases are in development

## Installation

```bash
# Install with pip
pip install mcp-nixos==0.5.0

# Install with uv
uv pip install mcp-nixos==0.5.0

# Install with uvx
uvx mcp-nixos==0.5.0
```

## Usage

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

### Available Channels

The following channels are now available for all NixOS tools:

- `unstable` - The NixOS unstable development branch
- `25.05` - The NixOS 25.05 Beta release (upcoming)
- `beta` - Alias for the current beta channel (currently 25.05)
- `24.11` - The current stable NixOS release
- `stable` - Alias for the current stable release (currently 24.11)

Example usage:

```python
# Search packages in the beta channel
nixos_search(query="nginx", channel="beta")

# Get information about a package in the 25.05 channel
nixos_info(name="python3", type="package", channel="25.05")
```

## Contributors

- James Brink (@utensils)
- Sean Callan (Moral Support)
