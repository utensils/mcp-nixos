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
# Last-resort channel map, used only when alias discovery fails outright.
# These generations bit-rot: Hydra retires old `latest-<gen>-nixos-*` aliases,
# and a retired alias 404s on every query. The cache therefore never memoizes a
# fallback result — it retries discovery on the next call (see ChannelCache) —
# so this map only has to cover a single request during an upstream blip.
FALLBACK_CHANNELS = {
    "unstable": "latest-50-nixos-unstable",
    "stable": "latest-50-nixos-26.05",
    "26.05": "latest-50-nixos-26.05",
    "25.11": "latest-48-nixos-25.11",
    "beta": "latest-50-nixos-26.05",
}

# Home Manager's option docs are split across mdBook pages. The print view keeps
# the complete option catalogue in one document for search, info, browse, and stats.
HOME_MANAGER_URL = "https://nix-community.github.io/home-manager/print.html"
DARWIN_URL = "https://nix-darwin.github.io/nix-darwin/manual/index.html"
# Fallback only: the live `latest-<gen>-group-manual` alias is discovered from
# `_cat/aliases` at runtime (see ChannelCache.get_flake_index), because Hydra
# retires old generations and a hardcoded one eventually 404s.
FLAKE_INDEX = "latest-51-group-manual"

# FlakeHub API (Determinate Systems)
FLAKEHUB_API = "https://api.flakehub.com"
FLAKEHUB_USER_AGENT = f"mcp-nixos/{__version__}"

# Nixvim options via NuschtOS search infrastructure.
# Layout (reorganized mid-2026; old `…/search/meta/N.json` path was removed):
#   data/options/chunks/N.json  →  ~300 options per chunk, JSON array of Option objects
#   data/options/meta.json      →  scope metadata (licenses/maintainers/teams)
#   data/options/index.ixx      →  binary search index (WASM-backed; not used here)
# We walk chunks until 404 and search in Python. The current catalogue is
# approximately 60 chunks / 17,000 options and fits comfortably in memory.
# Credit: https://github.com/NuschtOS/search - Simple and fast static-page NixOS option search
NIXVIM_OPTIONS_CHUNKS_BASE = "https://nix-community.github.io/nixvim/search/data/options/chunks"
# Kept for backward compatibility / potential scope lookups; not used by the chunked loader.
NIXVIM_META_BASE = "https://nix-community.github.io/nixvim/search/data"

# NVF options from the latest published (unstable) documentation.
NVF_OPTIONS_URL = "https://nvf.notashelf.dev/options.html"

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
    "nvf",
    "wiki",
    "nix-dev",
    "noogle",
    "nixhub",
}
