#!/usr/bin/env python3
"""MCP-NixOS Server - Model Context Protocol tools for NixOS, Home Manager, and nix-darwin.

Provides search and query capabilities for:
- NixOS packages, options, and programs via Elasticsearch API
- Home Manager configuration options via HTML documentation parsing
- nix-darwin (macOS) configuration options via HTML documentation parsing

All responses are formatted as human-readable plain text for optimal LLM interaction.
"""

import asyncio
import re
from typing import Annotated, Any

from fastmcp import FastMCP

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
mcp = FastMCP("mcp-nixos")


# =============================================================================
# MCP Tools (only 2 exposed)
# =============================================================================


@mcp.tool()
async def nix(
    action: Annotated[str, "search|info|stats|options|channels|flake-inputs|cache"],
    query: Annotated[str, "Search term, name, or prefix. For flake-inputs: input_name or input:path"] = "",
    source: Annotated[str, "nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle|nixhub"] = "nixos",
    type: Annotated[str, "packages|options|programs|list|ls|read"] = "packages",
    channel: Annotated[str, "unstable|stable|25.05"] = "unstable",
    limit: Annotated[int, "1-100 (or 1-2000 for flake-inputs read)"] = 20,
    version: Annotated[str, "Version for cache action (default: latest)"] = "latest",
    system: Annotated[str, "System for cache action (e.g., x86_64-linux). Empty for all."] = "",
) -> str:
    """Query NixOS, Home Manager, Darwin, flakes, FlakeHub, Nixvim, Wiki, nix.dev, Noogle, NixHub, or flake inputs."""
    # Limit validation: flake-inputs read allows up to 2000, others limited to 100
    if action == "flake-inputs" and type == "read":
        if not 1 <= limit <= MAX_LINE_LIMIT:
            return error(f"Limit must be 1-{MAX_LINE_LIMIT} for flake-inputs read")
    elif not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    if action == "search":
        if not query:
            return error("Query required for search")
        if source == "nixos":
            if type not in ["packages", "options", "programs", "flakes"]:
                return error("Type must be packages|options|programs|flakes")
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
            return error("Source must be nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle|nixhub")

    elif action == "info":
        if not query:
            return error("Name required for info")
        if source == "nixos":
            if type not in ["package", "packages", "option", "options"]:
                return error("Type must be package|option")
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
            return error("Info not available for nix-dev. Use search to find docs, then visit the URL.")
        elif source == "noogle":
            return await asyncio.to_thread(_info_noogle, query)
        elif source == "nixhub":
            return await _info_nixhub(query)
        else:
            return error("Source must be nixos|home-manager|darwin|flakehub|nixvim|wiki|nix-dev|noogle|nixhub")

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
            return error(f"Stats not available for {source}")
        else:
            return error("Source must be nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle|nixhub")

    elif action == "options":
        if source not in ["home-manager", "darwin", "nixvim", "noogle"]:
            return error("Options browsing only for home-manager|darwin|nixvim|noogle")
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
            return error("Type must be list|ls|read for flake-inputs")

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
            return error("Type must be list|ls|read for flake-inputs")

    elif action == "cache":
        if not query:
            return error("Package name required for cache action")
        return await _check_binary_cache(query, version, system)

    else:
        return error("Action must be search|info|stats|options|channels|flake-inputs|cache")


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
        mcp.run()
    except KeyboardInterrupt:
        pass


# =============================================================================
# Backward compatibility exports for tests
# =============================================================================

# Re-export all symbols that tests may import from server.py
__all__ = [
    # MCP server and tools
    "mcp",
    "main",
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
]


if __name__ == "__main__":
    main()
