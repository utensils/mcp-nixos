---
title: Usage
description: How to run MCP-NixOS in your MCP client of choice.
---

# Usage

## Pick Your Poison

We've got five ways to run this thing. They all do the same thing, so just pick based on
what tools you already have installed. Or try all five. We don't judge.

::: tip No Nix Required
This tool works on any system — Windows, macOS, Linux. You're just querying web APIs.
Yes, even you, Windows users.
:::

### Option 1: uvx {#option-1-uvx}

<UsageOption title="Recommended for most humans" note="Pro tip: this installs nothing permanently. It's like a one-night stand with software.">

The civilized approach. If you've got Python and can install things like a normal person,
this is for you.

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

</UsageOption>

### Option 2: Nix {#option-2-nix}

<UsageOption title="For the enlightened" alt note="Bonus: this method makes you feel superior at developer meetups.">

You're already using Nix, so you probably think you're better than everyone else.
And you know what? You might be right.

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

</UsageOption>

### Option 2b: Declarative Nix {#option-2b-declarative-nix}

<UsageOption title="The true Nix way" alt note="Finally, a package that slots into your 3,000-line flake.nix without drama.">

`mcp-nixos` ships in [nixpkgs](https://search.nixos.org/packages?channel=unstable&show=mcp-nixos&query=mcp-nixos).
Add it to your config like everything else you've spent 400 hours perfecting.

```nix
# NixOS (configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];

# Home Manager (home.nix)
home.packages = [ pkgs.mcp-nixos ];

# nix-darwin (darwin-configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];
```

Or consume the flake directly via the provided overlay:

```nix
# flake.nix
{
  inputs.mcp-nixos.url = "github:utensils/mcp-nixos";

  outputs = { nixpkgs, mcp-nixos, ... }: {
    nixpkgs.overlays = [ mcp-nixos.overlays.default ];
    # pkgs.mcp-nixos is now available everywhere
  };
}
```

</UsageOption>

### Option 3: Docker {#option-3-docker}

<UsageOption title="Container enthusiasts unite" note="May consume 500MB of disk for a 10MB Python script. But hey, it's &quot;isolated&quot;!">

Because why install software directly when you can wrap it in 17 layers of abstraction?
At least it's reproducible. Probably.

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

Multi-arch images (amd64 + arm64) on both GHCR and Docker Hub:

- `ghcr.io/utensils/mcp-nixos`
- `utensils/mcp-nixos`

</UsageOption>

### Option 4: HTTP Transport (Remote MCP) {#option-4-http-transport}

<UsageOption title="For grown-up deployments" alt note="Defaults to 127.0.0.1:8000/mcp. Works with any MCP client that speaks HTTP.">

Run the server over HTTP instead of STDIO. Great for shared setups, remote hosts, or when
you want one server instance serving multiple clients like a responsible adult.

```bash
# Start with defaults: http://127.0.0.1:8000/mcp
MCP_NIXOS_TRANSPORT=http mcp-nixos

# Custom host, port, and path
MCP_NIXOS_TRANSPORT=http \
  MCP_NIXOS_HOST=0.0.0.0 \
  MCP_NIXOS_PORT=9090 \
  MCP_NIXOS_PATH=/api/mcp \
  mcp-nixos

# Stateless mode — no per-client sessions
MCP_NIXOS_TRANSPORT=http MCP_NIXOS_STATELESS_HTTP=1 mcp-nixos
```

</UsageOption>

### Option 5: Pi Coding Agent {#option-5-pi-coding-agent}

<UsageOption title="For Pi users" note="Pi doesn't speak MCP natively, so we meet it halfway.">

[Pi](https://www.npmjs.com/package/@mariozechner/pi-coding-agent) doesn't speak MCP
natively. Two supported paths:

**A. pi-mcp-adapter** (recommended — single source of truth):

```bash
pi install npm:pi-mcp-adapter
```

Then add to `~/.pi/agent/mcp.json`:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"],
      "lifecycle": "lazy"
    }
  }
}
```

**B. Project-local extension:** the repo ships `.pi/extensions/mcp-nixos.ts`, auto-loaded
when you run `pi` inside the cloned repo. Optional: `cd .pi && npm install` for editor
type resolution. Pi runs it either way.

</UsageOption>

## The Tools {#the-tools}

Just two. We consolidated 17 tools into 2 because your AI's context window isn't infinite.
**~1,030 tokens total.** You're welcome.

### `nix` — Unified Query Tool {#the-nix-tool}

One tool to rule them all:

```text
nix(action, query, source, type, channel, limit, version, system)
```

`version` and `system` are only used by `action="cache"`.

| Action | What it does |
|--------|-------------|
| `search` | Search packages, options, programs, flakes, wiki, docs |
| `info` | Get detailed info about a package, option, or function |
| `stats` | Counts, channels, categories |
| `browse` | Browse Home Manager / Darwin options by prefix (alias: `options`) |
| `channels` | List available NixOS channels |
| `flake-inputs` | Explore local flake inputs from the Nix store |
| `cache` | Check binary cache status for packages |
| `store` | Read files directly from `/nix/store` |

| Source | What it queries |
|--------|-----------------|
| `nixos` | Packages, options, programs (search.nixos.org) |
| `home-manager` | Home Manager options |
| `darwin` | nix-darwin options |
| `flakes` | Community flakes (search.nixos.org) |
| `flakehub` | FlakeHub registry (flakehub.com) |
| `nixvim` | Nixvim Neovim configuration options |
| `noogle` | Nix function signatures & docs (noogle.dev) |
| `wiki` | NixOS Wiki articles (wiki.nixos.org) |
| `nix-dev` | Official Nix docs (nix.dev) |
| `nixhub` | Package metadata & store paths (nixhub.io) |

#### Examples

```python
# Search NixOS packages
nix(action="search", query="firefox", source="nixos", type="packages")

# Get package info
nix(action="info", query="firefox", source="nixos", type="package")

# Search Home Manager options
nix(action="search", query="git", source="home-manager")

# Browse darwin options by prefix
nix(action="browse", source="darwin", query="system.defaults")

# Search Nixvim options
nix(action="search", query="telescope", source="nixvim")

# Search FlakeHub
nix(action="search", query="nixpkgs", source="flakehub")

# Noogle function lookup
nix(action="info", query="lib.attrsets.mapAttrs", source="noogle")

# NixOS Wiki
nix(action="search", query="nvidia", source="wiki")

# nix.dev tutorials
nix(action="search", query="packaging tutorial", source="nix-dev")

# NixHub rich metadata
nix(action="info", query="python", source="nixhub")

# Stats
nix(action="stats", source="nixos", channel="stable")

# Local flake inputs (requires Nix installed locally)
nix(action="flake-inputs", type="list")
nix(action="flake-inputs", type="ls",   query="nixpkgs:pkgs/by-name")
nix(action="flake-inputs", type="read", query="nixpkgs:flake.nix")
```

### `nix_versions` — Package Version History {#the-nix-versions-tool}

Historical package versions with nixpkgs commit hashes. Output includes:

- Package metadata (license, homepage, programs) when available
- Platform availability per version (Linux / macOS)
- nixpkgs commit hash for reproducible builds
- Attribute path for Nix expressions

```python
nix_versions(package, version, limit)
```

```python
# List recent versions with metadata
nix_versions(package="python", limit=5)

# Find a specific version
nix_versions(package="nodejs", version="20.0.0")
```

### Binary Cache & NixHub {#binary-cache-nixhub}

Two crowd-pleasers worth calling out separately.

**Check the binary cache before you commit to a three-hour build:**

```python
# Is hello cached?
nix(action="cache", query="hello")

# Specific version
nix(action="cache", query="python", version="3.12.0")

# Specific system
nix(action="cache", query="firefox", system="x86_64-linux")
```

Shows download size, unpacked size, compression method, and availability per platform.

**Grab rich metadata from NixHub.io:**

```python
# Search packages with metadata
nix(action="search", source="nixhub", query="nodejs")

# Detailed info — license, homepage, programs, store paths
nix(action="info", source="nixhub", query="python")
```

## Environment Variables {#environment-variables}

| Variable | Purpose | Default |
|----------|---------|---------|
| `MCP_NIXOS_TRANSPORT` | `stdio` or `http` | `stdio` |
| `MCP_NIXOS_HOST` | HTTP bind address | `127.0.0.1` |
| `MCP_NIXOS_PORT` | HTTP bind port | `8000` |
| `MCP_NIXOS_PATH` | HTTP MCP endpoint path | `/mcp` |
| `MCP_NIXOS_STATELESS_HTTP` | Set to `1` to disable per-client session state | unset |
| `ELASTICSEARCH_URL` | Override the NixOS search backend (for local testing) | unset |

## What Happens Next? {#what-happens-next}

Once you've picked your configuration method and added it to your MCP client:

- Your AI assistant stops making up NixOS package names
- You get actual, real-time information about 130K+ packages
- Configuration options that actually exist (shocking, we know)
- Version history that helps you find that one specific Ruby version from 2019
- Binary cache status so you know if you'll be waiting three hours to build Firefox

That's it. No complex setup. No 47-step installation guide. No sacrificing a USB stick to
the Nix gods. Just paste, reload, and enjoy an AI that actually knows what it's talking
about.

::: info Still confused?
Good news: that's what the AI is for. Just ask it.
:::
