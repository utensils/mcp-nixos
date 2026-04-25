#!/usr/bin/env python3
"""MCP-NixOS Server - Model Context Protocol tools for NixOS, Home Manager, and nix-darwin.

Provides search and query capabilities for:
- NixOS packages, options, and programs via Elasticsearch API
- Home Manager configuration options via HTML documentation parsing
- nix-darwin (macOS) configuration options via HTML documentation parsing

All responses are formatted as human-readable plain text for optimal LLM interaction.
"""

import asyncio
import json
import os
import re
import sys
from typing import Annotated, Any

from fastmcp import FastMCP

from . import __version__

# Import from our modules
from .caches import (
    ChannelCache,
    NixDevCache,
    NixvimCache,
    NoogleCache,
    channel_cache,
    nixdev_cache,
    nixvim_cache,
    noogle_cache,
)
from .config import (
    BASE_CHANNELS,
    CACHE_NIXOS_ORG,
    DARWIN_URL,
    DEFAULT_LINE_LIMIT,
    FALLBACK_CHANNELS,
    FLAKE_INDEX,
    FLAKEHUB_API,
    FLAKEHUB_USER_AGENT,
    HOME_MANAGER_URL,
    KNOWN_SOURCES,
    MAX_FILE_SIZE,
    MAX_LINE_LIMIT,
    NIXDEV_BASE_URL,
    NIXDEV_SEARCH_INDEX,
    NIXHUB_API,
    NIXOS_API,
    NIXOS_AUTH,
    NIXVIM_META_BASE,
    NOOGLE_API,
    WIKI_API,
    APIError,
    DocumentParseError,
)
from .sources import (
    # Nixvim
    _browse_nixvim_options,
    # Noogle
    _browse_noogle_options,
    # Base
    _browse_options,
    # NixHub
    _check_binary_cache,
    # Flake inputs
    _check_nix_available,
    _check_system_cache,
    _fetch_nixhub_pkg,
    _fetch_nixhub_resolve,
    _fetch_nixhub_resolve_sync,
    _fetch_nixhub_search,
    _flake_inputs_list,
    _flake_inputs_ls,
    _flake_inputs_read,
    _flatten_inputs,
    _format_nixvim_option,
    _get_flake_inputs,
    _get_noogle_aliases,
    _get_noogle_description,
    _get_noogle_function_path,
    _get_noogle_type_signature,
    # Darwin
    _info_darwin,
    # FlakeHub
    _info_flakehub,
    # Home Manager
    _info_home_manager,
    # nix.dev
    _info_nixdev,
    _info_nixhub,
    # NixOS
    _info_nixos,
    _info_nixvim,
    _info_noogle,
    # Wiki
    _info_wiki,
    _list_channels,
    _run_nix_command,
    _search_darwin,
    _search_flakehub,
    # Flakes
    _search_flakes,
    _search_home_manager,
    # nix.dev
    _search_nixdev,
    _search_nixhub,
    _search_nixos,
    _search_nixvim,
    _search_noogle,
    _search_wiki,
    _stats_darwin,
    _stats_flakehub,
    _stats_flakes,
    _stats_home_manager,
    _stats_nixos,
    _stats_nixvim,
    _stats_noogle,
    _store_ls,
    _store_read,
    es_query,
    get_channel_suggestions,
    get_channels,
    validate_channel,
)
from .utils import (
    NarInfo,
    _format_release,
    _format_size,
    _is_binary_file,
    _parse_narinfo,
    _read_file_with_limit,
    _validate_store_path,
    _version_key,
    error,
    parse_html_options,
    strip_html,
)

# Create MCP server instance
#
# The `instructions` string is surfaced to clients via the MCP
# InitializeResult and is how hosts prime the model on when to
# reach for this server versus Bash/web search. Keep it short,
# intent-focused, and explicit about triggers; see GH #146.
_SERVER_INSTRUCTIONS = (
    "Use this server for any question about nixpkgs packages, NixOS / home-manager / "
    "nix-darwin / nixvim options, flakes, FlakeHub, channels, the binary cache, store "
    "paths, or the NixOS wiki and nix.dev docs. It queries live APIs (search.nixos.org, "
    "NixHub, FlakeHub, cache.nixos.org) and is faster and more current than `nix search`, "
    "scraping search.nixos.org by hand, or running `gh api` against NixOS/nixpkgs.\n\n"
    "Trigger on any mention of a Nix package name, attribute path, NixOS / "
    "home-manager / darwin option, channel name (unstable, 25.05, ...), flake input, "
    "or `/nix/store/` path. Use even when you think you know the answer — your training "
    "data lags nixpkgs by months.\n\n"
    "Two tools are exposed:\n"
    "- `nix` — unified search/info/stats/browse/channels/flake-inputs/cache/store across "
    "NixOS, Home Manager, nix-darwin, Nixvim, flakes, FlakeHub, NixHub, the NixOS wiki, "
    "nix.dev, and Noogle. For package version *history* pair with `nix_versions`.\n"
    "- `nix_versions` — commit-accurate history from NixHub (which nixpkgs commit "
    "shipped version X, what attribute path, which platforms).\n\n"
    "Common intents → calls (copy the JSON shape exactly):\n"
    '  "is package X in channel Y?"         → nix {"action":"info","query":"X","channel":"Y"}\n'
    '  "which channels are available?"      → nix {"action":"channels"}\n'
    '  "search NixOS options for X"         → nix {"action":"search","query":"X","type":"options"}\n'
    '  "home-manager option for X"          → nix {"action":"search","source":"home-manager","query":"X"}\n'
    '  "does X have a binary cache?"        → nix {"action":"cache","query":"X"}\n'
    '  "read /nix/store/<path>"             → nix {"action":"store","type":"read","query":"/nix/store/<path>"}\n'
    '  "which commit shipped X version Y?"  → nix_versions {"package":"X","version":"Y"}\n'
)

mcp = FastMCP("mcp-nixos", version=__version__, instructions=_SERVER_INSTRUCTIONS)


_TRUE_TOKENS = {"1", "true", "yes", "y", "on"}
_FALSE_TOKENS = {"0", "false", "no", "n", "off", ""}


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_TOKENS:
        return True
    if value in _FALSE_TOKENS:
        return False
    raise ValueError(f"{name} must be a boolean (true/false/1/0/yes/no), got {raw!r}")


# =============================================================================
# MCP Tools (only 2 exposed)
# =============================================================================


@mcp.tool()
async def nix(
    action: Annotated[
        str,
        "One of: search, info, stats, browse, channels, flake-inputs, cache, store. "
        "Use 'search' for keyword lookup, 'info' for details about a specific name, "
        "'browse' to walk an option hierarchy by prefix (home-manager/darwin/nixvim/noogle only). "
        "'store' reads files or lists directories at an explicit /nix/store/ path.",
    ],
    query: Annotated[
        str,
        "Search term for 'search', exact name for 'info', prefix path for 'browse'. "
        "For flake-inputs: input_name or input:path. For store: absolute /nix/store/ path. "
        "Leave empty for 'stats'/'channels'.",
    ] = "",
    source: Annotated[
        str,
        "Data source for search/info/stats/browse/cache. One of: nixos (default), "
        "home-manager, darwin, flakes, flakehub, nixvim, wiki, nix-dev, noogle, nixhub. "
        "For action=flake-inputs, this may instead be a path to a flake directory; "
        "omit/default to use the current project. Ignored by action=store.",
    ] = "nixos",
    type: Annotated[
        str,
        "Sub-type of query. For source=nixos with action=search, one of: "
        "packages, options, programs, flakes. For source=nixos with action=info, one of: "
        "package, option. For flake-inputs, one of: list, ls, read. For store, one of: "
        "ls, read. Ignored by most other sources.",
    ] = "packages",
    channel: Annotated[str, "NixOS channel: unstable (default), stable, or a release like 25.05."] = "unstable",
    limit: Annotated[int, "Max results. 1-100 (or 1-2000 for flake-inputs/store read)."] = 20,
    version: Annotated[str, "Only used by action=cache. Package version (default: latest)."] = "latest",
    system: Annotated[str, "Only used by action=cache. System arch e.g. x86_64-linux. Empty for all."] = "",
) -> str:
    """Query NixOS, Home Manager, Darwin, FlakeHub, flakes, Nixvim, Wiki, nix.dev, Noogle, NixHub.

    Use this tool for anything touching nixpkgs, Nix channels, flakes, NixOS / home-manager /
    darwin options, the binary cache, or /nix/store paths — even when you think you know the
    answer. Your training data lags nixpkgs by months. Prefer this over `nix search`, scraping
    search.nixos.org, or running `gh api` against NixOS/nixpkgs.

    INTENTS → CALLS (copy the JSON shape exactly):
      "is package X in channel Y?"        → {"action": "info", "query": "X", "channel": "Y"}
      "search for package X"              → {"action": "search", "query": "X"}
      "which channels are available?"     → {"action": "channels"}
      "which commit did channel X index?" → {"action": "channels"}  (indexed commit shown when known;
                                                                     branch HEAD otherwise — label matters)
      "search NixOS options for X"        → {"action": "search", "query": "X", "type": "options"}
      "get option details for X"          → {"action": "info", "query": "X", "type": "option"}
      "home-manager option for X"         → {"action": "search", "query": "X", "source": "home-manager"}
      "darwin option for X"               → {"action": "search", "query": "X", "source": "darwin"}
      "nixvim option for X"               → {"action": "search", "query": "X", "source": "nixvim"}
      "what programs does pkg X provide?" → {"action": "search", "query": "X", "type": "programs"}
      "count packages/options"            → {"action": "stats"}
      "browse hm option tree under P"     → {"action": "browse", "query": "P", "source": "home-manager"}
      "does X have a binary cache?"       → {"action": "cache", "query": "X"}
      "search the NixOS wiki for X"       → {"action": "search", "query": "X", "source": "wiki"}
      "search nix.dev docs"               → {"action": "search", "query": "X", "source": "nix-dev"}
      "read a nix.dev page"               → {"action": "info", "query": "tutorials/nix-language", "source": "nix-dev"}
      "list inputs of current flake"      → {"action": "flake-inputs"}
      "ls inside flake input X"           → {"action": "flake-inputs", "type": "ls", "query": "X"}
      "read /nix/store/... file"          → {"action": "store", "type": "read", "query": "/nix/store/..."}
      "ls /nix/store/... dir"             → {"action": "store", "type": "ls",   "query": "/nix/store/..."}

    For package version *history* ("which commit shipped firefox 150?", "when was node 18 added?"),
    use the separate `nix_versions` tool — it returns commit hashes, attribute paths, and dates.

    Notes:
      - To search NixOS *options*, use action=search with type=options. Do NOT use action=browse
        for source=nixos — browse is for walking a pre-indexed option tree and only works with
        home-manager, darwin, nixvim, or noogle.
      - For source=nix-dev, action=info returns the page markdown. The query may be a bare
        docname like "tutorials/nix-language", the URL printed by nix-dev search
        ("https://nix.dev/tutorials/nix-language"), or a rendered ".html" URL.
      - action=info for packages matches on the exact attribute path first, then the exact pname.
        If multiple packages share a pname (e.g. firefox / firefox-esr / firefox-mobile), the
        canonical attribute wins and the response flags the disambiguation explicitly.
      - Omit parameters you don't need; do not pass empty strings for optional args.
    """
    # Limit validation: flake-inputs/store read allow up to 2000, others limited to 100
    if action == "flake-inputs" and type == "read":
        if not 1 <= limit <= MAX_LINE_LIMIT:
            return error(f"Limit must be 1-{MAX_LINE_LIMIT} for flake-inputs read")
    elif action == "store" and type == "read":
        if not 1 <= limit <= MAX_LINE_LIMIT:
            return error(f"Limit must be 1-{MAX_LINE_LIMIT} for store read")
    elif not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    # Accept `browse` as canonical, keep `options` as a legacy alias.
    # The action=options name was confusing small models (GitHub #125).
    if action == "options":
        action = "browse"

    if action == "search":
        if not query:
            return error('Query required for search. Example: {"action": "search", "query": "firefox"}')
        if source == "nixos":
            if type not in ["packages", "options", "programs", "flakes"]:
                return error(
                    "For source=nixos, type must be one of: packages, options, programs, flakes. "
                    'Example: {"action": "search", "query": "nginx", "type": "options"}'
                )
            return await asyncio.to_thread(_search_nixos, query, type, limit, channel)
        elif source == "home-manager":
            return await asyncio.to_thread(_search_home_manager, query, limit)
        elif source == "darwin":
            return await asyncio.to_thread(_search_darwin, query, limit)
        elif source == "flakes":
            return await asyncio.to_thread(_search_flakes, query, limit)
        elif source == "flakehub":
            return await asyncio.to_thread(_search_flakehub, query, limit)
        elif source == "nixvim":
            return await asyncio.to_thread(_search_nixvim, query, limit)
        elif source == "wiki":
            return await asyncio.to_thread(_search_wiki, query, limit)
        elif source == "nix-dev":
            return await asyncio.to_thread(_search_nixdev, query, limit)
        elif source == "noogle":
            return await asyncio.to_thread(_search_noogle, query, limit)
        elif source == "nixhub":
            return await _search_nixhub(query, limit)
        else:
            return error(
                f"Unknown source: {source!r}. Must be one of: "
                "nixos, home-manager, darwin, flakes, flakehub, nixvim, wiki, nix-dev, noogle, nixhub."
            )

    elif action == "info":
        if not query:
            return error('Name required for info. Example: {"action": "info", "query": "firefox"}')
        if source == "flakes":
            example = json.dumps({"action": "search", "source": "flakes", "query": query})
            return error(
                f"action=info is not supported for source=flakes. Use action=search instead. Example: {example}."
            )
        if source == "nixos":
            if type not in ["package", "packages", "option", "options"]:
                return error(
                    "For source=nixos, type must be 'package' or 'option'. "
                    'Example: {"action": "info", "query": "services.nginx.enable", "type": "option"}'
                )
            info_type = "package" if type in ["package", "packages"] else "option"
            return await asyncio.to_thread(_info_nixos, query, info_type, channel)
        elif source == "home-manager":
            return await asyncio.to_thread(_info_home_manager, query)
        elif source == "darwin":
            return await asyncio.to_thread(_info_darwin, query)
        elif source == "flakehub":
            return await asyncio.to_thread(_info_flakehub, query)
        elif source == "nixvim":
            return await asyncio.to_thread(_info_nixvim, query)
        elif source == "wiki":
            return await asyncio.to_thread(_info_wiki, query)
        elif source == "nix-dev":
            return await asyncio.to_thread(_info_nixdev, query)
        elif source == "noogle":
            return await asyncio.to_thread(_info_noogle, query)
        elif source == "nixhub":
            return await _info_nixhub(query)
        else:
            return error(
                f"Unknown source: {source!r}. For action=info, must be one of: "
                "nixos, home-manager, darwin, flakehub, nixvim, wiki, nix-dev, noogle, nixhub."
            )

    elif action == "stats":
        if source == "nixos":
            return await asyncio.to_thread(_stats_nixos, channel)
        elif source == "home-manager":
            return await asyncio.to_thread(_stats_home_manager)
        elif source == "darwin":
            return await asyncio.to_thread(_stats_darwin)
        elif source == "flakes":
            return await asyncio.to_thread(_stats_flakes)
        elif source == "flakehub":
            return await asyncio.to_thread(_stats_flakehub)
        elif source == "nixvim":
            return await asyncio.to_thread(_stats_nixvim)
        elif source == "noogle":
            return await asyncio.to_thread(_stats_noogle)
        elif source in ["wiki", "nix-dev", "nixhub"]:
            return error(f"Stats not available for source={source}.")
        else:
            return error(
                f"Unknown source: {source!r}. For action=stats, must be one of: "
                "nixos, home-manager, darwin, flakes, flakehub, nixvim, noogle."
            )

    elif action == "browse":
        if source == "nixos":
            return error(
                "action=browse is not for NixOS. To search NixOS options, use: "
                '{"action": "search", "query": "nginx", "type": "options"}. '
                "To get a specific option's details, use: "
                '{"action": "info", "query": "services.nginx.enable", "type": "option"}.'
            )
        if source not in ["home-manager", "darwin", "nixvim", "noogle"]:
            return error(
                "action=browse only supports source in: home-manager, darwin, nixvim, noogle. "
                'Example: {"action": "browse", "query": "programs", "source": "home-manager"}'
            )
        if source == "nixvim":
            return await asyncio.to_thread(_browse_nixvim_options, query)
        if source == "noogle":
            return await asyncio.to_thread(_browse_noogle_options, query)
        return await asyncio.to_thread(_browse_options, source, query)

    elif action == "channels":
        return await asyncio.to_thread(_list_channels)

    elif action == "flake-inputs":
        # Determine flake directory: use source if it's not a known source name
        flake_dir = source if source not in KNOWN_SOURCES else "."

        # Validate type parameter for flake-inputs
        # Note: "packages" is accepted as alias for "list" (default type parameter)
        if type not in ["list", "ls", "read", "packages"]:
            return error("Type must be one of: list, ls, read for flake-inputs")

        # Handle limit for read operation
        read_limit = limit
        if type == "read":
            if limit == 20:  # Default was used, apply DEFAULT_LINE_LIMIT
                read_limit = DEFAULT_LINE_LIMIT
            # Ensure read_limit doesn't exceed MAX_LINE_LIMIT
            read_limit = min(read_limit, MAX_LINE_LIMIT)

        # Route to appropriate function
        if type == "list" or type == "packages":
            return await _flake_inputs_list(flake_dir)
        elif type == "ls":
            if not query:
                return error("Query required for ls (input name or input:path)")
            return await _flake_inputs_ls(flake_dir, query)
        elif type == "read":
            if not query:
                return error("Query required for read (input:path format)")
            return await _flake_inputs_read(flake_dir, query, read_limit)
        else:
            return error("Type must be one of: list, ls, read for flake-inputs")

    elif action == "cache":
        if not query:
            return error("Package name required for cache action")
        return await _check_binary_cache(query, version, system)

    elif action == "store":
        if type not in ["ls", "read"]:
            return error(
                "Type must be one of: ls, read for store. "
                'Example: {"action": "store", "type": "ls", "query": "/nix/store/<hash>-<name>"}'
            )
        if not query:
            return error(
                "Query required for store (absolute /nix/store/ path). "
                'Example: {"action": "store", "type": "ls", "query": "/nix/store/<hash>-<name>"}'
            )
        if type == "ls":
            # Match _store_read's default-promotion so a bare call returns a
            # useful window of entries for large /nix/store directories
            # instead of only the first 20.
            ls_limit = limit if limit != 20 else DEFAULT_LINE_LIMIT
            ls_limit = min(ls_limit, MAX_LINE_LIMIT)
            return await _store_ls(query, ls_limit)

        # type == "read": default limit behavior mirrors flake-inputs read.
        read_limit = limit
        if limit == 20:  # Default was used, apply DEFAULT_LINE_LIMIT
            read_limit = DEFAULT_LINE_LIMIT
        read_limit = min(read_limit, MAX_LINE_LIMIT)
        return await _store_read(query, read_limit)

    else:
        return error(
            f"Unknown action: {action!r}. Must be one of: "
            "search, info, stats, browse, channels, flake-inputs, cache, store. "
            'Example: {"action": "search", "query": "firefox"}'
        )


@mcp.tool()
async def nix_versions(
    package: Annotated[str, "Package name"],
    version: Annotated[str, "Specific version to find"] = "",
    limit: Annotated[int, "1-50"] = 10,
) -> str:
    """Get package version history from NixHub.io."""
    if not package or not package.strip():
        return error("Package name required")
    if not re.match(r"^[a-zA-Z0-9\-_.]+$", package):
        return error("Invalid package name")
    if not 1 <= limit <= 50:
        return error("Limit must be 1-50")

    # Fetch package data via thread pool to avoid blocking event loop
    err, data = await asyncio.to_thread(_fetch_nixhub_pkg, package)
    if err:
        return err

    try:
        # v1/pkg returns an array of version records
        if not isinstance(data, list) or not data:
            return error(f"Package '{package}' not found", "NOT_FOUND")

        releases: list[dict[str, Any]] = data

        # If specific version requested, find it
        if version:
            for release in releases:
                if release.get("version") == version:
                    version_lines = [f"Found {package} version {version}\n"]
                    # Get commit hash from the release
                    commit = release.get("commit_hash", "")
                    if commit and re.match(r"^[a-fA-F0-9]{40}$", commit):
                        version_lines.append(f"Nixpkgs commit: {commit}")
                        # Get attribute path from systems data
                        systems_dict = release.get("systems", {})
                        if isinstance(systems_dict, dict):
                            for sys_info in systems_dict.values():
                                if isinstance(sys_info, dict):
                                    attr_paths = sys_info.get("attr_paths", [])
                                    if attr_paths:
                                        version_lines.append(f"  Attribute: {attr_paths[0]}")
                                        break
                    return "\n".join(version_lines)

            # Version not found
            versions_list: list[str] = [str(r.get("version", "")) for r in releases[:limit]]
            return f"Version {version} not found for {package}\nAvailable: {', '.join(versions_list)}"

        # Build package header with rich metadata from first (latest) release
        results: list[str] = [f"Package: {package}"]
        latest = releases[0]

        # Add package-level metadata from latest release
        license_info: str = latest.get("license", "")
        if license_info:
            results.append(f"License: {license_info}")

        homepage: str = latest.get("homepage", "")
        if homepage:
            results.append(f"Homepage: {homepage}")

        # Get programs from systems data
        programs: list[str] = []
        systems_dict = latest.get("systems", {})
        if isinstance(systems_dict, dict):
            for sys_info in systems_dict.values():
                if isinstance(sys_info, dict):
                    sys_programs = sys_info.get("programs", [])
                    if sys_programs:
                        programs = sys_programs
                        break
        if programs:
            progs = programs[:10]
            prog_str = ", ".join(progs)
            if len(programs) > 10:
                prog_str += f" ... ({len(programs)} total)"
            results.append(f"Programs: {prog_str}")

        results.append(f"Total versions: {len(releases)}")
        results.append("")

        # Return version history
        shown: list[dict[str, Any]] = releases[:limit]
        results.append(f"Recent versions ({len(shown)} of {len(releases)}):\n")
        for release in shown:
            results.extend(_format_release(release, package))
            results.append("")
        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


def main() -> None:
    """Run the MCP server."""
    try:
        transport = os.environ.get("MCP_NIXOS_TRANSPORT", "").strip().lower()
        if transport in {"", "stdio"}:
            # Defaults to STDIO transport
            mcp.run()
        elif transport == "http":
            host = os.environ.get("MCP_NIXOS_HOST", "127.0.0.1").strip() or "127.0.0.1"
            port_raw = os.environ.get("MCP_NIXOS_PORT", "8000").strip() or "8000"
            try:
                port = int(port_raw)
            except ValueError:
                raise ValueError("MCP_NIXOS_PORT must be an integer") from None

            if not 1 <= port <= 65535:
                raise ValueError("MCP_NIXOS_PORT must be between 1 and 65535")

            path_raw = os.environ.get("MCP_NIXOS_PATH")
            if path_raw is None:
                path = "/mcp"
            else:
                path = path_raw.strip()
                if not path:
                    raise ValueError("MCP_NIXOS_PATH must be a non-empty absolute path")

            if not path.startswith("/"):
                raise ValueError("MCP_NIXOS_PATH must start with '/'")
            if "//" in path:
                raise ValueError("MCP_NIXOS_PATH must not contain '//'")

            stateless_http = env_bool("MCP_NIXOS_STATELESS_HTTP", default=False)
            mcp.run(transport="http", host=host, port=port, path=path, stateless_http=stateless_http)
        else:
            raise ValueError("MCP_NIXOS_TRANSPORT must be one of: stdio, http")
    except KeyboardInterrupt:
        pass
    except ValueError as exc:
        print(f"mcp-nixos: error: {exc}", file=sys.stderr)
        sys.exit(1)


# =============================================================================
# Backward compatibility exports for tests
# =============================================================================

# Re-export all symbols that tests may import from server.py
__all__ = [
    # MCP server and tools
    "mcp",
    "main",
    "env_bool",
    "nix",
    "nix_versions",
    # Exceptions
    "APIError",
    "DocumentParseError",
    # Config constants
    "NIXOS_API",
    "NIXOS_AUTH",
    "BASE_CHANNELS",
    "FALLBACK_CHANNELS",
    "HOME_MANAGER_URL",
    "DARWIN_URL",
    "FLAKE_INDEX",
    "FLAKEHUB_API",
    "FLAKEHUB_USER_AGENT",
    "NIXVIM_META_BASE",
    "WIKI_API",
    "NIXDEV_SEARCH_INDEX",
    "NIXDEV_BASE_URL",
    "NOOGLE_API",
    "NIXHUB_API",
    "CACHE_NIXOS_ORG",
    "MAX_FILE_SIZE",
    "DEFAULT_LINE_LIMIT",
    "MAX_LINE_LIMIT",
    "KNOWN_SOURCES",
    # Cache classes and instances
    "ChannelCache",
    "NixvimCache",
    "NixDevCache",
    "NoogleCache",
    "channel_cache",
    "nixvim_cache",
    "nixdev_cache",
    "noogle_cache",
    # Utility functions
    "strip_html",
    "error",
    "parse_html_options",
    "_version_key",
    "_format_release",
    "_format_size",
    "NarInfo",
    "_parse_narinfo",
    "_validate_store_path",
    "_is_binary_file",
    "_read_file_with_limit",
    "_check_nix_available",
    # Channel functions
    "get_channels",
    "validate_channel",
    "get_channel_suggestions",
    "es_query",
    # NixOS functions
    "_search_nixos",
    "_info_nixos",
    "_stats_nixos",
    # Home Manager functions
    "_search_home_manager",
    "_info_home_manager",
    "_stats_home_manager",
    # Darwin functions
    "_search_darwin",
    "_info_darwin",
    "_stats_darwin",
    # Flakes functions
    "_search_flakes",
    "_stats_flakes",
    # FlakeHub functions
    "_search_flakehub",
    "_info_flakehub",
    "_stats_flakehub",
    # Wiki functions
    "_search_wiki",
    "_info_wiki",
    # nix.dev functions
    "_search_nixdev",
    "_info_nixdev",
    # Nixvim functions
    "_search_nixvim",
    "_info_nixvim",
    "_format_nixvim_option",
    "_stats_nixvim",
    "_browse_nixvim_options",
    # Noogle functions
    "_get_noogle_function_path",
    "_get_noogle_type_signature",
    "_get_noogle_aliases",
    "_get_noogle_description",
    "_search_noogle",
    "_info_noogle",
    "_stats_noogle",
    "_browse_noogle_options",
    # Browsing utilities
    "_list_channels",
    "_browse_options",
    # NixHub functions
    "_check_system_cache",
    "_fetch_nixhub_resolve",
    "_check_binary_cache",
    "_fetch_nixhub_search",
    "_search_nixhub",
    "_fetch_nixhub_pkg",
    "_fetch_nixhub_resolve_sync",
    "_info_nixhub",
    # Flake inputs functions
    "_run_nix_command",
    "_get_flake_inputs",
    "_flatten_inputs",
    "_flake_inputs_list",
    "_flake_inputs_ls",
    "_flake_inputs_read",
    # Store functions
    "_store_ls",
    "_store_read",
]


if __name__ == "__main__":
    main()
