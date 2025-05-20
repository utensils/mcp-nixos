# MCP-NixOS - Because Your AI Assistant Shouldn't Hallucinate About Packages

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![smithery badge](https://smithery.ai/badge/@utensils/mcp-nixos)](https://smithery.ai/server/@utensils/mcp-nixos)
[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/99cc55fb-a5c5-4473-b315-45a6961b2e8c)

> **⚠️ ACTIVE DEVELOPMENT**: This package is under active development. Like my career choices, it's constantly evolving.
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

### Environment Variables (For Control Freaks)

| Variable                    | Description                                        | Default                          |
| --------------------------- | -------------------------------------------------- | -------------------------------- |
| `MCP_NIXOS_LOG_LEVEL`       | How much you want to know about your failures      | INFO                             |
| `MCP_NIXOS_LOG_FILE`        | Where to document said failures                    | (nowhere—your secret is safe)    |
| `MCP_NIXOS_CACHE_DIR`       | Where to store stuff you'll forget about           | OS-specific cache locations\*    |
| `MCP_NIXOS_CACHE_TTL`       | How long until cache invalidation ruins your day   | 86400 (24h)                      |
| `MCP_NIXOS_CLEANUP_ORPHANS` | Whether to kill orphaned MCP processes on startup  | false                            |
| `KEEP_TEST_CACHE`           | Keep test cache directory for debugging (dev-only) | false                            |
| `ELASTICSEARCH_URL`         | NixOS Elasticsearch API URL                        | https://search.nixos.org/backend |

\*Default cache locations (where your gigabytes will quietly disappear to):

- Linux: `~/.cache/mcp_nixos/` (because ~/.cache wasn't cluttered enough)
- macOS: `~/Library/Caches/mcp_nixos/` (buried where you'll never look)
- Windows: `%LOCALAPPDATA%\mcp_nixos\Cache\` (lost in the void of Windows directories)

## Features That Might Actually Work

- **NixOS Resources**: Packages and system options via Elasticsearch API
  - Multiple channels: unstable (for the brave), stable (for the boring), and specific versions
  - Detailed package metadata that tells you everything except how to make it work
- **Home Manager**: User configuration options via parsed documentation
  - Programs, services, and settings you'll spend weekends configuring
  - Hierarchical paths for when you want to get absurdly specific
- **nix-darwin**: macOS configuration for the "I use NixOS BTW" Apple users
  - System defaults, services, and settings Apple never intended you to touch
  - Break your Mac in new and exciting ways!
- **Smart Caching**: Because nobody wants to wait for Elasticsearch queries
  - Reduces network requests and improves startup time
  - Works offline once cached (perfect for your next internet outage)
- **Rich Search**: Find what you need or something close enough
  - Fast in-memory search engine that's surprisingly not terrible
  - Related options for when you're not quite sure what you're looking for

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

### Dependencies (Because Nothing Stands Alone Anymore)

This project uses `pyproject.toml` because we're not animals.

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

## Implementation Details: The House of Cards Revealed

### Code Architecture: How We Made This Work (Somehow)

MCP-NixOS is organized into a modular structure that somehow manages to work despite all odds:

- `mcp_nixos/cache/` - Caching components that save your bandwidth and sanity
- `mcp_nixos/clients/` - API clients that talk to Elasticsearch and parse HTML docs
- `mcp_nixos/contexts/` - Context objects that keep everything from falling apart
- `mcp_nixos/resources/` - MCP resource definitions for all platforms
- `mcp_nixos/tools/` - MCP tool implementations that do the actual work
- `mcp_nixos/utils/` - Utility functions because we're not animals
- `mcp_nixos/server.py` - The glue that holds this house of cards together

### NixOS API Integration: The External Connection

Connects to the NixOS Elasticsearch API with:

- Multiple channel support (unstable, stable/24.11)
- Field-specific search boosts for better relevance
- Error handling that expects the worst but hopes for the best (story of my life)

### HTML Documentation Parsers: Where Dreams Go To Die

For Home Manager and nix-darwin options, we've committed crimes against HTML parsing:

1. **Documentation Parsers**: Extracts structured data through a combination of BeautifulSoup incantations, regex black magic, and the kind of determination that only comes from staring at malformed HTML for 72 hours straight.

2. **Search Engines**: Cobbled together with:

   - Inverted index for fast text search (when it doesn't fall over)
   - Prefix tree for hierarchical lookups (seemed like a good idea at 3 AM)
   - Result scoring based on an algorithm best described as "vibes-based sorting"

3. **Caching System**: Because parsing that HTML once was traumatic enough:
   - Stores HTML content, processed data structures, and search indices
   - Uses platform-specific cache locations so you don't have to think about it
   - Implements TTL-based expiration to refresh content when needed
   - Falls back gracefully when things inevitably go wrong (unlike my relationships)

## What is Model Context Protocol?

### For Those Who Skipped Straight to the End

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that connects LLMs to external data and tools using JSON messages over stdin/stdout. This project implements MCP to give AI assistants access to NixOS, Home Manager, and nix-darwin resources, so they can finally stop making things up about your operating system.

## License

MIT (Because I'm not a monster)

*The NixOS snowflake logo is used with attribution to the NixOS project. See [attribution information](website/public/images/attribution.md) for details.*

---

_Created by James Brink, self-proclaimed Tinkerer of Terror, who somehow manages to make things work despite himself._
