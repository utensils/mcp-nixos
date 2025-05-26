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