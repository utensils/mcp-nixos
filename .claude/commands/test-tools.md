---
allowed-tools: mcp__nixos__nix, mcp__nixos__nix_versions, Task
description: Test MCP NixOS Tools (project)
---

# Test MCP NixOS Tools

**CRITICAL INSTRUCTIONS:**
1. You MUST dispatch ALL test groups below to subagents running IN PARALLEL
2. Each subagent MUST run EVERY test in its assigned group - no skipping
3. After ALL subagents complete, compile a SINGLE summary table with pass/fail for EVERY test
4. Do NOT stop early - all 8 test groups must be executed

## Dispatch Strategy

Launch these 8 subagents IN PARALLEL (single message with multiple Task tool calls):

---

### Group 1: Core NixOS Source Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for the core NixOS source. Run EVERY test below and record pass/fail:

SEARCH:
- action=search, source=nixos, type=packages, query=firefox
- action=search, source=nixos, type=options, query=nginx
- action=search, source=nixos, type=programs, query=vim, limit=3
- action=search, source=nixos, channel=stable, query=firefox, limit=3
- action=search, source=nixos, query=xyznonexistent12345 (expect "No packages found")

INFO:
- action=info, source=nixos, type=package, query=firefox
- action=info, source=nixos, type=option, query=services.nginx.enable
- action=info, source=nixos, query=nonexistentpkg123 (expect NOT_FOUND)

STATS:
- action=stats, source=nixos

CHANNELS:
- action=channels

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 2: Home Manager & Darwin Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for Home Manager and Darwin sources. Run EVERY test below:

HOME-MANAGER SEARCH:
- action=search, source=home-manager, query=git

HOME-MANAGER INFO:
- action=info, source=home-manager, query=programs.git.enable

HOME-MANAGER STATS:
- action=stats, source=home-manager

HOME-MANAGER OPTIONS:
- action=options, source=home-manager, query=programs.git
- action=options, source=home-manager (no query - list all categories)

DARWIN SEARCH:
- action=search, source=darwin, query=dock

DARWIN INFO:
- action=info, source=darwin, query=system.defaults.dock.autohide

DARWIN STATS:
- action=stats, source=darwin

DARWIN OPTIONS:
- action=options, source=darwin, query=system

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 3: Flakes & FlakeHub Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for Flakes and FlakeHub sources. Run EVERY test below:

FLAKES SEARCH:
- action=search, source=flakes, query=atuin

FLAKES STATS:
- action=stats, source=flakes

FLAKES INFO (expect error):
- action=info, source=flakes, query=test (expect "flakes don't support info")

FLAKEHUB SEARCH:
- action=search, source=flakehub, query=nixpkgs

FLAKEHUB INFO:
- action=info, source=flakehub, query=NixOS/nixpkgs

FLAKEHUB STATS:
- action=stats, source=flakehub

FLAKE-INPUTS (requires nix installed):
- action=flake-inputs, type=list
- action=flake-inputs, type=ls, query=nixpkgs
- action=flake-inputs, type=ls, query=nixpkgs:pkgs/by-name
- action=flake-inputs, type=read, query=nixpkgs:flake.nix
- action=flake-inputs, type=read, query=flake-parts:flake.nix, limit=50
- action=flake-inputs, type=ls (missing query - expect error)
- action=flake-inputs, type=read, query=nixpkgs (missing file path - expect error)
- action=flake-inputs, type=ls, query=nonexistent-input (expect NOT_FOUND)

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 4: Nixvim & Wiki Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for Nixvim and Wiki sources. Run EVERY test below:

NIXVIM SEARCH:
- action=search, source=nixvim, query=telescope

NIXVIM INFO:
- action=info, source=nixvim, query=plugins.telescope.enable

NIXVIM STATS:
- action=stats, source=nixvim

NIXVIM OPTIONS:
- action=options, source=nixvim, query=plugins

WIKI SEARCH:
- action=search, source=wiki, query=nvidia
- action=search, source=wiki, query=installation, limit=5
- action=search, source=wiki, query=flakes, limit=10
- action=search, source=wiki, query=home-manager, limit=5
- action=search, source=wiki, query=gaming, limit=5
- action=search, source=wiki, query=xyznonexistent12345, limit=5 (expect "No wiki articles found")
- action=search, source=wiki, query=NixOS, limit=1

WIKI INFO:
- action=info, source=wiki, query=Flakes
- action=info, source=wiki, query=Nvidia
- action=info, source=wiki, query=NixOS
- action=info, source=wiki, query=Home Manager
- action=info, source=wiki, query=NonExistentPageXYZ123 (expect NOT_FOUND)

WIKI ERRORS:
- action=stats, source=wiki (expect "Stats not available")
- action=options, source=wiki, query=test (expect error)

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 5: Noogle Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for Noogle source (noogle.dev). Run EVERY test below:

SEARCH:
- action=search, source=noogle, query=mapAttrs, limit=5
- action=search, source=noogle, query=concatStrings, limit=5
- action=search, source=noogle, query=filter, limit=10
- action=search, source=noogle, query=hasAttr, limit=5
- action=search, source=noogle, query=builtins.map, limit=5
- action=search, source=noogle, query=mkDerivation, limit=5
- action=search, source=noogle, query=xyznonexistent12345, limit=5 (expect "No Noogle functions found")
- action=search, source=noogle, query=map, limit=1
- action=search, source=noogle, query=AttrSet, limit=5

INFO:
- action=info, source=noogle, query=lib.attrsets.mapAttrs
- action=info, source=noogle, query=builtins.map
- action=info, source=noogle, query=lib.strings.concatStrings
- action=info, source=noogle, query=lib.lists.filter
- action=info, source=noogle, query=lib.trivial.id
- action=info, source=noogle, query=nonexistent.function.xyz (expect NOT_FOUND)
- action=info, source=noogle, query=builtins.mapAttrs (alias lookup)
- action=info, source=noogle, query=lib.mapAttrs (alias lookup)

STATS:
- action=stats, source=noogle

OPTIONS:
- action=options, source=noogle (list all categories)
- action=options, source=noogle, query=lib.strings
- action=options, source=noogle, query=lib.attrsets
- action=options, source=noogle, query=lib.lists
- action=options, source=noogle, query=builtins
- action=options, source=noogle, query=nonexistent.category (expect "No Noogle functions found")

ERRORS:
- action=info, source=noogle, query= (empty query - expect error)
- action=search, source=noogle, query= (empty query - expect error)

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 6: nix-dev & NixHub Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool for nix-dev and NixHub sources. Run EVERY test below:

NIX-DEV SEARCH:
- action=search, source=nix-dev, query=flakes, limit=5
- action=search, source=nix-dev, query=tutorial, limit=10
- action=search, source=nix-dev, query=packaging, limit=5
- action=search, source=nix-dev, query=derivation, limit=5
- action=search, source=nix-dev, query=language, limit=5
- action=search, source=nix-dev, query=best practices, limit=5
- action=search, source=nix-dev, query=xyznonexistent12345, limit=5 (expect "No nix.dev documentation found")
- action=search, source=nix-dev, query=nix, limit=1
- action=search, source=nix-dev, query=getting started, limit=20

NIX-DEV ERRORS:
- action=info, source=nix-dev, query=test (expect error suggesting search)
- action=stats, source=nix-dev (expect "Stats not available")
- action=options, source=nix-dev, query=test (expect error)

NIXHUB SEARCH:
- action=search, source=nixhub, query=python, limit=5
- action=search, source=nixhub, query=nodejs, limit=5
- action=search, source=nixhub, query=ripgrep, limit=5
- action=search, source=nixhub, query=firefox, limit=5
- action=search, source=nixhub, query=rust, limit=10
- action=search, source=nixhub, query=xyznonexistent12345, limit=5 (expect "No packages found")
- action=search, source=nixhub, query=go, limit=1

NIXHUB INFO:
- action=info, source=nixhub, query=ripgrep (expect license, homepage, programs, store paths)
- action=info, source=nixhub, query=python
- action=info, source=nixhub, query=nodejs
- action=info, source=nixhub, query=hello
- action=info, source=nixhub, query=git
- action=info, source=nixhub, query=nonexistent-package-xyz (expect NOT_FOUND)

NIXHUB ERRORS:
- action=stats, source=nixhub (expect "Stats not available")
- action=search, source=nixhub, query= (empty query - expect error)
- action=info, source=nixhub, query= (empty query - expect error)
- action=options, source=nixhub, query=test (expect error)

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 7: Cache Action Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix tool cache action (binary cache status). Run EVERY test below:

BASIC:
- action=cache, query=hello
- action=cache, query=ripgrep
- action=cache, query=firefox
- action=cache, query=python
- action=cache, query=nodejs

VERSION-SPECIFIC:
- action=cache, query=hello, version=latest
- action=cache, query=python, version=3.12.0
- action=cache, query=nodejs, version=20.0.0

SYSTEM-SPECIFIC:
- action=cache, query=hello, system=x86_64-linux
- action=cache, query=hello, system=aarch64-linux
- action=cache, query=hello, system=x86_64-darwin
- action=cache, query=hello, system=aarch64-darwin
- action=cache, query=hello, system=invalid-system (expect NOT_FOUND)

COMBINED:
- action=cache, query=ripgrep, version=latest, system=x86_64-linux
- action=cache, query=git, system=aarch64-darwin

ERRORS:
- action=cache, query= (expect "Package name required")
- action=cache, query=nonexistent-package-xyz-123 (expect NOT_FOUND)

OUTPUT VERIFICATION:
- Verify cached packages show: Store path, Status (CACHED), Download size, Unpacked size, Compression

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

### Group 8: nix_versions Tool Tests
**Subagent prompt:**
```
Test the mcp__nixos__nix_versions tool. Run EVERY test below:

BASIC:
- package=python, limit=3
- package=nodejs, limit=3
- package=ripgrep, limit=3
- package=git, limit=3
- package=hello, limit=3

SPECIFIC VERSION:
- package=nodejs, version=20.0.0
- package=python, version=3.12.0

NOT FOUND:
- package=nonexistent-xyz-123 (expect NOT_FOUND)

PLATFORM SUMMARY:
- package=hello, limit=1 (verify shows "Platforms: Linux and macOS" or similar)
- package=ripgrep, limit=1

OUTPUT VERIFICATION:
- Verify output includes: Package name, License (if available), Homepage (if available)
- Verify output includes: Programs list (if available), Total versions count
- Verify each version shows: Version number, Updated date, Platform summary, Commit hash

Return a markdown table with Test | Expected | Actual | Status (PASS/FAIL) for each test.
```

---

## Subagent Output Format (REQUIRED)

Each subagent MUST return results in this EXACT format:

```markdown
## [Group Name] Test Results

### Summary
- Total Tests: X
- Passed: X
- Failed: X

### Detailed Results

| # | Test | Expected | Actual | Status |
|---|------|----------|--------|--------|
| 1 | `action=search, source=X, query=Y` | Results found | Found N results | PASS |
| 2 | `action=info, source=X, query=Y` | Package info | Package: name... | PASS |
| 3 | `action=X, query=nonexistent` | NOT_FOUND error | Error (NOT_FOUND) | PASS |
| 4 | `action=X, source=invalid` | Error message | Unexpected result | FAIL |

### Failed Tests Detail (if any)
- Test #4: Expected "Error message" but got "Unexpected result"
```

---

## Final Summary Requirements

After ALL 8 subagents complete, compile a FINAL SUMMARY in this EXACT format:

```markdown
# MCP NixOS Tools Test Report

## Test Execution Summary

| Group | Total | Passed | Failed | Pass Rate |
|-------|-------|--------|--------|-----------|
| 1. Core NixOS | X | X | X | X% |
| 2. Home Manager & Darwin | X | X | X | X% |
| 3. Flakes & FlakeHub | X | X | X | X% |
| 4. Nixvim & Wiki | X | X | X | X% |
| 5. Noogle | X | X | X | X% |
| 6. nix-dev & NixHub | X | X | X | X% |
| 7. Cache Action | X | X | X | X% |
| 8. nix_versions | X | X | X | X% |
| **TOTAL** | **X** | **X** | **X** | **X%** |

## Failed Tests (if any)

| Group | Test | Expected | Actual |
|-------|------|----------|--------|
| Group N | `test description` | expected result | actual result |

## Issues Discovered (if any)

1. **Issue Title**: Description of the bug or unexpected behavior
   - Affected tests: list tests
   - Severity: Critical/High/Medium/Low

## Recommendations (if any)

- List any suggested fixes or improvements
```

---

## Execution Checklist

Before completing, verify:
- [ ] All 8 subagents were launched in parallel
- [ ] Each subagent ran ALL tests in its group
- [ ] Each subagent returned a properly formatted results table
- [ ] Final summary includes counts from ALL 8 groups
- [ ] All failed tests are documented with expected vs actual

**DO NOT SKIP ANY TESTS. ALL 8 GROUPS MUST BE EXECUTED.**
