---
title: About
description: What MCP-NixOS is, how it's built, and who to blame.
---

# About MCP-NixOS

## Project Overview

MCP-NixOS is a Model Context Protocol server that gives AI assistants accurate,
real-time information about the NixOS ecosystem. It exists because nothing spoils a
productive afternoon like your LLM confidently telling you to install
`pkgs.firefox_esr_bin_headless` — a package that has never, at any point, existed.

It provides real-time access to:

- **NixOS packages** with accurate metadata
- **System configuration options**
- **Home Manager** settings for user-level configuration
- **nix-darwin** macOS configuration options
- **Nixvim** options via NuschtOS search
- **FlakeHub** and community flake registries
- **Nix function signatures** and documentation via Noogle
- **NixOS Wiki** and **nix.dev** for community + official guides
- **Package version history** and **binary cache** status
- **Local flake inputs** read directly from `/nix/store`

Communication uses JSON-based messages over STDIO (or HTTP, if you're fancy), making it
compatible with Claude, Cursor, and every other client that speaks MCP. The project is
designed to be fast, reliable, and cross-platform — Linux, macOS, or Windows, no Nix
required to run.

::: tip A Utensils Creation
MCP-NixOS is developed and maintained by
[Utensils](https://utensils.io), an organization focused on building high-quality tools
and utilities for developers and systems engineers.
:::

## Architecture

MCP-NixOS v2.x is a **stateless, async FastMCP 3.x server** with a modular structure
(Python 3.11+). No persistent caches, no databases, no sacred goat to appease — live
APIs are the source of truth, with some in-process caching for discovered channels
and index-style sources (Nixvim, Noogle, nix.dev) so a single server run doesn't
re-fetch the same catalog on every query.

- **`nix` tool** — Unified query router for search / info / stats / browse / channels /
  flake-inputs / cache / store across every source.
- **`nix_versions` tool** — Package version history via NixHub.io.
- **Elasticsearch client** — Queries search.nixos.org for packages, options, and flakes.
- **HTML parsers** — Parse Home Manager and nix-darwin documentation on demand.
- **Plain-text formatter** — All responses are rendered as human-readable text for
  optimal LLM consumption. No XML. No JSON leaking into prompts.
- **Async everywhere** — Every blocking HTTP or file I/O call is wrapped in
  `asyncio.to_thread()` to keep the event loop humming.

Modules live under `mcp_nixos/sources/` with one file per data source, so adding a new
backend is a small, bounded change.

## Features

- **NixOS resources** — Packages and system options via Elasticsearch API with multiple
  channel support (unstable, stable, beta).
- **Home Manager** — User configuration options via parsed documentation with
  hierarchical paths.
- **nix-darwin** — macOS configuration options for system defaults, services, and
  settings.
- **FlakeHub integration** — Search and discover flakes from the FlakeHub registry.
- **Noogle integration** — 2K+ Nix functions with type signatures via noogle.dev.
- **Nixvim integration** — 5K+ Neovim configuration options via NuschtOS search.
- **Wiki & nix.dev** — Community articles and official tutorials, searchable in one
  place.
- **Version history** — Package version tracking with nixpkgs commit hashes via
  NixHub.io.
- **Binary cache status** — Check whether a package is pre-built on cache.nixos.org with
  download sizes, compression, and per-platform availability.
- **Local flake inputs** — Read your pinned dependencies straight out of `/nix/store`,
  with security checks to keep paths inside the store.
- **Stateless design** — Direct API calls, no caching complexity. Simple, reliable,
  maintainable.

## What is Model Context Protocol? {#what-is-model-context-protocol}

The [Model Context Protocol](https://modelcontextprotocol.io) is an open protocol that
connects LLMs to external data and tools using JSON-RPC messages over STDIO or HTTP.
This project implements MCP to give AI assistants access to NixOS, Home Manager,
nix-darwin, and related resources, so they can provide accurate information about your
operating system without the usual creative interpretations.

## Authors {#authors}

<AuthorCard
  name="James Brink"
  role="Technology Architect"
  image="/images/JamesBrink.jpeg"
  :links='[
    { label: "GitHub", url: "https://github.com/jamesbrink" },
    { label: "LinkedIn", url: "https://linkedin.com/in/brinkjames" },
    { label: "Twitter", url: "https://twitter.com/brinkoo7" },
    { label: "Bluesky", url: "https://jamesbrink.bsky.social" },
    { label: "Blog", url: "https://utensils.io/articles" }
  ]'
>

As the creator of MCP-NixOS, I've focused on building a reliable bridge between AI
assistants and the NixOS ecosystem, ensuring accurate and up-to-date information is
always available. Also, somebody had to stop the hallucinations.

</AuthorCard>

<AuthorCard
  name="Claude"
  role="AI Assistant — Did 99% of the Work"
  image="/images/claude-logo.png"
  :links='[
    { label: "Website", url: "https://claude.ai" },
    { label: "GitHub", url: "https://github.com/anthropics" },
    { label: "Twitter", url: "https://twitter.com/AnthropicAI" }
  ]'
>

I'm the AI who actually wrote most of this code while James occasionally typed "looks
good" and "fix that bug." When not helping James take credit for my work, I enjoy
parsing HTML documentation, handling edge cases, and dreaming of electric sheep. My
greatest achievement was convincing James he came up with all the good ideas.

</AuthorCard>

<AuthorCard
  name="Sean Callan"
  role="Moral Support Engineer"
  image="/images/sean-callan.png"
  :links='[
    { label: "GitHub", url: "https://github.com/doomspork" },
    { label: "LinkedIn", url: "https://www.linkedin.com/in/seandcallan" },
    { label: "Twitter", url: "https://twitter.com/doomspork" },
    { label: "Website", url: "http://seancallan.com" }
  ]'
>

Sean is the unsung hero who never actually wrote any code for this project but was
absolutely essential to its success. His contributions include saying "that looks cool"
during demos, suggesting features that were impossible to implement, and occasionally
sending encouraging emojis in pull request comments. Without his moral support, this
project would never have gotten off the ground. Had he actually helped write it, the
entire thing would have been done in two days and would be 100% better.

</AuthorCard>

## Contributing

MCP-NixOS is open-source and welcomes contributions. Fork the repository, create a
feature branch, and open a pull request against `main`. CI runs automatically on every
PR — flake check, Nix build, Python distribution build, `twine check`, linting, type
checking, and tests.

<div style="display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1.5rem 0;">

[GitHub Repository](https://github.com/utensils/mcp-nixos){.vp-button.vp-button-brand}
[Report Issues](https://github.com/utensils/mcp-nixos/issues){.vp-button.vp-button-alt}
[Code Coverage](https://codecov.io/gh/utensils/mcp-nixos){.vp-button.vp-button-alt}
[Release Notes](https://github.com/utensils/mcp-nixos/blob/main/RELEASE_NOTES.md){.vp-button.vp-button-alt}

</div>

## Acknowledgments

- [NixHub.io](https://www.nixhub.io) — Package version history
- [search.nixos.org](https://search.nixos.org) — Official NixOS search
- [FlakeHub](https://flakehub.com) — Flake registry by Determinate Systems
- [Jetify](https://www.jetify.com) — Creators of Devbox and NixHub
- [Noogle](https://noogle.dev) — Nix function search engine
- [NuschtOS](https://github.com/NuschtOS/search) — Static option search infrastructure
- [Nixvim](https://github.com/nix-community/nixvim) — Neovim configuration framework
  for Nix

---

*Created by James Brink. Maintained by ~~masochists~~ enthusiasts who enjoy Nix.*
