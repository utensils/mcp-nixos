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

## Error handling

Test these produce clear errors:
- `action=invalid`
- `action=search, source=invalid, query=test`
- `action=info, source=flakes, query=test` (flakes don't support info)
- `action=options, source=nixos, query=test` (nixos doesn't support options browsing)

Summarize results in a table showing pass/fail status for each test.
