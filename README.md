# MCP-NixOS - Because Your AI Assistant Shouldn't Hallucinate About Packages

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/99cc55fb-a5c5-4473-b315-45a6961b2e8c)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/utensils/mcp-nixos?utm_source=oss&utm_medium=github&utm_campaign=utensils%2Fmcp-nixos&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude-D97757?logo=claude&logoColor=white)](https://claude.ai)

## Quick Start (Because You Want to Use It NOW)

**🚨 No Nix/NixOS Required!** This tool works on any system - Windows, macOS, Linux. You're just querying web APIs.

### Option 1: Using uvx (Recommended for most users)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=nixos&config=eyJjb21tYW5kIjoidXZ4IG1jcC1uaXhvcyJ9)

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

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=nixos&config=eyJjb21tYW5kIjoibml4IHJ1biBnaXRodWI6dXRlbnNpbHMvbWNwLW5peG9zIC0tIn0%3D)

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

### Option 3: Using Docker (Container lovers unite)

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=nixos&config=eyJjb21tYW5kIjoiZG9ja2VyIiwiYXJncyI6WyJydW4iLCItLXJtIiwiLWkiLCJnaGNyLmlvL3V0ZW5zaWxzL21jcC1uaXhvcyJdfQ%3D%3D)

```json
{
  "mcpServers": {
    "nixos": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/utensils/mcp-nixos"]
    }
  }
}
```

That's it. Your AI assistant now has access to real NixOS data instead of making things up. You're welcome.

## What Is This Thing?

MCP-NixOS is a Model Context Protocol server that gives your AI assistant accurate, real-time information about:

- **NixOS packages** (130K+ packages that actually exist)
- **Configuration options** (23K+ ways to break your system)
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

### 📦 Version History Tools

- `nixhub_package_versions(package, limit)` - Get version history with commit hashes
- `nixhub_find_version(package, version)` - Smart search for specific versions

### 🏠 Home Manager Tools

- `home_manager_search(query)` - Search user config options
- `home_manager_info(name)` - Get option details (with suggestions!)
- `home_manager_stats()` - See what's available
- `home_manager_list_options()` - Browse all 89 categories
- `home_manager_options_by_prefix(prefix)` - Explore options by prefix

### 🍎 Darwin Tools

- `darwin_search(query)` - Search macOS options
- `darwin_info(name)` - Get option details
- `darwin_stats()` - macOS configuration statistics
- `darwin_list_options()` - Browse all 17 categories
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

### Local Development Setup

Want to test your changes in Claude Code or another MCP client? Create a `.mcp.json` file in your project directory:

```json
{
  "mcpServers": {
    "nixos": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/hackerman/Projects/mcp-nixos",
        "mcp-nixos"
      ]
    }
  }
}
```

Replace `/home/hackerman/Projects/mcp-nixos` with your actual project path (yes, even you, Windows users with your `C:\Users\CoolDev\...` paths).

This `.mcp.json` file:

- **Automatically activates** when you launch Claude Code from the project directory
- **Uses your local code** instead of the installed package
- **Enables real-time testing** - just restart Claude Code after changes
- **Already in .gitignore** so you won't accidentally commit your path

### With Nix (The Blessed Path)

```bash
nix develop
menu  # Shows all available commands

# Common tasks
run        # Start the server (now with FastMCP!)
run-tests  # Run all tests (now async!)
lint       # Format and check code (ruff replaced black/flake8)
typecheck  # Check types (mypy still judges you)
build      # Build the package
publish    # Upload to PyPI (requires credentials)
```

### Without Nix (The Path of Pain)

```bash
# Install development dependencies
uv pip install -e ".[dev]"  # or pip install -e ".[dev]"

# Run the server locally
uv run mcp-nixos  # or python -m mcp_nixos.server

# Development commands
pytest tests/          # Now with asyncio goodness
ruff format mcp_nixos/ # black is so 2023
ruff check mcp_nixos/  # flake8 is for boomers
mypy mcp_nixos/        # Still pedantic as ever

# Build and publish
python -m build        # Build distributions
twine upload dist/*    # Upload to PyPI
```

### Testing Philosophy

- **330 tests** that actually test things
- **Real API calls** because mocks are for cowards (await real_courage())
- **Plain text validation** ensuring no XML leaks through
- **Cross-platform tests** because Windows users deserve pain too
- **14 test files** because organization is a virtue

## Environment Variables

Just one. We're minimalists now:

| Variable | Description | Default |
|----------|-------------|---------|
| `ELASTICSEARCH_URL` | NixOS API endpoint | <https://search.nixos.org/backend> |

## Troubleshooting

### Nix Sandbox Error

If you encounter this error when running via Nix:

```text
error: derivation '/nix/store/...-python3.11-watchfiles-1.0.4.drv' specifies a sandbox profile,
but this is only allowed when 'sandbox' is 'relaxed'
```

**Solution**: Run with relaxed sandbox mode:

```bash
nix run --option sandbox relaxed github:utensils/mcp-nixos --
```

**Why this happens**: The `watchfiles` package (a transitive dependency via MCP) requires custom sandbox permissions for file system monitoring. This is only allowed when Nix's sandbox is in 'relaxed' mode instead of the default 'strict' mode.

**Permanent fix**: Add to your `/etc/nix/nix.conf`:

```ini
sandbox = relaxed
```

## Acknowledgments

This project queries data from several amazing services:

- **[NixHub.io](https://www.nixhub.io)** - Provides package version history and commit tracking
- **[search.nixos.org](https://search.nixos.org)** - Official NixOS package and option search
- **[Jetify](https://www.jetify.com)** - Creators of [Devbox](https://www.jetify.com/devbox) and NixHub

*Note: These services have not endorsed this tool. We're just grateful API consumers.*

## License

MIT - Because sharing is caring, even if the code hurts.

---

*Created by James Brink and maintained by masochists who enjoy Nix and async/await patterns.*

*Special thanks to the NixOS project for creating an OS that's simultaneously the best and worst thing ever.*
