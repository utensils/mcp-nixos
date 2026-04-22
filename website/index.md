---
layout: home

title: MCP-NixOS
titleTemplate: Model Context Protocol for NixOS

hero:
  name: MCP-NixOS
  text: Because your AI shouldn't hallucinate package names.
  tagline: Real, up-to-the-second information about NixOS packages, options, Home Manager, nix-darwin, flakes, and friends — served over the Model Context Protocol.
  image:
    src: /images/mcp-nixos.png
    alt: MCP-NixOS
  actions:
    - theme: brand
      text: Get Started
      link: /usage
    - theme: alt
      text: View on GitHub
      link: https://github.com/utensils/mcp-nixos
    - theme: alt
      text: What is this?
      link: /about

features:
  - icon: 📦
    title: NixOS Packages & Options
    details: Search and inspect 130K+ packages and 23K+ system options. Stop guessing attribute names at 2am.
  - icon: 🏠
    title: Home Manager
    details: 5K+ user-level options for dotfile enthusiasts who have opinions about everything.
  - icon: 🍎
    title: nix-darwin
    details: 1K+ macOS settings Apple would rather you didn't know existed.
  - icon: ❄️
    title: Flakes & FlakeHub
    details: Search community flakes on search.nixos.org and the FlakeHub registry by Determinate Systems.
  - icon: 🧠
    title: Noogle + Nixvim
    details: 2K+ Nix functions with type signatures plus 5K+ Nixvim options. Because writing Nix is already hard enough.
  - icon: ⏱️
    title: Package Version History
    details: Historical versions with nixpkgs commit hashes via NixHub.io. Find that one Ruby version from 2019 you're pretending to still support.
  - icon: ☁️
    title: Binary Cache Status
    details: Before building Firefox for the next three hours, check cache.nixos.org and save yourself the pain.
  - icon: 🤖
    title: Plays Well With Claude
    details: Built on MCP, works with Claude, Cursor, and every other client that speaks the protocol.
  - icon: 🪶
    title: ~1,030 Tokens Total
    details: While other MCP servers hog your context like it's Black Friday, we're sipping minimalist tea in the corner.
  - icon: 🌍
    title: No Nix Required to Run
    details: This is an API client, not a rite of passage. Works on Windows, macOS, and Linux. Yes, even you.
  - icon: 📖
    title: Wiki + nix.dev
    details: Community wisdom from wiki.nixos.org and the official nix.dev tutorials, surfaced in one query.
  - icon: 🔌
    title: STDIO or HTTP
    details: Run it locally over STDIO or host it as a remote MCP server over HTTP. Your ops team will thank you.
---

<div style="text-align: center; margin-top: 3rem;">
  <a href="https://github.com/utensils/mcp-nixos/releases/latest" class="pill" target="_blank" rel="noopener">Latest release ↗</a>
  <span class="pill">2 MCP tools</span>
  <span class="pill">Plain text responses</span>
  <span class="pill">MIT</span>
</div>

## Quick Start

Paste this into your MCP client config. Congratulations, you now have access to real NixOS data.

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

Need more? [See all the ways to run it →](/usage)

## What This Actually Does

MCP-NixOS exposes **two** (yes, two) MCP tools to your AI assistant:

- **`nix`** — one unified query tool for search, info, stats, option browsing, channels, flake inputs, and binary cache lookups across every source below.
- **`nix_versions`** — package version history with nixpkgs commit hashes via NixHub.io.

All responses come back as **plain text**, because your LLM does not want to parse XML any more than you do.

## Sources Under the Hood

<div class="vp-raw" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-top: 1.5rem;">

- **[search.nixos.org](https://search.nixos.org)** — Official package & option index
- **[NixHub.io](https://www.nixhub.io)** — Versions, store paths, license metadata
- **[cache.nixos.org](https://cache.nixos.org)** — Binary cache status
- **[FlakeHub](https://flakehub.com)** — Determinate Systems flake registry
- **[noogle.dev](https://noogle.dev)** — Nix function signatures
- **[NuschtOS](https://github.com/NuschtOS/search)** — Nixvim option index
- **[wiki.nixos.org](https://wiki.nixos.org)** — Community wiki
- **[nix.dev](https://nix.dev)** — Official tutorials & guides
- **Local `/nix/store`** — Your pinned flake inputs, read directly

</div>

## Ready to stop arguing with your AI about whether `pkgs.firefox_esr` exists?

<div style="text-align: center; margin-top: 1.5rem;">

[Get Started →](/usage){.vp-button}

</div>
