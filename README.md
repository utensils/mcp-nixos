# MCP-NixOS - Because Your AI Assistant Shouldn't Hallucinate About Packages

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![smithery badge](https://smithery.ai/badge/@utensils/mcp-nixos)](https://smithery.ai/server/@utensils/mcp-nixos)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/99cc55fb-a5c5-4473-b315-45a6961b2e8c)

> **🎉 REFACTORED**: Version 1.0.0 represents a complete rewrite from 9,755 lines down to under 400. Because sometimes less is more, and more is just showing off.
>
> **📢 RENAMED**: This package was renamed from `nixmcp` to `mcp-nixos` in version 0.2.0. Update your references accordingly or continue living in the past—your choice.

## What The Hell Is This Thing?

MCP-NixOS is a Model Context Protocol server that stops your AI assistant from making stuff up about NixOS. Because let's face it—the only thing worse than confusing NixOS documentation is an AI confidently hallucinating about it.

It provides real-time access to:

- NixOS packages (yes, the ones that actually exist)
- System options (the ones you'll spend hours configuring)
- Home Manager settings (for when system-wide chaos isn't enough)
- nix-darwin macOS configurations (because Apple users need complexity too)

## Quick Start: For the Chronically Impatient

Look, we both know you're just going to skim this README and then complain when things don't work. Here's the bare minimum to get started:

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

There. Now your AI assistant can actually give you correct information about NixOS instead of hallucinating package names from 2019. You're welcome.

### Environment Variables (For the Paranoid)

Since v1.0.0, the server operates statelessly. No cache directories to fill up your disk, no orphan processes to haunt your system:

| Variable            | Description                              | Default                          |
| ------------------- | ---------------------------------------- | -------------------------------- |
| `ELASTICSEARCH_URL` | NixOS Elasticsearch API URL             | https://search.nixos.org/backend |

That's it. That's the list. We removed all the complexity because, let's be honest, you weren't going to configure those other variables anyway.

## Features That Might Actually Work

- **NixOS Resources**: Packages and system options via Elasticsearch API
  - Multiple channels: unstable (for the brave), stable (for the boring), and specific versions
  - Detailed package metadata that tells you everything except how to make it work
- **Home Manager**: User configuration options via live HTML parsing
  - Programs, services, and settings you'll spend weekends configuring
  - Hierarchical paths for when you want to get absurdly specific
- **nix-darwin**: macOS configuration for the "I use NixOS BTW" Apple users
  - System defaults, services, and settings Apple never intended you to touch
  - Break your Mac in new and exciting ways!
- **Stateless Operation**: Because state management is overrated
  - No cache to corrupt, no files to clean up
  - Direct API calls every time (your internet better be working)
- **Structured Output**: XML responses that AI models actually understand
  - Clear error messages when things go wrong (and they will)
  - Consistent format across all tools

## MCP Resources & Tools: The Power Tools You Didn't Know You Needed

### NixOS: The OS That Makes You Feel Simultaneously Smarter and Dumber

**Resources:**

- `nixos://package/{name}` - Find that package you're sure exists
- `nixos://search/packages/{query}` - Search for packages that might exist
- `nixos://search/options/{query}` - Search system options you'll misconfig
- `nixos://option/{name}` - Get option info you'll still manage to mess up
- `nixos://search/programs/{name}` - Find packages providing programs
- `nixos://packages/stats` - Stats to impress your nerd friends

**Tools:**

- `nixos_search(query, type, channel)` - The search function you'll use most
- `nixos_info(name, type, channel)` - Get package or option details
- `nixos_stats(channel)` - Get NixOS statistics nobody asked for

**Channels:**

- `unstable` (default) - Living on the edge where nothing is stable, including your sanity
- `stable` (24.11) - For those who prefer their breakage on a schedule
- Old versions - For when you're feeling nostalgic about earlier failures

### Home Manager: Because System-Wide Configuration Wasn't Complicated Enough

**Resources:**

- `home-manager://search/options/{query}` - Search user config options
- `home-manager://option/{name}` - Option details you'll screenshot for later
- `home-manager://options/prefix/{prefix}` - All options under a prefix
- `home-manager://options/{category}` - Category options (programs, services, etc.)

**Tools:**

- `home_manager_search(query)` - Search configuration options
- `home_manager_info(name)` - Get option details with actual explanation
- `home_manager_options_by_prefix(option_prefix)` - Get options by prefix
- `home_manager_list_options()` - List all option categories when overwhelmed

### nix-darwin: For Mac Users Who Crave Pain

**Resources:**

- `darwin://search/options/{query}` - Search macOS options
- `darwin://option/{name}` - Option details for your Apple devices
- `darwin://options/prefix/{prefix}` - All options under a prefix
- `darwin://options/{category}` - Category options (system, services, etc.)

**Tools:**

- `darwin_search(query)` - Search macOS configuration options
- `darwin_info(name)` - Get option details Apple doesn't want you to know
- `darwin_options_by_prefix(option_prefix)` - Get options by prefix
- `darwin_list_options()` - List all option categories

### Tool Usage Examples (Copy/Paste Ready)

```python
# NixOS examples for when you're pretending to know what you're doing
nixos_search(query="firefox", type="packages", channel="unstable")
nixos_search(query="postgresql", type="options", channel="stable")
nixos_info(name="firefox", type="package")
nixos_info(name="services.postgresql.enable", type="option")

# Home Manager examples for the domestic configuration enthusiasts
home_manager_search(query="programs.git")
home_manager_info(name="programs.firefox.enable")
home_manager_options_by_prefix(option_prefix="programs.git")

# nix-darwin examples for the masochistic Mac users
darwin_search(query="system.defaults.dock")
darwin_info(name="services.yabai.enable")
darwin_options_by_prefix(option_prefix="system.defaults")
```

## Installation & Configuration: The Part You'll Probably Skip

### Install It (Pick Your Poison)

```bash
# Option 1: Install with pip like a normie
pip install mcp-nixos

# Option 2: Install with uv because you're too cool for pip
uv pip install mcp-nixos

# Option 3: Run directly with uvx (recommended for the truly enlightened)
uvx --install-deps mcp-nixos

# Option 4: Install with Nix like a true believer (requires Nix with flakes enabled)
nix profile install github:utensils/mcp-nixos
```

### Configure It (The Part You'll Definitely Mess Up)

Add to your MCP configuration file (e.g., `~/.config/claude/config.json`):

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

If you installed using Nix:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "mcp-nixos"
    }
  }
}
```

Or run directly from GitHub without installing:

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

For development with the source code (for those who enjoy punishment):

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uv",
      "args": ["run", "-m", "mcp_nixos.__main__"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

### Cache & Channels: Where Magic Happens and Files Disappear

**Cache System:**

- Default locations that you'll forget about in 5 minutes
- Stores HTML content, serialized data, and search indices
- Works offline once cached (the only feature you'll actually appreciate)

**NixOS Channels:**

- `unstable`: Latest NixOS unstable (for daredevils)
- `stable`: Current stable release (for the risk-averse)
- `24.11`: Specific version reference (for the historically inclined)

## Development: For Those Not Content With Just Using Things

### Dependencies (Now With 40% Less Bloat!)

This project uses `pyproject.toml` and has been on a diet. We went from 5 dependencies to 3:

- `mcp>=1.5.0` - The protocol that makes this all possible
- `requests>=2.32.3` - For talking to APIs like civilized people
- `beautifulsoup4>=4.13.3` - For parsing HTML that shouldn't exist

That's it. No more psutil, no more python-dotenv. We're living lean and mean.

```bash
# Install development dependencies for the brave
pip install -e ".[dev]"

# Or with uv (recommended for the enlightened)
uv pip install -e ".[dev]"
```

### Using Nix (Of Course There's a Nix Development Environment)

```bash
# Enter dev shell and see available commands
nix develop && menu

# Common commands for common folk
run         # Start the server (and your journey into madness)
run-tests   # Run tests with coverage (expose the flaws)
lint        # Format and lint code (fix the mess you made)
publish     # Build and publish to PyPI (share your pain)
```

### Native Nix Package (For True NixOS Enthusiasts)

The project can also be used directly as a Nix package:

```bash
# Build the package without installing it
nix build github:utensils/mcp-nixos

# Run it directly without installing
nix run github:utensils/mcp-nixos

# Install to your user profile
nix profile install github:utensils/mcp-nixos

# Use in your NixOS configuration
{
  inputs.mcp-nixos.url = "github:utensils/mcp-nixos";
  
  outputs = { self, nixpkgs, mcp-nixos }: {
    nixosConfigurations.yourhostname = nixpkgs.lib.nixosSystem {
      modules = [
        ({ pkgs, ... }: {
          environment.systemPackages = [ mcp-nixos.packages.${pkgs.system}.default ];
        })
      ];
    };
  };
}
```

### Testing (Yes, We Actually Do That)

Tests use real Elasticsearch API calls instead of mocks because we're not afraid of the real world:

```bash
# Run tests with coverage (default and recommended)
run-tests

# Run tests without coverage (for those who prefer blissful ignorance)
run-tests --no-coverage
```

Code coverage is tracked on [Codecov](https://codecov.io/gh/utensils/mcp-nixos) (where we pretend to care about 100% coverage).

## Using with LLMs: The Whole Point of This Exercise

Once configured, use MCP-NixOS in your prompts with MCP-compatible models:

```
# NixOS resources for the confused
~nixos://package/python
~nixos://option/services.nginx
~nixos://search/packages/firefox

# Home Manager resources for the domestically challenged
~home-manager://search/options/programs.git
~home-manager://option/programs.firefox.profiles

# nix-darwin resources for the Apple addicted
~darwin://search/options/system.defaults.dock

# NixOS tools for the tool-inclined
~nixos_search(query="postgresql", type="options")
~nixos_info(name="firefox", type="package", channel="unstable")

# Home Manager tools for home improvement
~home_manager_search(query="programs.zsh")
~home_manager_info(name="programs.git.userName")

# nix-darwin tools for the Mac masochists
~darwin_search(query="services.yabai")
~darwin_info(name="system.defaults.dock.autohide")
```

The LLM will fetch information through the MCP server and might actually give you correct information for once.

## Implementation Details: The 95.7% Smaller House of Cards

### Code Architecture: Less Is More (Or So They Tell Me)

MCP-NixOS v1.0.0 is a masterclass in minimalism. We threw away 95.7% of the code and somehow it still works:

- `mcp_nixos/server.py` - 393 lines of pure, unadulterated functionality
- `mcp_nixos/__main__.py` - 28 lines that just work™
- That's it. That's the implementation.

Gone are the days of:
- Complex caching layers that nobody understood
- Abstract client interfaces that abstracted nothing
- Context managers managing contexts that didn't need managing
- Utility functions that were neither utilitarian nor functional

### The Great Refactoring of 2025

We went from this:
```
9,755 lines across 47 files in 6 directories
```

To this:
```
416 lines across 2 files that actually matter
```

That's a 95.7% reduction in code, a 100% reduction in complexity, and a 0% reduction in functionality.

### Direct API Integration: No More Middlemen

- **NixOS**: Direct Elasticsearch queries with proper authentication
- **Home Manager**: Live HTML parsing (because they don't have an API)
- **nix-darwin**: More HTML parsing (sensing a pattern here?)

No abstractions, no frameworks, no "enterprise patterns". Just functions that do what they say on the tin.

### Structured XML Output: Because AI Models Are Picky Eaters

Every response is carefully crafted XML that AI models can digest:

```xml
<package_info>
  <name>firefox</name>
  <version>123.0</version>
  <description>A web browser that respects your privacy</description>
</package_info>
```

Clean, consistent, and parseable. Unlike my git commit history.

## What is Model Context Protocol?

### For Those Who Skipped Straight to the End

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that connects LLMs to external data and tools using JSON messages over stdin/stdout. This project implements MCP to give AI assistants access to NixOS, Home Manager, and nix-darwin resources, so they can finally stop making things up about your operating system.

## License

MIT (Because I'm not a monster)

*The NixOS snowflake logo is used with attribution to the NixOS project. See [attribution information](website/public/images/attribution.md) for details.*

---

_Created by James Brink, self-proclaimed Tinkerer of Terror, who somehow manages to make things work despite himself._
