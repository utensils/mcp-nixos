"""Data source implementations for MCP-NixOS server.

This module re-exports all source functions for backward compatibility.
Each source is implemented in its own module for better organization.
"""

# Base functionality (channel helpers, elasticsearch, browsing)
from .base import (
    _browse_options,
    _list_channels,
    es_query,
    get_channel_suggestions,
    get_channels,
    validate_channel,
)

# nix-darwin options
from .darwin import (
    _info_darwin,
    _search_darwin,
    _stats_darwin,
)

# Flake inputs (local nix store)
from .flake_inputs import (
    _check_nix_available,
    _flake_inputs_list,
    _flake_inputs_ls,
    _flake_inputs_read,
    _flatten_inputs,
    _get_flake_inputs,
    _run_nix_command,
)

# FlakeHub (Determinate Systems)
from .flakehub import (
    _info_flakehub,
    _search_flakehub,
    _stats_flakehub,
)

# NixOS flakes (search.nixos.org)
from .flakes import (
    _search_flakes,
    _stats_flakes,
)

# Home Manager options
from .home_manager import (
    _info_home_manager,
    _search_home_manager,
    _stats_home_manager,
)

# nix.dev documentation
from .nixdev import (
    _search_nixdev,
)

# NixHub (binary cache, package metadata)
from .nixhub import (
    _check_binary_cache,
    _check_system_cache,
    _fetch_nixhub_pkg,
    _fetch_nixhub_resolve,
    _fetch_nixhub_resolve_sync,
    _fetch_nixhub_search,
    _info_nixhub,
    _search_nixhub,
)

# NixOS packages and options
from .nixos import (
    _info_nixos,
    _search_nixos,
    _stats_nixos,
)

# Nixvim options
from .nixvim import (
    _browse_nixvim_options,
    _format_nixvim_option,
    _info_nixvim,
    _search_nixvim,
    _stats_nixvim,
)

# Noogle (Nix function search)
from .noogle import (
    _browse_noogle_options,
    _get_noogle_aliases,
    _get_noogle_description,
    _get_noogle_function_path,
    _get_noogle_type_signature,
    _info_noogle,
    _search_noogle,
    _stats_noogle,
)

# NixOS Wiki
from .wiki import (
    _info_wiki,
    _search_wiki,
)

__all__ = [
    # Base
    "get_channels",
    "validate_channel",
    "get_channel_suggestions",
    "es_query",
    "_list_channels",
    "_browse_options",
    # NixOS
    "_search_nixos",
    "_info_nixos",
    "_stats_nixos",
    # Home Manager
    "_search_home_manager",
    "_info_home_manager",
    "_stats_home_manager",
    # Darwin
    "_search_darwin",
    "_info_darwin",
    "_stats_darwin",
    # Flakes
    "_search_flakes",
    "_stats_flakes",
    # FlakeHub
    "_search_flakehub",
    "_info_flakehub",
    "_stats_flakehub",
    # Wiki
    "_search_wiki",
    "_info_wiki",
    # nix.dev
    "_search_nixdev",
    # Nixvim
    "_search_nixvim",
    "_info_nixvim",
    "_format_nixvim_option",
    "_stats_nixvim",
    "_browse_nixvim_options",
    # Noogle
    "_get_noogle_function_path",
    "_get_noogle_type_signature",
    "_get_noogle_aliases",
    "_get_noogle_description",
    "_search_noogle",
    "_info_noogle",
    "_stats_noogle",
    "_browse_noogle_options",
    # NixHub
    "_check_system_cache",
    "_fetch_nixhub_resolve",
    "_check_binary_cache",
    "_fetch_nixhub_search",
    "_search_nixhub",
    "_fetch_nixhub_pkg",
    "_fetch_nixhub_resolve_sync",
    "_info_nixhub",
    # Flake inputs
    "_check_nix_available",
    "_run_nix_command",
    "_get_flake_inputs",
    "_flatten_inputs",
    "_flake_inputs_list",
    "_flake_inputs_ls",
    "_flake_inputs_read",
]
