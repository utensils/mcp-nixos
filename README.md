# MCP-NixOS - Because Your AI Shouldn't Hallucinate Package Names

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![FlakeHub](https://img.shields.io/endpoint?url=https://flakehub.com/f/utensils/mcp-nixos/badge)](https://flakehub.com/flake/utensils/mcp-nixos)
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
- **FlakeHub** - 600+ flakes from [FlakeHub.com](https://flakehub.com) registry
- **Noogle** - 2K+ Nix functions with type signatures via [noogle.dev](https://noogle.dev)
- **NixOS Wiki** - Community documentation and guides from [wiki.nixos.org](https://wiki.nixos.org)
- **nix.dev** - Official Nix tutorials and guides from [nix.dev](https://nix.dev)
- **Package versions** - Historical versions with commit hashes via [NixHub.io](https://www.nixhub.io)
- **Local flake inputs** - Explore your pinned flake dependencies directly from the Nix store (requires Nix)

## The Tools

Just two. We consolidated 17 tools into 2 because your AI's context window isn't infinite.

**~365 tokens total.** That's it. While other MCP servers are hogging your context like it's Black Friday, we're sipping minimalist tea in the corner. Your AI gets NixOS superpowers without the bloat.

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
| `flake-inputs` | Explore local flake inputs from Nix store |

| Source | What it queries |
|--------|----------------|
| `nixos` | Packages, options, programs |
| `home-manager` | Home Manager options |
| `darwin` | nix-darwin options |
| `flakes` | Community flakes (search.nixos.org) |
| `flakehub` | FlakeHub registry (flakehub.com) |
| `nixvim` | Nixvim Neovim configuration options |
| `noogle` | Nix function signatures and docs (noogle.dev) |
| `wiki` | NixOS Wiki articles (wiki.nixos.org) |
| `nix-dev` | Official Nix documentation (nix.dev) |

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

# Search FlakeHub
nix(action="search", query="nixpkgs", source="flakehub")

# Get FlakeHub flake info
nix(action="info", query="NixOS/nixpkgs", source="flakehub")

# Search Noogle for Nix functions
nix(action="search", query="mapAttrs", source="noogle")

# Get Noogle function info
nix(action="info", query="lib.attrsets.mapAttrs", source="noogle")

# Browse Noogle function categories
nix(action="options", source="noogle", query="lib.strings")

# Search NixOS Wiki
nix(action="search", query="nvidia", source="wiki")

# Get Wiki page info
nix(action="info", query="Flakes", source="wiki")

# Search nix.dev documentation
nix(action="search", query="packaging tutorial", source="nix-dev")

# Get stats
nix(action="stats", source="nixos", channel="stable")

# List local flake inputs (requires Nix)
nix(action="flake-inputs", type="list")

# Browse files in a flake input
nix(action="flake-inputs", type="ls", query="nixpkgs:pkgs/by-name")

# Read a file from a flake input
nix(action="flake-inputs", type="read", query="nixpkgs:flake.nix")
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

### Declarative Installation (NixOS / Home Manager / nix-darwin)

mcp-nixos is available in [nixpkgs](https://search.nixos.org/packages?channel=unstable&show=mcp-nixos&query=mcp-nixos):

```nix
# NixOS (configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];

# Home Manager (home.nix)
home.packages = [ pkgs.mcp-nixos ];

# nix-darwin (darwin-configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];
```

Or use the flake directly with the provided overlay:

```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    mcp-nixos.url = "github:utensils/mcp-nixos";
  };

  outputs = { self, nixpkgs, mcp-nixos, ... }: {
    # Example: NixOS configuration
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [{
        nixpkgs.overlays = [ mcp-nixos.overlays.default ];
        environment.systemPackages = [ pkgs.mcp-nixos ];
      }];
    };

    # Example: Home Manager standalone
    homeConfigurations.myuser = home-manager.lib.homeManagerConfiguration {
      pkgs = import nixpkgs {
        system = "x86_64-linux";
        overlays = [ mcp-nixos.overlays.default ];
      };
      modules = [{
        home.packages = [ pkgs.mcp-nixos ];
      }];
    };
  };
}
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
- **[FlakeHub](https://flakehub.com)** - Flake registry by Determinate Systems
- **[Jetify](https://www.jetify.com)** - Creators of Devbox and NixHub
- **[Noogle](https://noogle.dev)** - Nix function search engine
- **[NuschtOS](https://github.com/NuschtOS/search)** - Static option search infrastructure powering Nixvim support
- **[Nixvim](https://github.com/nix-community/nixvim)** - Neovim configuration framework for Nix

## License

MIT - Because sharing is caring.

---

*Created by James Brink. Maintained by mass̶o̶c̶h̶i̶s̶t̶s̶ enthusiasts who enjoy Nix.*
