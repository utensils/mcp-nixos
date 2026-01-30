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
- `action=search, source=wiki, query=nvidia` (NixOS Wiki)
- `action=search, source=nix-dev, query=flakes` (nix.dev documentation)
- `action=search, source=noogle, query=mapAttrs` (Noogle function search)

**Info** (package and option):
- `action=info, source=nixos, type=package, query=firefox`
- `action=info, source=nixos, type=option, query=services.nginx.enable`
- `action=info, source=home-manager, query=programs.git.enable`
- `action=info, source=darwin, query=system.defaults.dock.autohide`
- `action=info, source=flakehub, query=NixOS/nixpkgs`
- `action=info, source=nixvim, query=plugins.telescope.enable`
- `action=info, source=wiki, query=Flakes` (NixOS Wiki page)
- `action=info, source=noogle, query=lib.attrsets.mapAttrs` (Noogle function info)

**Stats** (all sources):
- `action=stats, source=nixos`
- `action=stats, source=home-manager`
- `action=stats, source=darwin`
- `action=stats, source=flakes`
- `action=stats, source=flakehub`
- `action=stats, source=nixvim`
- `action=stats, source=noogle`

**Options browsing**:
- `action=options, source=home-manager, query=programs.git`
- `action=options, source=darwin, query=system`
- `action=options, source=nixvim, query=plugins`
- `action=options, source=noogle, query=lib.strings`

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

## Wiki source (wiki.nixos.org)

**Search tests**:
- `action=search, source=wiki, query=installation, limit=5` - common topic
- `action=search, source=wiki, query=nvidia, limit=5` - hardware topic
- `action=search, source=wiki, query=flakes, limit=10` - Nix concept
- `action=search, source=wiki, query=home-manager, limit=5` - related tool
- `action=search, source=wiki, query=gaming, limit=5` - use case topic
- `action=search, source=wiki, query=xyznonexistent12345, limit=5` (should return "No wiki articles found")

**Info tests** (get page content):
- `action=info, source=wiki, query=Flakes` - popular page
- `action=info, source=wiki, query=Nvidia` - hardware page
- `action=info, source=wiki, query=NixOS` - main topic
- `action=info, source=wiki, query=Home Manager` - related tool (space in title)
- `action=info, source=wiki, query=NonExistentPageXYZ123` (should return NOT_FOUND)

**Edge cases**:
- `action=search, source=wiki, query=NixOS, limit=1` - minimum limit
- `action=search, source=wiki, query=configuration, limit=100` - maximum limit
- `action=info, source=wiki, query=Python` - page with special characters in content

## Noogle source (noogle.dev - Nix function search)

**Search tests**:
- `action=search, source=noogle, query=mapAttrs, limit=5` - common function
- `action=search, source=noogle, query=concatStrings, limit=5` - string function
- `action=search, source=noogle, query=filter, limit=10` - list function
- `action=search, source=noogle, query=hasAttr, limit=5` - attrset function
- `action=search, source=noogle, query=builtins.map, limit=5` - builtin function
- `action=search, source=noogle, query=mkDerivation, limit=5` - pkgs function
- `action=search, source=noogle, query=xyznonexistent12345, limit=5` (should return "No Noogle functions found")

**Info tests** (get function details):
- `action=info, source=noogle, query=lib.attrsets.mapAttrs` - popular function with aliases
- `action=info, source=noogle, query=builtins.map` - builtin with primop info
- `action=info, source=noogle, query=lib.strings.concatStrings` - string function
- `action=info, source=noogle, query=lib.lists.filter` - list function
- `action=info, source=noogle, query=lib.trivial.id` - simple function
- `action=info, source=noogle, query=nonexistent.function.xyz` (should return NOT_FOUND with suggestions)

**Stats tests**:
- `action=stats, source=noogle` - should show total functions, categories, with signatures count

**Options browsing** (function categories):
- `action=options, source=noogle` - list all categories (no prefix)
- `action=options, source=noogle, query=lib.strings` - string functions
- `action=options, source=noogle, query=lib.attrsets` - attrset functions
- `action=options, source=noogle, query=lib.lists` - list functions
- `action=options, source=noogle, query=builtins` - builtin functions
- `action=options, source=noogle, query=pkgs` - package functions
- `action=options, source=noogle, query=nonexistent.category` (should return "No Noogle functions found")

**Edge cases**:
- `action=search, source=noogle, query=map, limit=1` - minimum limit, common term
- `action=search, source=noogle, query=lib, limit=100` - broad query, maximum limit
- `action=search, source=noogle, query=String, limit=5` - case sensitivity test
- `action=info, source=noogle, query=builtins.mapAttrs` - alias lookup (should find lib.attrsets.mapAttrs)
- `action=info, source=noogle, query=lib.mapAttrs` - another alias lookup

**Type signature verification**:
- `action=info, source=noogle, query=lib.attrsets.mapAttrs` - should show type signature
- `action=search, source=noogle, query=AttrSet, limit=5` - search by type term

## nix-dev source (nix.dev documentation)

**Search tests**:
- `action=search, source=nix-dev, query=flakes, limit=5` - core concept
- `action=search, source=nix-dev, query=tutorial, limit=10` - documentation type
- `action=search, source=nix-dev, query=packaging, limit=5` - common task
- `action=search, source=nix-dev, query=derivation, limit=5` - Nix concept
- `action=search, source=nix-dev, query=language, limit=5` - Nix language docs
- `action=search, source=nix-dev, query=best practices, limit=5` - guide topic
- `action=search, source=nix-dev, query=xyznonexistent12345, limit=5` (should return "No nix.dev documentation found")

**Edge cases**:
- `action=search, source=nix-dev, query=nix, limit=1` - minimum limit
- `action=search, source=nix-dev, query=getting started, limit=20` - multi-word query
- `action=search, source=nix-dev, query=FAQ, limit=5` - short query

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
- `action=info, source=nix-dev, query=test` (nix-dev doesn't support info - should suggest using search)
- `action=stats, source=wiki` (wiki doesn't support stats)
- `action=stats, source=nix-dev` (nix-dev doesn't support stats)
- `action=options, source=nixos, query=test` (nixos doesn't support options browsing)
- `action=options, source=wiki, query=test` (wiki doesn't support options browsing)
- `action=options, source=nix-dev, query=test` (nix-dev doesn't support options browsing)
- `action=info, source=noogle, query=` (empty query - should error)
- `action=search, source=noogle, query=` (empty query - should error)
- `action=flake-inputs, type=ls` (missing query - should error)
- `action=flake-inputs, type=read, query=nixpkgs` (missing file path - should error)
- `action=flake-inputs, type=ls, query=nonexistent-input` (should return NOT_FOUND with available inputs)
- `action=flake-inputs, type=read, query=nixpkgs:nonexistent/file.nix` (should return NOT_FOUND)
- `action=flake-inputs, source=/tmp/not-a-flake` (should return FLAKE_ERROR)

## Output format verification

All responses should be plain text (no XML/JSON):
- Search results should show article/doc titles with URLs
- Wiki info should show page title, URL, and extract
- Noogle search should show function paths with type signatures and aliases
- Noogle info should show function path, type, aliases, description, example, and source position
- Noogle stats should show total functions, categories, and top categories
- Error messages should be clear and actionable

Summarize results in a table showing pass/fail status for each test.
