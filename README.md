# MCP-NixOS - Because Your AI Assistant Shouldn't Hallucinate About Packages

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![smithery badge](https://smithery.ai/badge/@utensils/mcp-nixos)](https://smithery.ai/server/@utensils/mcp-nixos)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/99cc55fb-a5c5-4473-b315-45a6961b2e8c)

> **🎉 REFACTORED**: Version 1.0.0 represents a complete rewrite that drastically simplified everything. We removed all the complex caching, abstractions, and "enterprise" patterns. Because sometimes less is more, and more is just showing off.

## Quick Start (Because You Want to Use It NOW)

**🚨 No Nix/NixOS Required!** This tool works on any system - Windows, macOS, Linux. You're just querying web APIs.

### Option 1: Using uvx (Recommended for most users)
```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"]
    }
  }
}
```

### Option 2: Using Nix (For Nix users)
```json
{
  "mcpServers": {
    "nixos": {
      "command": "nix",
      "args": ["run", "github:utensils/mcp-nixos", "--"]
    }
  }
}
```

That's it. Your AI assistant now has access to real NixOS data instead of making things up. You're welcome.

## What Is This Thing?

MCP-NixOS is a Model Context Protocol server that gives your AI assistant accurate, real-time information about:
- **NixOS packages** (130K+ packages that actually exist)
- **Configuration options** (22K+ ways to break your system)
- **Home Manager settings** (4K+ options for the power users)
- **nix-darwin configurations** (1K+ macOS settings Apple doesn't want you to touch)
- **Package version history** via [NixHub.io](https://www.nixhub.io) (Find that ancient Ruby 2.6 with commit hashes)

## The Tools You Actually Care About

### 🔍 NixOS Tools
- `nixos_search(query, type, channel)` - Search packages, options, or programs
- `nixos_info(name, type, channel)` - Get detailed info about packages/options
- `nixos_stats(channel)` - Package and option counts
- `nixos_channels()` - List all available channels
- `nixos_flakes_search(query)` - Search community flakes
- `nixos_flakes_stats()` - Flake ecosystem statistics

### 📦 Version History Tools (NEW!)
- `nixhub_package_versions(package, limit)` - Get version history with commit hashes
- `nixhub_find_version(package, version)` - Smart search for specific versions

### 🏠 Home Manager Tools
- `home_manager_search(query)` - Search user config options
- `home_manager_info(name)` - Get option details (with suggestions!)
- `home_manager_stats()` - See what's available
- `home_manager_list_options()` - Browse all 131 categories
- `home_manager_options_by_prefix(prefix)` - Explore options by prefix

### 🍎 Darwin Tools
- `darwin_search(query)` - Search macOS options
- `darwin_info(name)` - Get option details
- `darwin_stats()` - macOS configuration statistics
- `darwin_list_options()` - Browse all 21 categories
- `darwin_options_by_prefix(prefix)` - Explore macOS options

## Installation Options

**Remember: You DON'T need Nix/NixOS installed!** This tool runs anywhere Python runs.

### For Regular Humans (Windows/Mac/Linux)
```bash
# Run directly with uvx (no installation needed)
uvx mcp-nixos

# Or install globally
pip install mcp-nixos
uv pip install mcp-nixos
```

### For Nix Users (You Know Who You Are)
```bash
# Run without installing
nix run github:utensils/mcp-nixos

# Install to profile
nix profile install github:utensils/mcp-nixos
```

## Features Worth Mentioning

### 🚀 Version 1.0.0: The Great Simplification
- **Drastically less code** - Removed thousands of lines of complexity
- **100% functionality** - Everything still works
- **0% cache corruption** - Because we removed the cache entirely
- **Stateless operation** - No files to clean up
- **Direct API access** - No abstraction nonsense

### 📊 What You Get
- **Real-time data** - Always current, never stale
- **Plain text output** - Human and AI readable
- **Smart suggestions** - Helps when you typo option names
- **Cross-platform** - Works on Linux, macOS, and yes, even Windows
- **No configuration** - It just works™

### 🎯 Key Improvements
- **Dynamic channel resolution** - `stable` always points to current stable
- **Enhanced error messages** - Actually helpful when things go wrong
- **Deduped flake results** - No more duplicate spam
- **Version-aware searches** - Find that old Ruby version you need
- **Category browsing** - Explore options systematically

## For Developers (The Brave Ones)

### With Nix (The Blessed Path)
```bash
nix develop
menu  # Shows all available commands

# Common tasks
run        # Start the server
run-tests  # Run all tests
lint       # Format and check code
typecheck  # Check types
```

### Without Nix (The Path of Pain)
```bash
pip install -e ".[dev]"
pytest tests/
black mcp_nixos/
flake8 mcp_nixos/
```

### Testing Philosophy
- **367 tests** that actually test things
- **Real API calls** because mocks are for cowards
- **Plain text validation** ensuring no XML leaks through
- **Cross-platform tests** because Windows users deserve pain too

## Environment Variables

Just one. We're minimalists now:

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTICSEARCH_URL` | NixOS API endpoint | https://search.nixos.org/backend |


## Acknowledgments

This project queries data from several amazing services:
- **[NixHub.io](https://www.nixhub.io)** - Provides package version history and commit tracking
- **[search.nixos.org](https://search.nixos.org)** - Official NixOS package and option search
- **[Jetify](https://www.jetify.com)** - Creators of [Devbox](https://www.jetify.com/devbox) and NixHub

*Note: These services have not endorsed this tool. We're just grateful API consumers.*

## License

MIT - Because sharing is caring, even if the code hurts.

---

_Created by James Brink and maintained by masochists who enjoy Nix._

_Special thanks to the NixOS project for creating an OS that's simultaneously the best and worst thing ever._