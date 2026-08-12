# Changelog

## [3.0.1](https://github.com/utensils/mcp-nixos/compare/v3.0.0...v3.0.1) (2026-08-12)


### Bug Fixes

* **channels:** stop memoizing the stale channel fallback ([#211](https://github.com/utensils/mcp-nixos/issues/211)) ([effeccf](https://github.com/utensils/mcp-nixos/commit/effeccf4efb1ad850ce8308456f0877d9c5f3d39))
* **ci:** build the distribution with --no-isolation ([#208](https://github.com/utensils/mcp-nixos/issues/208)) ([cd82f7d](https://github.com/utensils/mcp-nixos/commit/cd82f7debfc1d35ecdd18886ff589f22b3ab144c))
* **search:** align ES query semantics with search.nixos.org frontend ([#206](https://github.com/utensils/mcp-nixos/issues/206)) ([548578c](https://github.com/utensils/mcp-nixos/commit/548578c2f6c209d32c85b3823a6f44bf054ebf8c))
* **search:** restore exact-match ranking and correct result counts ([#209](https://github.com/utensils/mcp-nixos/issues/209)) ([a786fa8](https://github.com/utensils/mcp-nixos/commit/a786fa8c575fc130fa0e0ec39d9ee5592538df4f))

## [3.0.0](https://github.com/utensils/mcp-nixos/compare/v2.4.3...v3.0.0) (2026-08-04)


### Breaking Changes

* **flake:** Intel macOS (`x86_64-darwin`) flake outputs have been removed because a broken transitive nixpkgs dependency prevented FlakeHub from evaluating and publishing the flake. Apple Silicon macOS (`aarch64-darwin`) and both Linux systems remain supported. ([#177](https://github.com/utensils/mcp-nixos/issues/177)) ([73bdcbb](https://github.com/utensils/mcp-nixos/commit/73bdcbb3884e2187955e0a313135232170210ff9))


### Features

* add NVF as an options source ([#189](https://github.com/utensils/mcp-nixos/issues/189)) ([b59cad3](https://github.com/utensils/mcp-nixos/commit/b59cad33a9eea1c1daeac3d18dccd132530c1511))
* rank option search and cache HTML catalogues ([#192](https://github.com/utensils/mcp-nixos/issues/192)) ([7b21991](https://github.com/utensils/mcp-nixos/commit/7b219918636b8bcb475d16c6ff0239d64c9b69dc))


### Bug Fixes

* avoid incompatible FastMCP downgrade ([#199](https://github.com/utensils/mcp-nixos/issues/199)) ([939c81d](https://github.com/utensils/mcp-nixos/commit/939c81dd5442075a6a0bb584161398a4a3c9d3bb))
* **caches:** discover channels dynamically and pick latest generation ([#159](https://github.com/utensils/mcp-nixos/issues/159)) ([b6e7b25](https://github.com/utensils/mcp-nixos/commit/b6e7b25d05a90b5735363794346d8d208a69aa44))
* **ci:** retry website verification errors ([#194](https://github.com/utensils/mcp-nixos/issues/194)) ([de85ae4](https://github.com/utensils/mcp-nixos/commit/de85ae4cf8817709866fe91fef58774ef439d0a8))
* **nixvim:** load options from current NuschtOS chunks ([#173](https://github.com/utensils/mcp-nixos/issues/173)) ([d1862f4](https://github.com/utensils/mcp-nixos/commit/d1862f4391bf0188364a32cbb29c782b7272a599))
* **website:** prevent mobile overlap and refresh errors ([#193](https://github.com/utensils/mcp-nixos/issues/193)) ([3d48839](https://github.com/utensils/mcp-nixos/commit/3d48839f1aca0bab513dabec9f6e1607e0e32fcd))


### Continuous Integration

* adopt Release Please automation ([#200](https://github.com/utensils/mcp-nixos/issues/200)) ([5d85c2b](https://github.com/utensils/mcp-nixos/commit/5d85c2b3924740d622e4729ec5889f4763c3d80a))

## 2.4.3 - LLM Discoverability

### Overview

MCP-NixOS v2.4.3 makes the server measurably easier for LLMs to discover and use correctly. When asked Nix-flavored questions, models were reaching for `Bash` (`gh api`, `curl`, `nix search`) before considering this MCP — even though it would have answered faster and with less code. This release closes that gap with a server-level instructions string, an INTENTS → CALLS recipe block, deterministic `action=info` matching, and per-channel revision metadata. No breaking changes.

### Changes in v2.4.3

#### ✨ Added

- **Server-level `instructions`** (#146, #147): The FastMCP server now ships an `instructions` string that is surfaced to clients via the MCP `InitializeResult`. Hosts render it alongside tool schemas, priming the model on when to reach for this server vs. Bash / web search / scraping `search.nixos.org`. Includes intent triggers (mentions of package names, attribute paths, NixOS / home-manager / darwin options, channel names, flake inputs, `/nix/store/` paths) and a JSON-shaped recipe block.
- **INTENTS → CALLS recipe in the `nix` tool docstring** (#147): Real user phrasings ("is package X in channel Y?", "search NixOS options for X", "does X have a binary cache?") mapped to exact JSON call shapes. Cross-references `nix_versions` for history queries.
- **Per-channel nixpkgs HEAD commit in `action=channels`** (#147): When the commit is embedded in the ES index name, output labels it `Revision (indexed): <sha>` (safe to compare against `nix_versions`). Otherwise a best-effort GitHub API fetch labels it `Branch HEAD: <sha> (upstream; may be ahead of indexed data)`. Cached per branch with a 10-minute TTL so long-running servers don't return stale revisions.

#### 🔧 Fixed

- **Silent fuzzy match in `action=info` for packages** (#146, #147): Previously `{"action": "info", "query": "firefox"}` could arbitrarily return `firefox-esr` because `term: pname=firefox` matches three packages (firefox, firefox-esr, firefox-mobile) and `size:1` picked one non-deterministically. Match now prioritises exact attribute path, then exact pname; when multiple attrs share a pname, prefers the canonical entry (attr == pname) and explicitly flags the disambiguation in the response with a copy-pasteable JSON retry hint. Non-canonical tie-breaks sort by attribute name so repeated calls are deterministic.
- **Disambiguation hint emits a copy-pasteable JSON object** (#147): The pname-collision retry hint previously used a `action=info, query='X'` pseudo-call shape that did not match the JSON-object form models actually send.

#### 🛠️ Internal

- GitHub API call now sets a `User-Agent: mcp-nixos/<version>` header for traceability and rate-limit diagnostics.
- Channel branch revision lookups defensively handle non-JSON 200 responses and fall back to the stale cached value rather than bubbling the error up to `action=channels`.

#### 🧪 Tests

- 12 new unit tests covering attr-first match priority, pname ambiguity signaling and deterministic tie-break, single-pname-hit cleanliness, indexed vs. branch-HEAD revision labeling, TTL refresh and cache-hit paths, JSON-decode failure fallback, server instructions presence, and JSON call-shape consistency. Total tests: 348 (was 336).

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.4.3

# Install with uv
uv pip install mcp-nixos==2.4.3

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.4.3

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.4.3
```

### Migration Notes

Drop-in replacement for v2.4.2. No configuration or API changes. The biggest user-visible behavior change is that `action=info` for an ambiguous pname (e.g. `firefox`) now returns the canonical attribute deterministically instead of an arbitrary one — if you were relying on the old behavior, pass an explicit attribute path.

### Contributors

- James Brink (@jamesbrink) — design, implementation, tests
- Codex / Copilot / CodeRabbit — automated peer reviews on #147

---

## 2.4.2 - Dotenv Startup Crash Fix

### Overview

MCP-NixOS v2.4.2 fixes a startup crash when the server is launched from a working directory containing a non-UTF-8 `.env` file (e.g. git-crypt ciphertext, sops-encrypted dotenv, or any binary blob). Previously, `fastmcp`'s top-level `Settings()` construction ran python-dotenv on `.env` in the process CWD at import time, and a non-UTF-8 byte anywhere in that file took the whole server down with a `UnicodeDecodeError` — before the MCP stdio handshake ever ran. Clients (Claude Code, opencode, Roo, Pi, etc.) just saw mcp-nixos fail to initialise.

### Changes in v2.4.2

#### 🔧 Bug Fixes

- **Survive non-UTF-8 `.env` in CWD** (#144, #145): `mcp_nixos/__init__.py` now defaults `FASTMCP_ENV_FILE` to `os.devnull` via `os.environ.setdefault`, before any submodule imports fastmcp. mcp-nixos does not read any values from fastmcp's `.env` lookup, so pointing fastmcp at a known-empty path sidesteps the crash without behavior loss. Users who legitimately need a fastmcp dotenv can still set `FASTMCP_ENV_FILE` explicitly and it will be respected.

#### 🧪 Tests

- Added `tests/test_env_file_safety.py` — three subprocess-based regression tests that spawn fresh Python processes to exercise import-time behavior: non-UTF-8 `.env` in CWD → clean import; explicit `FASTMCP_ENV_FILE` override preserved; unset `FASTMCP_ENV_FILE` defaults to `os.devnull`.

#### 📚 Documentation

- Website migrated from Next.js + Tailwind to VitePress 1.6 with a small custom theme preserving the NixOS brand palette (#143). No behavioral change to the Python package — this only affects the mcp-nixos.io marketing site.

#### 📦 Dependencies

- No changes from previous version.

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.4.2

# Install with uv
uv pip install mcp-nixos==2.4.2

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.4.2

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.4.2
```

### Migration Notes

Drop-in replacement for v2.4.1. No configuration or API changes. If you previously worked around this bug with `FASTMCP_ENV_FILE=/dev/null` or a CWD-change wrapper, you can remove those shims — the server now ships the equivalent default.

### Contributors

- James Brink (@jamesbrink) — fix, tests
- Reporter: @versality (#144) — excellent reproducer and suggested fix path

---

## 2.4.1 - Flake Overlay Compatibility

### Overview

MCP-NixOS v2.4.1 fixes the `fastmcp3` Nix flake overlay for downstream consumers whose nixpkgs does not contain `griffelib` or `uncalled-for`. Both packages were added to nixos-unstable on 2026-03-18 and are absent from stable (`nixos-25.11`) and older unstable pins. No runtime, API, or Python-package changes — this release only affects Nix flake consumers.

### Changes in v2.4.1

#### 🔧 Bug Fixes

- **Flake overlay compatibility** (#135, #136): `overlays.fastmcp3` previously referenced `pyFinal.griffelib` and `pyFinal.uncalled-for` directly, which failed with `error: attribute 'griffelib' missing` for any consumer using `inputs.nixpkgs.follows = "nixpkgs"` against a nixpkgs that predates those packages. The overlay now guards both references with `or` fallbacks that `callPackage` local derivations (`nix/griffelib.nix`, `nix/uncalled-for.nix`) when the consumer's nixpkgs lacks them. Consumers on current unstable continue to use the upstream packages unchanged — the fallback path only triggers when the attribute is missing.

#### 📦 Dependencies

- No changes from previous version.

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.4.1

# Install with uv
uv pip install mcp-nixos==2.4.1

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.4.1

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.4.1
```

### Migration Notes

Drop-in replacement for v2.4.0. If you are a Nix flake consumer who pinned `v2.4.0` with `inputs.nixpkgs.follows` against a stable or older nixpkgs, bump to `v2.4.1` to unblock the build. PyPI and Docker consumers see no behavioral change.

### Contributors

- James Brink (@utensils) — overlay fix
- Reporter: @rolfst (#135) — flagged the downstream breakage

---

## 2.4.0 - FastMCP 3.x Upgrade

### Overview

MCP-NixOS v2.4.0 upgrades the framework dependency to FastMCP 3.x (`fastmcp>=3.2.0`). No user-facing behavior changes — this is a dependency bump needed to keep the project buildable alongside downstream nixpkgs work that moves consumers (e.g. `ha-mcp`) onto FastMCP 3 (tracked in [NixOS/nixpkgs#511658](https://github.com/NixOS/nixpkgs/pull/511658)).

### Changes in v2.4.0

#### 🚀 Framework

- **FastMCP 3.x upgrade** (#127, #130): Bumped `fastmcp>=2.11.0` → `fastmcp>=3.2.0` in `pyproject.toml`. The server's API surface (constructor, `@mcp.tool()`, `mcp.run()` with stdio/http kwargs) is unchanged; both transports continue to work identically.
- **Nix flake fastmcp 3 override**: The flake overlay temporarily overrides `python3Packages.fastmcp` to build PrefectHQ/fastmcp v3.2.4 directly, mirroring pending nixpkgs PR [#510339](https://github.com/NixOS/nixpkgs/pull/510339). The override lives in `overlays.fastmcp3` and is composed into `overlays.default`, so downstream consumers applying `mcp-nixos.overlays.default` get the upgraded fastmcp automatically. Removable once upstream nixpkgs catches up.
- **aarch64-linux docker build** (#131): Dropped `pydocket` from the inherited runtime deps in the fastmcp override — matches the upstream PR which moves it to `optional-dependencies.tasks`. Without this, `pydocket` pulled in `lupa`, whose bundled `libluajit.a` fails to link on aarch64-linux. Multi-arch Docker images now build cleanly on both `amd64` and `arm64` again.
- **Test shim for fastmcp 2.x / 3.x compat**: `tests/test_tools.py`, `tests/test_integration.py`, and `tests/test_flake_inputs.py` now use `getattr(tool, "fn", tool)` instead of `tool.fn`. FastMCP 2.x and the PyPI wheel of 3.2.4 wrap `@mcp.tool()` as `FunctionTool` (has `.fn`), while the nix-built 3.2.4 returns a plain async function. Same shim the `.pi` wrapper already uses.

#### ⚠️ Breaking (for package consumers)

- If you had `fastmcp==2.x` pinned elsewhere in your environment alongside `mcp-nixos`, pip/uv will now refuse to resolve. Upgrade fastmcp to >=3.2.0 or remove the pin.

#### 🧹 Docs

- `CLAUDE.md` updated to say "FastMCP 3.x server" and cite the actual pin (`fastmcp>=3.2.0`).

#### 🪲 Known non-issues

- The overlay keeps `py-key-value-aio` at nixpkgs' 0.3.0, which fastmcp 3.2.4 formally wants at >=0.4.4 with the `filetree` extra. This only affects the `fastmcp.server.auth.oauth_proxy` import path (missing `aiofile`) — not used by mcp-nixos. Tracked in #129; resolves naturally when nixpkgs PR #510339 lands.

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.4.0

# Install with uv
uv pip install mcp-nixos==2.4.0

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.4.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.4.0
```

### Migration Notes

No runtime or configuration changes. The only practical impact is the transitive dependency upgrade — if anything else in your environment holds fastmcp to 2.x, relax that pin.

### Contributors

- James Brink (@utensils) — FastMCP 3 upgrade, flake overlay, release
- Reporter: @JamieMagee (#127) — flagged the downstream nixpkgs upgrade blocker

---

## 2.3.2 - Local Agent Tool Descriptions

### Overview

MCP-NixOS v2.3.2 improves the `nix` tool's descriptions and error messages so smaller local models (qwen3.6, qwen3-coder via Pi, etc.) can reliably map intent to the right `action`/`type` combo. Also ships a project-local Pi Coding Agent extension.

### Changes in v2.3.2

#### 🔧 Bug Fixes

- **Rename `action=options` → `action=browse`** (#125): The old name suggested "the options action" but actually meant "browse an option hierarchy by prefix" and rejected `source=nixos` outright. Small models reasonably tried it for NixOS options and hit a dead end. `action=options` is still accepted as a silent alias for backward compatibility.
- **`browse` with `source=nixos` now redirects** (#125): Instead of a generic "not for nixos" rejection, the error now contains the exact correct JSON (`{"action": "search", ..., "type": "options"}`) so a retry uses the right shape.
- **Pi wrapper fastmcp 2.x compatibility** (#128): The `.pi/extensions/mcp-nixos.ts` wrapper now unwraps FastMCP `FunctionTool` via `getattr(tool, "fn", tool)`. Previously it worked on fastmcp 3.x (plain function) but failed on fastmcp 2.x (Nix dev-shell / CI) with `TypeError: 'FunctionTool' object is not callable`.
- **Pi wrapper cancellation propagation** (#128): Aborted tool calls now short-circuit the Python-candidate retry loop instead of spawning further `uv`/`python3`/`python` processes.

#### 📚 Tool Description Improvements (#123, #125)

- **Concrete JSON examples in the `nix` docstring**: 9 copy-pasteable examples (`search`, `info`, `browse`, `channels`, `cache`, etc.) that small models can pattern-match against.
- **Replaced pipe-separated values with plain prose** in parameter and error messages (e.g. `"one of: packages, options, programs, flakes"` instead of `"packages|options|programs|flakes"`). Pipes looked like pseudo-JSON to weaker models and fed back confusingly into the next attempt.
- **Tightened every `Annotated[...]` description** to say which action uses each parameter (e.g. `version`/`system` now say "only used by action=cache").
- **Documented the `flake-inputs` path mode** for `source` in both the Python tool and the Pi schema.
- **Concrete examples in redirect error** — replaced `<keyword>` / `<option.path>` placeholders in the browse-nixos redirect with `nginx` / `services.nginx.enable` so a literal copy is runnable.

#### 🧩 Pi Coding Agent

- **Project-local `.pi/extensions/mcp-nixos.ts`**: Auto-loaded by Pi when run in the cloned repo. Wraps the Python tools as native Pi tools (no MCP transport overhead).
- **README "Option 5: Pi Coding Agent"**: Documents both the `pi-mcp-adapter` path (recommended, speaks MCP) and the project-local extension path.
- **`.pi/package.json` + `.pi/tsconfig.json`**: Enable clean in-editor type resolution for the extension (optional — `npm install` locally if you want it; Pi itself resolves at runtime).

#### 🔧 Tooling

- **Pre-commit ruff bumped** from `v0.4.10` to `v0.14.10` to match the ruff version shipped by the Nix dev-shell / CI, ending a formatter ping-pong on assert layouts.

#### 📦 Dependencies

- No runtime dependency changes.

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.3.2

# Install with uv
uv pip install mcp-nixos==2.3.2

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.3.2

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.3.2
```

### Migration Notes

Drop-in replacement with no user-facing breaking changes. The renamed `action=browse` is additive — existing callers using `action=options` continue to work via the alias. Tool description changes are consumed by LLMs, not user code.

### Contributors

- James Brink (@utensils) — Tool description overhaul, Pi extension, release
- Reporters: @juk0de (#123), @Smona (#125)

---

## 2.3.1 - Dotted Package Name Search Fix

### Overview

MCP-NixOS v2.3.1 fixes package search and info lookups for dotted/namespaced attribute paths (e.g., `kdePackages.qt6ct`, `python314Packages.matplotlib`). Previously, models were unable to find packages by their exact namespaced names.

### Changes in v2.3.1

#### 🔧 Bug Fixes

- **Dotted Package Name Search** (#118): Search now queries `package_attr_name` in Elasticsearch and extracts the last component of dotted names for `package_pname` matching. Searching for `kdePackages.qt6ct` now correctly finds the `qt6ct` package.
- **Info Lookup by Attribute Path** (#118): The `info` action falls back to `package_attr_name` when the `pname` lookup returns no results, so `nix(action="info", query="kdePackages.qt6ct")` now works.
- **Attribute Path in Output** (#118): Search results and info output now display the full attribute path (e.g., `kdePackages.qt6ct`) instead of just the pname (`qt6ct`), helping users identify which package set a package belongs to.

#### 🧹 Housekeeping

- **CLAUDE.md / AGENTS.md**: Fixed circular symlinks. `CLAUDE.md` is now the source of truth, `AGENTS.md` symlinks to it.

#### 📦 Dependencies

- No changes from previous version

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.3.1

# Install with uv
uv pip install mcp-nixos==2.3.1

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.3.1

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.3.1
```

### Migration Notes

Drop-in replacement with no user-facing breaking changes. Search results now include attribute paths in the output, which provides more information but doesn't change the format in a breaking way.

### Contributors

- James Brink (@utensils) - Dotted package name fix

---

## 2.3.0 - HTTP Transport & Modular Architecture

### Overview

MCP-NixOS v2.3.0 adds HTTP transport support for Remote MCP, binary cache status checking, NixHub as a rich metadata source, and restructures the codebase into a modular architecture. This release includes two new user-facing features with no breaking changes.

### Changes in v2.3.0

#### 🚀 New Features

- **HTTP Transport Support** (#104): Run the server over HTTP in addition to STDIO
  - `MCP_NIXOS_TRANSPORT=http` enables HTTP mode (default endpoint: `http://127.0.0.1:8000/mcp`)
  - Configurable host, port, and path via `MCP_NIXOS_HOST`, `MCP_NIXOS_PORT`, `MCP_NIXOS_PATH`
  - Stateless mode via `MCP_NIXOS_STATELESS_HTTP=1` for scalable deployments
  - Works with any MCP client that supports HTTP transport

- **Binary Cache Status** (#92): Check if packages have pre-built binaries on cache.nixos.org
  - `nix(action="cache", query="hello")` — check cache availability
  - Shows download size, unpacked size, compression method, and per-platform availability
  - Resolves package versions to store paths via NixHub API

- **NixHub Package Metadata** (#92): Rich package information from NixHub.io
  - `nix(action="search", source="nixhub", query="nodejs")` — search with metadata
  - `nix(action="info", source="nixhub", query="python")` — license, homepage, store paths
  - Enhanced `nix_versions` with richer version data

#### 🏗️ Architecture

- **Modular Codebase Restructure** (#94): Split monolithic `server.py` into focused modules
  - `mcp_nixos/sources/` — one module per data source (nixos, home_manager, darwin, flakes, etc.)
  - `mcp_nixos/caches.py` — cache implementations
  - `mcp_nixos/config.py` — configuration constants
  - `mcp_nixos/utils.py` — shared utility functions
  - `mcp_nixos/server.py` — MCP tools and routing only

#### 🔧 Bug Fixes

- **serverInfo Version** (#109): Report package version correctly in MCP serverInfo response
- **pytest Config** (#105): Use list types for pytest ini_options
- **Channel Validation**: Corrected patch paths for channel validation tests
- **CI**: Allow dependabot PRs in Claude Code Review workflow

#### 📦 Dependencies & CI

- Bumped `aws-actions/configure-aws-credentials` from 5 to 6
- Website dependency updates: shiki, autoprefixer, @types/react
- Added `@pytest.mark.unit` decorators to test suite

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.3.0

# Install with uv
uv pip install mcp-nixos==2.3.0

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.3.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.3.0
```

### Migration Notes

This is a drop-in replacement for v2.2.0. All existing queries work unchanged. The new HTTP transport and binary cache/NixHub features are entirely additive.

### Contributors

- James Brink (@utensils) — Binary cache, NixHub, modular architecture, serverInfo fix
- ReStranger (@ReStranger) — HTTP transport support (#104)
- David Dudson (@DavidDudson) — pytest config fix (#105)

---

## 2.2.0 - Documentation Sources & Flake Inputs

### Overview

MCP-NixOS v2.2.0 adds three new documentation sources (NixOS Wiki, nix.dev, and Noogle) and a new `flake-inputs` action to explore local Nix store dependencies. This release significantly expands the knowledge accessible to AI assistants working with Nix.

### Changes in v2.2.0

#### 🚀 New Documentation Sources

Three new sources have been added to the `nix` tool:

- **NixOS Wiki** (`source="wiki"`): Search and retrieve articles from wiki.nixos.org via MediaWiki API
  - `action=search`: Find wiki articles by keyword
  - `action=info`: Get full article content

- **nix.dev** (`source="nix-dev"`): Search official Nix tutorials and guides
  - `action=search`: Find documentation via Sphinx search index
  - Covers tutorials, guides, and best practices

- **Noogle** (`source="noogle"`): Search 2,000+ Nix built-in functions from noogle.dev
  - `action=search`: Find functions by name or description
  - `action=info`: Get function details with type signatures
  - `action=stats`: View function statistics
  - `action=options`: Browse functions by category (e.g., `lib.strings`)

#### 🔍 Flake Inputs Exploration

New `flake-inputs` action to explore local Nix store dependencies (requires Nix):

- `action=flake-inputs type=list`: List all flake inputs with their store paths
- `action=flake-inputs type=ls query="nixpkgs:lib"`: Browse directories in inputs
- `action=flake-inputs type=read query="nixpkgs:flake.nix"`: Read files from inputs

Features:
- Async subprocess execution with timeout handling
- Security validation to keep paths within `/nix/store/`
- Binary file detection and file size limits (up to 2000 lines)
- Nested input flattening (e.g., `flake-parts.nixpkgs-lib`)

#### 🔧 Improvements & Bug Fixes

- **CI/CD**: Updated GitHub Actions (checkout v6, upload/download-artifact v6/v7, setup-node v6)
- **Documentation**: Added declarative Nix installation examples
- **Docker**: Fixed tag generation to match flake version output
- **Website**: Synced feature descriptions and updated dependencies

#### 📦 Dependencies

- No Python dependency changes
- Website dependencies updated (sharp, @types/node, eslint plugins)

### Usage Examples

```bash
# Search NixOS Wiki
nix action=search source=wiki query="nvidia drivers"

# Get wiki article
nix action=info source=wiki query="Flakes"

# Search nix.dev tutorials
nix action=search source=nix-dev query="first steps"

# Search Nix functions
nix action=search source=noogle query="map"

# Get function info with type signature
nix action=info source=noogle query="lib.strings.concatMapStrings"

# List flake inputs (requires Nix)
nix action=flake-inputs type=list

# Browse input directory
nix action=flake-inputs type=ls query="nixpkgs:lib/strings.nix"

# Read file from input
nix action=flake-inputs type=read query="nixpkgs:flake.nix"
```

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.2.0

# Install with uv
uv pip install mcp-nixos==2.2.0

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.2.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.2.0
```

### Migration Notes

This is a drop-in replacement for v2.1.1. All new features are additive with no breaking changes. Existing queries continue to work unchanged.

### Contributors

- James Brink (@utensils) - Documentation sources and flake-inputs implementation

---

## 2.1.1 - Stable Python Compatibility

### Overview

MCP-NixOS v2.1.1 fixes the Nix flake by using the stable python in nixpkgs.

### Changes in v2.1.1

#### 🔧 Improvements & Bug Fixes

- **Stable Python Compatibility**: MCP-NixOS v2.1.1 fixes the Nix flake by using the stable python in nixpkgs.

### Contributors

- Malix - Alix Brunet (@Malix-Labs)

---

## 2.1.0 - Pure Nix Flake

### Overview

MCP-NixOS v2.1.0 converts to a pure Nix flake build system and adds FlakeHub integration for easier installation. This release fixes build compatibility with nixpkgs-unstable and provides a proper Nix overlay for seamless integration into NixOS and Home Manager configurations.

### Changes in v2.1.0

#### 🚀 Pure Nix Flake Build System

- **Complete Flake Rewrite**: Migrated from hybrid venv/pip approach to pure Nix
- **Python 3.14 Support**: Now builds with Python 3.14 from nixpkgs
- **Proper Overlay**: Exposes `overlays.default` for easy integration into NixOS/Home Manager
- **flake-parts**: Refactored to use flake-parts for cleaner multi-system support
- **Build Fix**: Added overlay to handle fastmcp/mcp version constraints in nixpkgs-unstable

#### 🌐 FlakeHub Integration

- **FlakeHub Publishing**: Package now available on FlakeHub for simplified installation
- **Semantic Versioning**: Proper versioning support via FlakeHub

#### 📦 Installation

**Via FlakeHub:**
```nix
{
  inputs.mcp-nixos.url = "https://flakehub.com/f/utensils/mcp-nixos/*.tar.gz";
}
```

**Via GitHub:**
```nix
{
  inputs.mcp-nixos.url = "github:utensils/mcp-nixos";

  # Use the overlay
  nixpkgs.overlays = [ mcp-nixos.overlays.default ];

  # Then add to packages
  environment.systemPackages = [ pkgs.mcp-nixos ];  # NixOS
  home.packages = [ pkgs.mcp-nixos ];               # Home Manager
}
```

#### 🔧 Bug Fixes

- **nixpkgs-unstable Compatibility**: Fixed build failure caused by fastmcp requiring `mcp<1.17.0` while nixpkgs has `mcp>=1.25.0`

#### 📦 Dependencies

- No Python dependency changes
- Build system now uses pure nixpkgs packages

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.1.0

# Install with uv
uv pip install mcp-nixos==2.1.0

# Run directly with nix
nix run github:utensils/mcp-nixos
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.1.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.1.0
```

### Migration Notes

This is a drop-in replacement for v2.0.0 with no user-facing changes to the MCP tools. The changes are entirely in the Nix build infrastructure. If you were experiencing build failures with v2.0.0 on nixpkgs-unstable, this release resolves that issue.

### Contributors

- James Brink (@utensils) - Nix Flake Architect

---

## 2.0.0 - The Great Consolidation

### Overview

MCP-NixOS v2.0.0 is a major release that consolidates 17 MCP tools into just 2 unified tools, reducing token overhead by 95%. This release also adds comprehensive Nixvim support with 16,600+ configuration options.

### Changes in v2.0.0

#### 🎯 Tool Consolidation (95% Token Reduction)

- **Before**: 17 individual tools consuming ~15,000 tokens
- **After**: 2 unified tools consuming ~1,400 tokens
- **Result**: 95% reduction in token overhead

New tools:
- `nix` (769 tokens) - Unified query tool for search/info/stats/options/channels
- `nix_versions` (643 tokens) - Package version history from NixHub.io

#### 🚀 Nixvim Support

Added `nixvim` as a new source for the `nix` tool:

- **16,647 options** fetched from NuschtOS search infrastructure
- Supports all actions: search, info, stats, options browsing
- Covers plugins (14,216), LSP (1,439), colorschemes (679), and more
- Credits [NuschtOS/search](https://github.com/NuschtOS/search) for the data source

#### 🔧 Improvements

- **Input Validation**: Added limit validation (1-100) for nix tool queries
- **Type Safety**: Fixed `strip_html()` type hint to accept `str | None`
- **Test Suite**: Comprehensive 114 tests (unit + integration)
- **Edge Case Coverage**: Tests for channels, programs type, empty results

#### 🧹 Cleanup

- Removed smithery integration
- Removed orphaned `website/app/docs/claude.html` (17K+ lines)
- Consolidated test files from 12 files to 3

#### 📦 Dependencies

- No dependency changes
- Maintained compatibility with FastMCP 2.x

### Installation

```bash
# Install with pip
pip install mcp-nixos==2.0.0

# Install with uv
uv pip install mcp-nixos==2.0.0

# Install with uvx
uvx mcp-nixos==2.0.0
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:2.0.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:2.0.0
```

### Migration Guide

#### ⚠️ Breaking Changes

All 17 legacy tools have been removed. You must migrate to the new unified `nix` tool:

| Old Tool | New Equivalent |
|----------|----------------|
| `nixos_search` | `nix action=search source=nixos` |
| `nixos_info` | `nix action=info source=nixos` |
| `nixos_stats` | `nix action=stats source=nixos` |
| `home_manager_search` | `nix action=search source=home-manager` |
| `home_manager_info` | `nix action=info source=home-manager` |
| `home_manager_options` | `nix action=options source=home-manager` |
| `darwin_search` | `nix action=search source=darwin` |
| `darwin_info` | `nix action=info source=darwin` |
| `darwin_options` | `nix action=options source=darwin` |
| `flakes_search` | `nix action=search source=flakes` |
| `nixos_flakes_search` | `nix action=search source=flakes` |
| `nixos_channels` | `nix action=channels` |
| `nix_versions` | `nix_versions` (unchanged) |

#### New Nixvim Queries

```bash
# Search Nixvim options
nix action=search source=nixvim query=telescope

# Get option info
nix action=info source=nixvim query=plugins.telescope.enable

# Browse plugin options
nix action=options source=nixvim query=plugins

# Get statistics
nix action=stats source=nixvim
```

### Contributors

- James Brink (@utensils) - Chief Consolidator

---

## 1.1.0 - NixOS 25.11 Stable

### Overview

MCP-NixOS v1.1.0 updates to NixOS 25.11 as the new stable channel, fixes the flakes search index, and improves CI/CD reliability with automatic retry handling for integration tests.

### Changes in v1.1.0

#### 🚀 Channel Updates

- **NixOS 25.11 Stable**: Updated stable channel to the latest NixOS 25.11 release
- **Flakes Index Fix**: Fixed flakes search which was broken due to Elasticsearch index changes (#62)
- **Dynamic Channel Discovery**: Improved channel detection to handle new NixOS releases automatically

#### 🔧 Bug Fixes

- **Flaky Test Handling**: Added pytest-rerunfailures for automatic retry of integration tests on API timeouts (#63, #64)
- **Portability Fix**: Changed `.mcp.json` to use relative paths for better cross-environment compatibility
- **Test Stability**: All integration test classes now properly marked with flaky decorators

#### 🛠️ Development Experience

- **Test Cleanup**: Removed eval test framework and renamed tests with descriptive names
- **Documentation**: Updated README with accurate statistics and refreshed badges
- **CI Reliability**: Integration tests now retry up to 3 times with 2-second delay on transient failures

#### 📦 Dependencies

- Added `pytest-rerunfailures>=15.0` for flaky test handling
- Maintained compatibility with FastMCP 2.x

### Installation

```bash
# Install with pip
pip install mcp-nixos==1.1.0

# Install with uv
uv pip install mcp-nixos==1.1.0

# Install with uvx
uvx mcp-nixos==1.1.0
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:1.1.0

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:1.1.0
```

### Migration Notes

This is a drop-in replacement for v1.0.3. The "stable" channel alias now points to NixOS 25.11 instead of 25.05. If you explicitly use version-specific channels (e.g., `channel="25.05"`), your queries will continue to work unchanged.

### Contributors

- James Brink (@utensils) - NixOS 25.11 update and CI improvements

---

## 1.0.3 - Encoding Fix

### Overview

MCP-NixOS v1.0.3 fixes encoding errors when parsing Home Manager and nix-darwin documentation, ensuring robust operation with various HTML encodings from CDN edge servers.

### Changes in v1.0.3

#### 🔧 Bug Fixes

- **HTML Encoding Support**: Fixed parsing errors with non-UTF-8 encodings (windows-1252, ISO-8859-1, UTF-8 with BOM) in documentation (#58)
- **CDN Resilience**: Enhanced robustness when fetching docs from different CDN edge nodes with varying configurations
- **Test Coverage**: Added comprehensive encoding tests for all HTML parsing functions

#### 🛠️ Development Experience

- **Release Workflow**: Improved release command documentation with clearer formatting
- **Test Suite**: Updated 26 tests to properly handle byte content in mock responses

#### 📦 Dependencies

- No changes from previous version
- Maintained compatibility with FastMCP 2.x

### Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.3

# Install with uv
uv pip install mcp-nixos==1.0.3

# Install with uvx
uvx mcp-nixos==1.0.3
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:1.0.3

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:1.0.3
```

### Migration Notes

This is a drop-in replacement for v1.0.2 with no user-facing changes. The fix resolves intermittent "unknown encoding: windows-1252" errors when fetching documentation.

### Contributors

- James Brink (@utensils) - Fixed encoding handling in HTML parser

---

## 1.0.2 - Infrastructure Improvements

### Overview

MCP-NixOS v1.0.2 is a maintenance release focused on CI/CD improvements, security fixes, and enhanced Docker support. This release adds manual workflow dispatch capabilities, GHCR package visibility automation, and improves the deployment pipeline.

### Changes in v1.0.2

#### 🚀 CI/CD Enhancements

- **Manual Workflow Dispatch**: Added ability to manually trigger Docker builds for specific tags
- **GHCR Package Visibility**: Automated setting of GitHub Container Registry packages to public visibility
- **Continuous Docker Builds**: Docker images now build automatically on main branch pushes
- **FlakeHub Publishing**: Integrated automated FlakeHub deployment workflow
- **Workflow Separation**: Split website deployment into dedicated workflow for better CI/CD organization

#### 🔧 Bug Fixes

- **Tag Validation**: Fixed regex character class in Docker tag validation
- **API Resilience**: Added fallback channels when NixOS API discovery fails (#52, #54)
- **Documentation Fixes**: Escaped quotes in usage page to fix ESLint errors
- **Security**: Patched PrismJS DOM Clobbering vulnerability

#### 🛠️ Development Experience

- **Code Review Automation**: Enhanced Claude Code Review with sticky comments
- **Agent Support**: Added MCP and Python development subagents
- **CI Optimization**: Skip CI builds on documentation-only changes
- **Improved Docker Support**: Better multi-architecture builds (amd64, arm64)

#### 📦 Dependencies

- All dependencies remain unchanged from v1.0.1
- Maintained compatibility with FastMCP 2.x

### Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.2

# Install with uv
uv pip install mcp-nixos==1.0.2

# Install with uvx
uvx mcp-nixos==1.0.2
```

### Docker Images

```bash
# Pull from Docker Hub
docker pull utensils/mcp-nixos:1.0.2

# Pull from GitHub Container Registry
docker pull ghcr.io/utensils/mcp-nixos:1.0.2
```

### Migration Notes

This is a drop-in replacement for v1.0.1 with no user-facing changes. All improvements are infrastructure and workflow related.

### Contributors

- James Brink (@utensils) - Chief Infrastructure Engineer

---

## 1.0.1 - FastMCP 2.x Migration

### Overview

MCP-NixOS v1.0.1 completes the migration to FastMCP 2.x, bringing modern async/await patterns and improved MCP protocol compliance. This release maintains all existing functionality while modernizing the codebase for better performance and maintainability.

### Changes in v1.0.1

#### 🚀 Major Updates

- **FastMCP 2.x Migration**: Migrated from MCP SDK to FastMCP 2.x for better async support
- **Async/Await Patterns**: All tools now use proper async/await patterns throughout
- **Improved Type Safety**: Enhanced type annotations with FastMCP's built-in types
- **Test Suite Overhaul**: Fixed all 334 tests to work with new async architecture
- **CI/CD Modernization**: Updated to use ruff for linting/formatting (replacing black/flake8/isort)

#### 🔧 Technical Improvements

- **Tool Definitions**: Migrated from `@server.call_tool()` to `@mcp.tool()` decorators
- **Function Extraction**: Added `get_tool_function` helper for test compatibility
- **Mock Improvements**: Enhanced mock setup for async function testing
- **Channel Resolution**: Fixed channel cache mock configurations in tests
- **Error Messages**: Removed "await" from user-facing error messages for clarity

#### 🧪 Testing Enhancements

- **Test File Consolidation**: Removed duplicate test classes from merged files
- **Async Test Support**: All tests now properly handle async/await patterns
- **Mock JSON Responses**: Fixed mock setup to return proper dictionaries instead of Mock objects
- **API Compatibility**: Updated test expectations to match current NixHub API data
- **Coverage Maintained**: All 334 tests passing with comprehensive coverage

#### 🛠️ Development Experience

- **Ruff Integration**: Consolidated linting and formatting with ruff
- **Simplified Toolchain**: Removed black, flake8, and isort in favor of ruff
- **Faster CI/CD**: Improved CI pipeline efficiency with better caching
- **Type Checking**: Enhanced mypy configuration for FastMCP compatibility

#### 📦 Dependencies

- **FastMCP**: Now using `fastmcp>=2.11.0` for modern MCP support
- **Other Dependencies**: Maintained compatibility with all existing dependencies
- **Development Tools**: Streamlined dev dependencies with ruff

### Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.1

# Install with uv
uv pip install mcp-nixos==1.0.1

# Install with uvx
uvx mcp-nixos==1.0.1
```

### Migration Notes

This is a drop-in replacement for v1.0.1 with no user-facing changes. The migration to FastMCP 2.x is entirely internal and maintains full backward compatibility.

### Technical Details

The migration involved:

1. **Async Architecture**: Converted all tool functions to async with proper await usage
2. **Import Updates**: Changed from `mcp.server.Server` to `fastmcp.FastMCP`
3. **Decorator Migration**: Updated all tool decorators to FastMCP's `@mcp.tool()` pattern
4. **Test Compatibility**: Added function extraction helpers for test suite compatibility
5. **Mock Enhancements**: Improved mock setup for async testing patterns

### Contributors

- James Brink (@utensils) - Chief Modernizer

---

## 1.0.0 - The Great Simplification

### Overview

MCP-NixOS v1.0.0 is a complete rewrite that proves less is more. We've drastically simplified the codebase while maintaining 100% functionality and adding new features. This isn't just a refactor—it's a masterclass in minimalism.

### Changes in v1.0.0

#### 🎯 The Nuclear Option

- **Complete Rewrite**: Drastically simplified the entire codebase
- **Stateless Operation**: No more cache directories filling up your disk
- **Direct API Calls**: Removed all abstraction layers—now it's just functions doing their job
- **Simplified Dependencies**: Reduced from 5 to 3 core dependencies (40% reduction)
- **Two-File Implementation**: Everything you need in just `server.py` and `__main__.py`
- **Resolves #22**: Completely eliminated pickle usage and the entire cache layer

#### 🚀 Major Improvements

- **Plain Text Output**: All responses now return human-readable plain text (no XML!)
- **NixHub Integration**: Added package version history tools
  - `nixhub_package_versions`: Get version history with nixpkgs commits
  - `nixhub_find_version`: Smart search for specific versions
- **Dynamic Channel Resolution**: Auto-discovers current stable channel
- **Enhanced Error Messages**: Suggestions when exact matches fail
- **Flake Search**: Added deduplicated flake package search
- **Better Stats**: Accurate statistics for all tools
- **Zero Configuration**: Removed all the config options you weren't using anyway
- **Faster Startup**: No cache initialization, no state management, just pure functionality
- **100% Test Coverage**: Comprehensive test suite ensures everything works as advertised

#### 💥 Breaking Changes

- **No More Caching**: All operations are now stateless (your internet better be working)
- **Environment Variables Removed**: Only `ELASTICSEARCH_URL` remains
- **No Pre-Cache Option**: The `--pre-cache` flag is gone (along with the cache itself)
- **No Interactive Shell**: The deprecated CLI has been completely removed

#### 🧹 What We Removed

- `cache/` directory - Complex caching that nobody understood
- `clients/` directory - Abstract interfaces that abstracted nothing
- `contexts/` directory - Context managers for contexts that didn't exist
- `resources/` directory - MCP resource definitions (now inline)
- `tools/` directory - Tool implementations (now in server.py)
- `utils/` directory - "Utility" functions that weren't
- 45 files of over-engineered complexity

#### 📊 The Numbers

- **Before**: Many files with layers of abstraction
- **After**: Just 2 core files that matter
- **Result**: Dramatically less code, zero reduction in functionality, more features added

### Installation

```bash
# Install with pip
pip install mcp-nixos==1.0.0

# Install with uv
uv pip install mcp-nixos==1.0.0

# Install with uvx
uvx mcp-nixos==1.0.0
```

### Migration Guide

If you're upgrading from v0.x:

1. **Remove cache-related environment variables** - They don't do anything anymore
2. **Remove `--pre-cache` from any scripts** - It's gone
3. **That's it** - Everything else just works

### Why This Matters

This release demonstrates that most "enterprise" code is just complexity for complexity's sake. By removing abstractions, caching layers, and "design patterns," we've created something that:

- Is easier to understand
- Has fewer bugs (less code = less bugs)
- Starts faster
- Uses less memory
- Is more reliable

Sometimes the best code is the code you delete.

### Contributors

- James Brink (@utensils) - Chief Code Deleter

---

## 0.5.1

### Overview

MCP-NixOS v0.5.1 is a minor release that updates the Elasticsearch index references to ensure compatibility with the latest NixOS search API. This release updates the index references from `latest-42-` to `latest-43-` to maintain functionality with the NixOS search service.

### Changes in v0.5.1

#### 🔧 Fixes & Improvements

- **Updated Elasticsearch Index References**: Fixed the Elasticsearch index references to ensure proper connectivity with the NixOS search API
- **Version Bump**: Bumped version from 0.5.0 to 0.5.1

### Installation

```bash
# Install with pip
pip install mcp-nixos==0.5.1

# Install with uv
uv pip install mcp-nixos==0.5.1

# Install with uvx
uvx mcp-nixos==0.5.1
```

### Configuration

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

### Contributors

- James Brink (@utensils)

## 0.5.0

### Overview

MCP-NixOS v0.5.0 introduces support for the NixOS 25.05 Beta channel, enhancing the flexibility and forward compatibility of the tool. This release adds the ability to search and query packages and options from the upcoming NixOS 25.05 release while maintaining backward compatibility with existing channels.

### Changes in v0.5.0

#### 🚀 Major Enhancements

- **NixOS 25.05 Beta Channel Support**: Added support for the upcoming NixOS 25.05 release
- **New "beta" Alias**: Added a "beta" alias that maps to the current beta channel (currently 25.05)
- **Comprehensive Channel Documentation**: Updated all docstrings to include information about the new beta channel
- **Enhanced Testing**: Added extensive tests to ensure proper channel functionality

#### 🛠️ Implementation Details

- **Channel Validation**: Extended channel validation to include the new 25.05 Beta channel
- **Cache Management**: Ensured cache clearing behavior works correctly with the new channel
- **Alias Handling**: Implemented proper handling of the "beta" alias similar to the "stable" alias
- **Testing**: Comprehensive test suite to verify all aspects of channel switching and alias resolution

### Technical Details

The release implements the following key improvements:

1. **25.05 Beta Channel**: Added the Elasticsearch index mapping for the upcoming NixOS 25.05 release using the index name pattern `latest-43-nixos-25.05`

2. **Beta Alias**: Implemented a "beta" alias that will always point to the current beta channel, similar to how the "stable" alias points to the current stable release

3. **Extended Documentation**: Updated all function and parameter docstrings to include the new channel options, ensuring users know about the full range of available channels

4. **Future-Proofing**: Designed the implementation to make it easy to add new channels in the future when new NixOS releases are in development

### Installation

```bash
# Install with pip
pip install mcp-nixos==0.5.0

# Install with uv
uv pip install mcp-nixos==0.5.0

# Install with uvx
uvx mcp-nixos==0.5.0
```

### Usage

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

#### Available Channels

The following channels are now available for all NixOS tools:

- `unstable` - The NixOS unstable development branch
- `25.05` - The NixOS 25.05 Beta release (upcoming)
- `beta` - Alias for the current beta channel (currently 25.05)
- `24.11` - The current stable NixOS release
- `stable` - Alias for the current stable release (currently 24.11)

Example usage:

```python
# Search packages in the beta channel
nixos_search(query="nginx", channel="beta")

# Get information about a package in the 25.05 channel
nixos_info(name="python3", type="package", channel="25.05")
```

### Contributors

- James Brink (@utensils)
- Sean Callan (Moral Support)
