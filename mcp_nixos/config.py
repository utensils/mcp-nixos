"""Configuration constants and exception classes for MCP-NixOS server."""

from . import __version__


class APIError(Exception):
    """Custom exception for API-related errors."""


class DocumentParseError(Exception):
    """Custom exception for document parsing errors."""


# API Configuration
NIXOS_API = "https://search.nixos.org/backend"
NIXOS_AUTH = ("aWVSALXpZv", "X8gPHnzL52wFEekuxsfQ9cSh")

# Base channel patterns - these are dynamic and auto-discovered
BASE_CHANNELS = {
    "unstable": "nixos-unstable",
    "25.05": "nixos-25.05",
    "25.11": "nixos-25.11",
}

# Fallback channels when API discovery fails (static mappings based on recent patterns)
FALLBACK_CHANNELS = {
    "unstable": "latest-44-nixos-unstable",
    "stable": "latest-44-nixos-25.11",
    "25.05": "latest-44-nixos-25.05",
    "25.11": "latest-44-nixos-25.11",
    "beta": "latest-44-nixos-25.11",
}

HOME_MANAGER_URL = "https://nix-community.github.io/home-manager/options.xhtml"
DARWIN_URL = "https://nix-darwin.github.io/nix-darwin/manual/index.html"
FLAKE_INDEX = "latest-44-group-manual"

# FlakeHub API (Determinate Systems)
FLAKEHUB_API = "https://api.flakehub.com"
FLAKEHUB_USER_AGENT = f"mcp-nixos/{__version__}"

# Nixvim options via NuschtOS search infrastructure (paginated, ~300 options per chunk)
# Credit: https://github.com/NuschtOS/search - Simple and fast static-page NixOS option search
NIXVIM_META_BASE = "https://nix-community.github.io/nixvim/search/meta"

# NixOS Wiki (MediaWiki API)
WIKI_API = "https://wiki.nixos.org/w/api.php"

# nix.dev documentation (Sphinx search index)
NIXDEV_SEARCH_INDEX = "https://nix.dev/searchindex.js"
NIXDEV_BASE_URL = "https://nix.dev"

# Noogle API (Nix function search)
NOOGLE_API = "https://noogle.dev/api/v1/data"

# NixHub API (binary cache, package metadata)
NIXHUB_API = "https://search.devbox.sh"
CACHE_NIXOS_ORG = "https://cache.nixos.org"

# Flake inputs constants
# Maximum file size for reading (1MB)
MAX_FILE_SIZE = 1024 * 1024
# Default and maximum line limits
DEFAULT_LINE_LIMIT = 500
MAX_LINE_LIMIT = 2000
# Known sources (to distinguish from flake paths)
KNOWN_SOURCES = {
    "nixos",
    "home-manager",
    "darwin",
    "flakes",
    "flakehub",
    "nixvim",
    "wiki",
    "nix-dev",
    "noogle",
    "nixhub",
}
