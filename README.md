# MCP-NixOS - Because Your AI Shouldn't Hallucinate Package Names

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/utensils/mcp-nixos?utm_source=oss&utm_medium=github&utm_campaign=utensils%2Fmcp-nixos&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude-D97757?logo=claude&logoColor=white)](https://claude.ai)

## Quick Start

**🚨 No Nix/NixOS Required!** Works on any system - Windows, macOS, Linux. You're just querying APIs.

### Option 1: uvx (Recommended)

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

### Option 2: Nix

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

### Option 3: Docker

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

Your AI now has access to real NixOS data instead of making things up. You're welcome.

## What Is This?

An MCP server providing accurate, real-time information about:

- **NixOS packages** - 130K+ packages that actually exist
- **NixOS options** - 23K+ ways to configure your system
- **Home Manager** - 5K+ options for dotfile enthusiasts
- **nix-darwin** - 1K+ macOS settings Apple doesn't document
- **Nixvim** - 5K+ options for Neovim configuration via [NuschtOS search](https://github.com/NuschtOS/search)
- **Package versions** - Historical versions with commit hashes via [NixHub.io](https://www.nixhub.io)

## The Tools

Just two. We consolidated 17 tools into 2 because your AI's context window isn't infinite.

### `nix` - Unified Query Tool

One tool to rule them all:

```text
nix(action, query, source, type, channel, limit)
```

| Action | What it does |
|--------|-------------|
| `search` | Search packages, options, programs, or flakes |
| `info` | Get detailed info about a package or option |
| `stats` | Get counts and categories |
| `options` | Browse Home Manager/Darwin options by prefix |
| `channels` | List available NixOS channels |

| Source | What it queries |
|--------|----------------|
| `nixos` | Packages, options, programs |
| `home-manager` | Home Manager options |
| `darwin` | nix-darwin options |
| `flakes` | Community flakes |
| `nixvim` | Nixvim Neovim configuration options |

**Examples:**

```python
# Search NixOS packages
nix(action="search", query="firefox", source="nixos", type="packages")

# Get package info
nix(action="info", query="firefox", source="nixos", type="package")

# Search Home Manager options
nix(action="search", query="git", source="home-manager")

# Browse darwin options
nix(action="options", source="darwin", query="system.defaults")

# Search Nixvim options
nix(action="search", query="telescope", source="nixvim")

# Get Nixvim option info
nix(action="info", query="plugins.telescope.enable", source="nixvim")

# Get stats
nix(action="stats", source="nixos", channel="stable")
```

### `nix_versions` - Package Version History

Find historical versions with nixpkgs commit hashes:

```
nix_versions(package, version, limit)
```

**Examples:**

```python
# List recent versions
nix_versions(package="python", limit=5)

# Find specific version
nix_versions(package="nodejs", version="20.0.0")
```

## Installation

**You DON'T need Nix installed.** This runs anywhere Python runs.

```bash
# Run directly (no install)
uvx mcp-nixos

# Or install
pip install mcp-nixos
```

For Nix users:

```bash
nix run github:utensils/mcp-nixos
nix profile install github:utensils/mcp-nixos
```

## Development

```bash
nix develop          # Enter dev shell
nix build            # Build package
pytest tests/        # Run tests
ruff check .         # Lint
ruff format .        # Format
mypy mcp_nixos/      # Type check
```

## Acknowledgments

- **[NixHub.io](https://www.nixhub.io)** - Package version history
- **[search.nixos.org](https://search.nixos.org)** - Official NixOS search
- **[Jetify](https://www.jetify.com)** - Creators of Devbox and NixHub
- **[NuschtOS](https://github.com/NuschtOS/search)** - Static option search infrastructure powering Nixvim support
- **[Nixvim](https://github.com/nix-community/nixvim)** - Neovim configuration framework for Nix

## License

MIT - Because sharing is caring.

---

*Created by James Brink. Maintained by mass̶o̶c̶h̶i̶s̶t̶s̶ enthusiasts who enjoy Nix.*
