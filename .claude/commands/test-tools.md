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
- `action=search, source=nixhub, query=python` (NixHub package search)

**Info** (package and option):
- `action=info, source=nixos, type=package, query=firefox`
- `action=info, source=nixos, type=option, query=services.nginx.enable`
- `action=info, source=home-manager, query=programs.git.enable`
- `action=info, source=darwin, query=system.defaults.dock.autohide`
- `action=info, source=flakehub, query=NixOS/nixpkgs`
- `action=info, source=nixvim, query=plugins.telescope.enable`
- `action=info, source=wiki, query=Flakes` (NixOS Wiki page)
- `action=info, source=noogle, query=lib.attrsets.mapAttrs` (Noogle function info)
- `action=info, source=nixhub, query=ripgrep` (NixHub package info with rich metadata)

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

**Cache** (binary cache status checking):
- `action=cache, query=hello` - check cache status for hello package (all systems)
- `action=cache, query=firefox, version=latest` - check cache for latest firefox
- `action=cache, query=ripgrep, system=x86_64-linux` - check cache for specific system
- `action=cache, query=nodejs, version=20.0.0` - check cache for specific version
- `action=cache, query=hello, system=aarch64-darwin` - check macOS ARM cache

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

## NixHub source (search.devbox.sh - package metadata)

**Search tests**:
- `action=search, source=nixhub, query=python, limit=5` - popular package
- `action=search, source=nixhub, query=nodejs, limit=5` - another popular package
- `action=search, source=nixhub, query=ripgrep, limit=5` - CLI tool
- `action=search, source=nixhub, query=firefox, limit=5` - GUI application
- `action=search, source=nixhub, query=rust, limit=10` - programming language
- `action=search, source=nixhub, query=xyznonexistent12345, limit=5` (should return "No packages found on NixHub")

**Info tests** (get rich package metadata):
- `action=info, source=nixhub, query=ripgrep` - should show license, homepage, programs, flake ref, store paths
- `action=info, source=nixhub, query=python` - popular package with metadata
- `action=info, source=nixhub, query=nodejs` - another metadata test
- `action=info, source=nixhub, query=hello` - simple package
- `action=info, source=nixhub, query=git` - tool with programs
- `action=info, source=nixhub, query=nonexistent-package-xyz` (should return NOT_FOUND)

**Edge cases**:
- `action=search, source=nixhub, query=go, limit=1` - minimum limit, short query
- `action=search, source=nixhub, query=rust, limit=100` - maximum limit
- `action=stats, source=nixhub` (should return "Stats not available for nixhub")

**Output verification**:
- Info should show: Package name, Version, Summary/Description
- Info should show (when available): License, Homepage, Programs list
- Info should show (when available): Flake Reference, Store Paths per system
- All platforms should be listed when available

## Cache action (binary cache status - cache.nixos.org)

**Basic cache tests**:
- `action=cache, query=hello` - simple package, likely cached
- `action=cache, query=ripgrep` - CLI tool, should be cached
- `action=cache, query=firefox` - large package, check cache status
- `action=cache, query=python` - popular package
- `action=cache, query=nodejs` - another common package

**Version-specific tests**:
- `action=cache, query=hello, version=latest` - explicit latest version
- `action=cache, query=python, version=3.12.0` - specific version (may or may not exist)
- `action=cache, query=nodejs, version=20.0.0` - specific nodejs version

**System-specific tests**:
- `action=cache, query=hello, system=x86_64-linux` - Linux x86_64
- `action=cache, query=hello, system=aarch64-linux` - Linux ARM64
- `action=cache, query=hello, system=x86_64-darwin` - macOS x86_64
- `action=cache, query=hello, system=aarch64-darwin` - macOS ARM64
- `action=cache, query=hello, system=invalid-system` (should return NOT_FOUND for system)

**Combined tests**:
- `action=cache, query=ripgrep, version=latest, system=x86_64-linux` - all parameters
- `action=cache, query=git, system=aarch64-darwin` - specific system

**Error handling**:
- `action=cache, query=` (should return "Package name required for cache action")
- `action=cache, query=nonexistent-package-xyz-123` (should return NOT_FOUND)
- `action=cache, query=invalid<>package` (should handle gracefully)

**Output verification**:
- Should show: "Binary Cache Status: {package}@{version}"
- Should show per system: System name, Store path, Cache status (CACHED/NOT CACHED)
- When cached, should show: Download size, Unpacked size, Compression method
- Should handle multiple systems when no specific system requested

## Enhanced nix_versions output

**Metadata tests** (verify rich metadata in output):
- `package=ripgrep, limit=3` - should show License, Homepage, Programs
- `package=python, limit=3` - should show metadata when available
- `package=nodejs, limit=3` - another metadata test
- `package=git, limit=3` - tool with multiple programs
- `package=hello, limit=3` - simple package

**Platform summary tests**:
- `package=hello, limit=1` - should show "Platforms: Linux and macOS" or similar summary
- `package=ripgrep, limit=1` - verify platform display

**Output verification**:
- Package header should include: Package name, License (if available), Homepage (if available)
- Package header should include: Programs list (if available), Total versions count
- Each version should show: Version number, Updated date, Platform summary
- Each version should show: Nixpkgs commit hash, Attribute path

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
- `action=stats, source=nixhub` (nixhub doesn't support stats)
- `action=options, source=nixos, query=test` (nixos doesn't support options browsing)
- `action=options, source=wiki, query=test` (wiki doesn't support options browsing)
- `action=options, source=nix-dev, query=test` (nix-dev doesn't support options browsing)
- `action=options, source=nixhub, query=test` (nixhub doesn't support options browsing)
- `action=info, source=noogle, query=` (empty query - should error)
- `action=search, source=noogle, query=` (empty query - should error)
- `action=search, source=nixhub, query=` (empty query - should error)
- `action=info, source=nixhub, query=` (empty query - should error)
- `action=cache, query=` (empty query - should error "Package name required")
- `action=cache, query=nonexistent-xyz-123` (should return NOT_FOUND)
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
- NixHub search should show package names, versions, summaries, and update dates
- NixHub info should show package name, version, license, homepage, programs, flake ref, store paths
- Cache status should show system name, store path, cache status, download/unpacked size
- nix_versions should show package metadata (license, homepage, programs) plus version history
- Error messages should be clear and actionable

Summarize results in a table showing pass/fail status for each test.
