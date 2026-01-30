---
allowed-tools: mcp__nixos__nix, mcp__nixos__nix_versions
description: Test MCP NixOS Tools (project)
---

# Test MCP NixOS Tools

Test the `nix` and `nix_versions` MCP tools by running through these scenarios:

## nix tool

**Search** (all sources):
- `action=search, source=nixos, type=packages, query=firefox`
- `action=search, source=nixos, type=options, query=nginx`
- `action=search, source=home-manager, query=git`
- `action=search, source=darwin, query=dock`
- `action=search, source=flakes, query=atuin`
- `action=search, source=flakehub, query=nixpkgs`
- `action=search, source=nixvim, query=telescope`

**Info** (package and option):
- `action=info, source=nixos, type=package, query=firefox`
- `action=info, source=nixos, type=option, query=services.nginx.enable`
- `action=info, source=home-manager, query=programs.git.enable`
- `action=info, source=darwin, query=system.defaults.dock.autohide`
- `action=info, source=flakehub, query=NixOS/nixpkgs`
- `action=info, source=nixvim, query=plugins.telescope.enable`

**Stats** (all sources):
- `action=stats, source=nixos`
- `action=stats, source=home-manager`
- `action=stats, source=darwin`
- `action=stats, source=flakes`
- `action=stats, source=flakehub`
- `action=stats, source=nixvim`

**Options browsing**:
- `action=options, source=home-manager, query=programs.git`
- `action=options, source=darwin, query=system`
- `action=options, source=nixvim, query=plugins`

**Channels**:
- `action=channels`

**Flake Inputs** (requires nix installed, uses current directory's flake):
- `action=flake-inputs, type=list` - list all inputs with store paths
- `action=flake-inputs, type=ls, query=nixpkgs` - list root of nixpkgs input
- `action=flake-inputs, type=ls, query=nixpkgs:pkgs/by-name` - list subdirectory
- `action=flake-inputs, type=read, query=nixpkgs:flake.nix` - read flake.nix from input
- `action=flake-inputs, type=read, query=flake-parts:flake.nix, limit=50` - read with line limit

## nix_versions tool

- `package=python, limit=3`
- `package=nodejs, version=20.0.0`
- `package=nonexistent-xyz-123` (should return NOT_FOUND)

## Edge cases

**Channel parameter**:
- `action=search, source=nixos, channel=stable, query=firefox, limit=3`

**Programs type**:
- `action=search, source=nixos, type=programs, query=vim, limit=3`

**Empty results**:
- `action=search, source=nixos, query=xyznonexistent12345` (should return "No packages found")
- `action=info, source=nixos, query=nonexistentpkg123` (should return NOT_FOUND)

**Category listing (no prefix)**:
- `action=options, source=home-manager` (should list all categories)

**Flake inputs with custom source path**:
- `action=flake-inputs, type=list, source=/path/to/other/flake` (use source for different flake dir)

## Error handling

Test these produce clear errors:
- `action=invalid`
- `action=search, source=invalid, query=test`
- `action=info, source=flakes, query=test` (flakes don't support info)
- `action=options, source=nixos, query=test` (nixos doesn't support options browsing)
- `action=flake-inputs, type=ls` (missing query - should error)
- `action=flake-inputs, type=read, query=nixpkgs` (missing file path - should error)
- `action=flake-inputs, type=ls, query=nonexistent-input` (should return NOT_FOUND with available inputs)
- `action=flake-inputs, type=read, query=nixpkgs:nonexistent/file.nix` (should return NOT_FOUND)
- `action=flake-inputs, source=/tmp/not-a-flake` (should return FLAKE_ERROR)

Summarize results in a table showing pass/fail status for each test.
