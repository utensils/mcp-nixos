#!/usr/bin/env python3
"""MCP-NixOS Server - Model Context Protocol tools for NixOS, Home Manager, and nix-darwin.

Provides search and query capabilities for:
- NixOS packages, options, and programs via Elasticsearch API
- Home Manager configuration options via HTML documentation parsing
- nix-darwin (macOS) configuration options via HTML documentation parsing

All responses are formatted as human-readable plain text for optimal LLM interaction.
"""

import re
from typing import Annotated, Any

import aiohttp
import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from pydantic import Field


class APIError(Exception):
    """Custom exception for API-related errors."""


class DocumentParseError(Exception):
    """Custom exception for document parsing errors."""


mcp = FastMCP("mcp-nixos")

# API Configuration
NIXOS_API = "https://search.nixos.org/backend"
NIXOS_AUTH = ("aWVSALXpZv", "X8gPHnzL52wFEekuxsfQ9cSh")

# Base channel patterns - these are dynamic and auto-discovered
BASE_CHANNELS = {
    "unstable": "nixos-unstable",
    "24.11": "nixos-24.11",
    "25.05": "nixos-25.05",
}

HOME_MANAGER_URL = "https://nix-community.github.io/home-manager/options.xhtml"
DARWIN_URL = "https://nix-darwin.github.io/nix-darwin/manual/index.html"


class ChannelCache:
    """Cache for discovered channels and resolved mappings."""

    def __init__(self) -> None:
        """Initialize empty cache."""
        self.available_channels: dict[str, str] | None = None
        self.resolved_channels: dict[str, str] | None = None

    def get_available(self) -> dict[str, str]:
        """Get available channels, discovering if needed."""
        if self.available_channels is None:
            self.available_channels = self._discover_available_channels()
        return self.available_channels if self.available_channels is not None else {}

    def get_resolved(self) -> dict[str, str]:
        """Get resolved channel mappings, resolving if needed."""
        if self.resolved_channels is None:
            self.resolved_channels = self._resolve_channels()
        return self.resolved_channels if self.resolved_channels is not None else {}

    def _discover_available_channels(self) -> dict[str, str]:
        """Discover available NixOS channels by testing API patterns."""
        # Test multiple generation patterns (43, 44, 45) and versions
        generations = [43, 44, 45, 46]  # Future-proof
        versions = ["unstable", "20.09", "24.11", "25.05", "25.11", "26.05", "30.05"]  # Past, current and future

        available = {}
        for gen in generations:
            for version in versions:
                pattern = f"latest-{gen}-nixos-{version}"
                try:
                    resp = requests.post(
                        f"{NIXOS_API}/{pattern}/_count",
                        json={"query": {"match_all": {}}},
                        auth=NIXOS_AUTH,
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        count = resp.json().get("count", 0)
                        if count > 0:
                            available[pattern] = f"{count:,} documents"
                except Exception:
                    continue

        return available

    def _resolve_channels(self) -> dict[str, str]:
        """Resolve user-friendly channel names to actual indices."""
        available = self.get_available()
        resolved = {}

        # Find unstable (should be consistent)
        unstable_pattern = None
        for pattern in available:
            if "unstable" in pattern:
                unstable_pattern = pattern
                break

        if unstable_pattern:
            resolved["unstable"] = unstable_pattern

        # Find stable release (highest version number with most documents)
        stable_candidates = []
        for pattern, count_str in available.items():
            if "unstable" not in pattern:
                # Extract version (e.g., "25.05" from "latest-43-nixos-25.05")
                parts = pattern.split("-")
                if len(parts) >= 4:
                    version = parts[3]  # "25.05"
                    try:
                        # Parse version for comparison (25.05 -> 25.05)
                        major, minor = map(int, version.split("."))
                        count = int(count_str.replace(",", "").replace(" documents", ""))
                        stable_candidates.append((major, minor, version, pattern, count))
                    except (ValueError, IndexError):
                        continue

        if stable_candidates:
            # Sort by version (descending), then by document count (descending) as tiebreaker
            stable_candidates.sort(key=lambda x: (x[0], x[1], x[4]), reverse=True)
            current_stable = stable_candidates[0]

            resolved["stable"] = current_stable[3]  # pattern
            resolved[current_stable[2]] = current_stable[3]  # version -> pattern

            # Add other version mappings (prefer higher generation/count for same version)
            version_patterns: dict[str, tuple[str, int]] = {}
            for _major, _minor, version, pattern, count in stable_candidates:
                if version not in version_patterns or count > version_patterns[version][1]:
                    version_patterns[version] = (pattern, count)

            for version, (pattern, _count) in version_patterns.items():
                resolved[version] = pattern

        # Add beta (alias for stable)
        if "stable" in resolved:
            resolved["beta"] = resolved["stable"]

        return resolved


# Create a single instance of the cache
channel_cache = ChannelCache()


class NixOSContext:
    """Shared context manager for tools to preserve state between calls."""

    def __init__(self) -> None:
        self.last_search_results: list[dict[str, Any]] = []
        self.last_search_query = ""
        self.last_search_type = ""
        self.last_package_name = None
        self.last_channel = "unstable"
        self.user_preferences = {
            "verbosity": "normal",  # normal, concise
            "default_install_method": "user",  # user, system, shell, home
        }

    def update_search_context(self, query: str, search_type: str, results: list[dict[str, Any]]) -> None:
        """Update context with search results."""
        self.last_search_query = query
        self.last_search_type = search_type
        self.last_search_results = results

        # Extract package names for quick reference
        if results and search_type == "packages":
            first_result = results[0].get("_source", {})
            self.last_package_name = first_result.get("package_pname", "")

    def get_recent_package(self, name: str | None = None) -> str | None:
        """Get the most recently searched package name."""
        if name:
            return name

        # If we have a recent package from search
        if self.last_package_name and self.last_search_type == "packages":
            return self.last_package_name

        # If there's only one result from recent search
        if len(self.last_search_results) == 1:
            source = self.last_search_results[0].get("_source", {})
            if self.last_search_type == "packages":
                return str(source.get("package_pname", ""))
            elif self.last_search_type == "options":
                return str(source.get("option_name", ""))

        return None

    def get_result_by_index(self, index: int) -> dict[str, Any] | None:
        """Get a search result by index (1-based for user convenience)."""
        if 0 < index <= len(self.last_search_results):
            return self.last_search_results[index - 1]
        return None


# Create a single instance of the context
context = NixOSContext()


def error(msg: str, code: str = "ERROR", suggestions: list[str] | None = None) -> str:
    """Format error as plain text with helpful suggestions."""
    # Ensure msg is always a string, even if empty
    msg = str(msg) if msg is not None else ""

    output = [f"Error ({code}): {msg}"]

    if suggestions:
        output.append("\nTry:")
        for suggestion in suggestions:
            output.append(f"• {suggestion}")

    return "\n".join(output)


def get_closest_matches(query: str, candidates: list[str], max_results: int = 3) -> list[str]:
    """Find closest matches using simple string similarity."""
    query_lower = query.lower()
    scored_candidates = []

    for candidate in candidates:
        candidate_lower = candidate.lower()
        score = 0

        # Exact match
        if query_lower == candidate_lower:
            score = 100
        # Starts with query
        elif candidate_lower.startswith(query_lower):
            score = 80
        # Query is substring
        elif query_lower in candidate_lower:
            score = 60
        # Candidate starts with query (partial)
        elif len(query_lower) >= 3 and candidate_lower.startswith(query_lower[:3]):
            score = 40
        # Common prefix
        else:
            common_len = 0
            for i, (c1, c2) in enumerate(zip(query_lower, candidate_lower, strict=False)):
                if c1 == c2:
                    common_len = i + 1
                else:
                    break
            if common_len >= 2:
                score = 20 + (common_len * 5)

        if score > 0:
            scored_candidates.append((score, candidate))

    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return [candidate for _, candidate in scored_candidates[:max_results]]


def get_did_you_mean_suggestions(
    query: str, search_type: str = "packages", closest_matches: list[str] | None = None
) -> list[str]:
    """Generate helpful 'did you mean' suggestions for failed searches."""
    suggestions = []

    # If we have closest matches from actual search, use those first
    if closest_matches:
        suggestions.append("Did you mean:")
        for match in closest_matches[:3]:
            if search_type == "packages":
                suggestions.append(f"  • search(query='{match}')")
            elif search_type == "options":
                suggestions.append(f"  • show(name='{match}', type='option')")
        suggestions.append("")

    # Common misspellings and variations
    common_variations = {
        "neovim": ["nvim", "vim", "neovim-unwrapped"],
        "firefox": ["firefox-esr", "firefox-bin", "firefox-devedition"],
        "postgres": ["postgresql", "postgresql_15", "postgresql_16"],
        "node": ["nodejs", "nodejs_20", "nodejs_18"],
        "python": ["python3", "python311", "python312", "python3Packages"],
        "ruby": ["ruby_3_2", "ruby_3_1", "rubyPackages"],
        "java": ["openjdk", "jdk", "temurin-bin", "jre"],
        "docker": ["docker-compose", "podman", "docker-client"],
        "vscode": ["vscodium", "code-server", "vscode-fhs"],
        "gcc": ["gcc13", "gcc12", "clang", "gccStdenv"],
        "vim": ["neovim", "vim-full", "gvim"],
        "emacs": ["emacs-gtk", "emacs-nox", "emacs29"],
        "nginx": ["nginx-mainline", "nginxStable", "openresty"],
        "mysql": ["mariadb", "mysql80", "percona-server"],
        "chrome": ["chromium", "google-chrome", "brave"],
    }

    # Check for close matches in common variations
    query_lower = query.lower()
    for key, alternatives in common_variations.items():
        if query_lower in key or key in query_lower:
            if not closest_matches:  # Only if we don't have actual matches
                suggestions.append("Common alternatives:")
                for alt in alternatives[:3]:
                    suggestions.append(f"  • search(query='{alt}')")
            break

    # Type-specific suggestions - always add these
    if search_type == "packages":
        suggestions.extend(
            [
                "",
                "Other search strategies:",
                f"  • search(query='{query}', search_type='programs') - if looking for a command",
                f"  • which(package_name='{query}') - find package providing this command",
                f"  • search(query='{query[:3]}') - try with first 3 letters"
                if len(query) > 3
                else "  • Try shorter search terms",
            ]
        )
    elif search_type == "options":
        suggestions.extend(
            [
                "",
                "Option search tips:",
                "  • Use dot notation: 'services.nginx' not 'nginx services'",
                f"  • Try the service name: search(query='{query.split()[0]}', search_type='options')",
                f"  • Browse by prefix: hm_browse(option_prefix='{query}')",
            ]
        )
    elif search_type == "programs":
        suggestions.extend(
            [
                "",
                "Program search tips:",
                f"  • which(package_name='{query}') - for exact command match",
                f"  • search(query='{query}', search_type='packages') - to find packages",
                "  • Check common aliases (python→python3, node→nodejs)",
            ]
        )

    return suggestions


def format_output(sections: dict[str, str | list[str]], style: str = "normal") -> str:
    """Format output based on user preference for verbosity."""
    if style == "concise":
        # Concise mode: skip NEXT STEPS and minimize formatting
        output = []
        for section, content in sections.items():
            if section == "NEXT STEPS":
                continue  # Skip in concise mode

            if isinstance(content, list):
                output.extend(content)
            else:
                output.append(content)

        return "\n".join(output)

    # Normal mode: full formatting with sections
    output = []
    for section, content in sections.items():
        if section == "header":
            output.append(str(content))
            output.append("=" * len(str(content)))
        elif section == "results":
            if isinstance(content, list):
                output.extend(content)
            else:
                output.append(content)
        elif section == "NEXT STEPS":
            output.append("")
            output.append("NEXT STEPS:")
            output.append("-----------")
            if isinstance(content, list):
                output.extend(content)
            else:
                output.append(content)

    return "\n".join(output)


def format_tool_output(
    tool_name: str, action: str, content: list[str], next_steps: list[str], style: str = "normal"
) -> str:
    """
    Standardized output format for all tools.

    Format:
    TOOL: ACTION
    ━━━━━━━━━━━━

    {content}

    NEXT STEPS:
    ───────────
    {next_steps}
    """
    if style == "concise":
        # In concise mode, skip headers and next steps
        return "\n".join(content)

    output = []

    # Header
    header = f"{tool_name}: {action}"
    output.append(header)
    output.append("━" * len(header))
    output.append("")

    # Main content
    output.extend(content)

    # Next steps (if any)
    if next_steps:
        output.append("")
        output.append("NEXT STEPS:")
        output.append("───────────")
        output.extend(next_steps)

    return "\n".join(output)


def get_search_next_steps(query: str, search_type: str, results: list[dict[str, Any]], channel: str) -> list[str]:
    """Generate context-aware next steps for search results."""
    next_steps = []

    if not results:
        # No results found
        next_steps.extend(
            [
                f"• Try a broader search term: search(query='{query[:3]}', search_type='{search_type}')",
                f"• Search in {'unstable' if channel != 'unstable' else 'stable'} channel",
                "• Check alternate spellings or related terms",
            ]
        )
        if search_type == "packages":
            next_steps.append(f"• Try: which(command='{query}') - if looking for a command")
    elif len(results) == 1:
        # Single result
        src = results[0].get("_source", {})
        if search_type == "packages":
            name = src.get("package_pname", "")
            next_steps.extend(
                [
                    f"• Get details: show(name='{name}')",
                    f"• Install it: install(package_name='{name}')",
                    f"• Check versions: versions(package_name='{name}')",
                ]
            )
        elif search_type == "options":
            name = src.get("option_name", "")
            next_steps.extend(
                [
                    f"• Get details: show(name='{name}', type='option')",
                    "• Add to configuration.nix",
                    "• Search related options",
                ]
            )
    else:
        # Multiple results
        if search_type == "packages":
            # Use context to get first package name
            first_pkg = ""
            if "package_groups" in locals() and locals()["package_groups"]:
                first_pkg = list(locals()["package_groups"].keys())[0]
            elif results:
                first_pkg = results[0].get("_source", {}).get("package_pname", "")

            if first_pkg:
                next_steps.extend(
                    [
                        f"• Get details: show(name='{first_pkg}')",
                        "• Or use index: show(1) - for first result",
                        f"• Compare versions: compare(package_name='{first_pkg}')",
                    ]
                )
        elif search_type == "options":
            first_opt = results[0].get("_source", {}).get("option_name", "")
            next_steps.extend(
                [
                    f"• Get details: show(name='{first_opt}', type='option')",
                    "• Refine search with more specific terms",
                    "• Browse related options",
                ]
            )

    return next_steps


def get_channels() -> dict[str, str]:
    """Get current channel mappings (cached and resolved)."""
    return channel_cache.get_resolved()


def validate_channel(channel: str) -> bool:
    """Validate if a channel exists and is accessible."""
    channels = get_channels()
    if channel in channels:
        index = channels[channel]
        try:
            resp = requests.post(
                f"{NIXOS_API}/{index}/_count", json={"query": {"match_all": {}}}, auth=NIXOS_AUTH, timeout=5
            )
            return resp.status_code == 200 and resp.json().get("count", 0) > 0
        except Exception:
            return False
    return False


def get_channel_suggestions(invalid_channel: str) -> str:
    """Get helpful suggestions for invalid channels."""
    channels = get_channels()
    available = list(channels.keys())
    suggestions = []

    # Find similar channel names
    invalid_lower = invalid_channel.lower()
    for channel in available:
        if invalid_lower in channel.lower() or channel.lower() in invalid_lower:
            suggestions.append(channel)

    if not suggestions:
        # Fallback to most common channels
        common = ["unstable", "stable", "beta"]
        # Also include version numbers
        version_channels = [ch for ch in available if "." in ch and ch.replace(".", "").isdigit()]
        common.extend(version_channels[:2])  # Add up to 2 version channels
        suggestions = [ch for ch in common if ch in available]
        if not suggestions:
            suggestions = available[:4]  # First 4 available

    return f"Available channels: {', '.join(suggestions)}"


def es_query(index: str, query: dict[str, Any], size: int = 20) -> list[dict[str, Any]]:
    """Execute Elasticsearch query."""
    try:
        resp = requests.post(
            f"{NIXOS_API}/{index}/_search", json={"query": query, "size": size}, auth=NIXOS_AUTH, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        # Handle malformed responses gracefully
        if isinstance(data, dict) and "hits" in data:
            hits = data.get("hits", {})
            if isinstance(hits, dict) and "hits" in hits:
                return list(hits.get("hits", []))
        return []
    except requests.Timeout as exc:
        raise APIError("API error: Connection timed out") from exc
    except requests.HTTPError as exc:
        raise APIError(f"API error: {str(exc)}") from exc
    except Exception as exc:
        raise APIError(f"API error: {str(exc)}") from exc


def parse_html_options(url: str, query: str = "", prefix: str = "", limit: int = 100) -> list[dict[str, str]]:
    """Parse options from HTML documentation."""
    try:
        resp = requests.get(url, timeout=30)  # Increase timeout for large docs
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        options = []

        # Get all dt elements
        dts = soup.find_all("dt")

        for dt in dts:
            # Get option name
            name = ""
            if "home-manager" in url:
                # Home Manager uses anchor IDs like "opt-programs.git.enable"
                anchor = dt.find("a", id=True)
                if anchor:
                    anchor_id = anchor.get("id", "")
                    # Remove "opt-" prefix and convert underscores
                    if anchor_id.startswith("opt-"):
                        name = anchor_id[4:]  # Remove "opt-" prefix
                        # Convert _name_ placeholders back to <name>
                        name = name.replace("_name_", "<name>")
                else:
                    # Fallback to text content
                    name_elem = dt.find(string=True, recursive=False)
                    if name_elem:
                        name = name_elem.strip()
                    else:
                        name = dt.get_text(strip=True)
            else:
                # Darwin and fallback - use text content
                name = dt.get_text(strip=True)

            # Skip if it doesn't look like an option (must contain a dot)
            # But allow single-word options in some cases
            if "." not in name and len(name.split()) > 1:
                continue

            # Filter by query or prefix
            if query and query.lower() not in name.lower():
                continue
            if prefix and not (name.startswith(prefix + ".") or name == prefix):
                continue

            # Find the corresponding dd element
            dd = dt.find_next_sibling("dd")
            if dd:
                # Extract description (first p tag or direct text)
                desc_elem = dd.find("p")
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                else:
                    # Get first text node, handle None case
                    text = dd.get_text(strip=True)
                    description = text.split("\n")[0] if text else ""

                # Extract type info - look for various patterns
                type_info = ""
                # Pattern 1: <span class="term">Type: ...</span>
                type_elem = dd.find("span", class_="term")
                if type_elem and "Type:" in type_elem.get_text():
                    type_info = type_elem.get_text(strip=True).replace("Type:", "").strip()
                # Pattern 2: Look for "Type:" in text
                elif "Type:" in dd.get_text():
                    text = dd.get_text()
                    type_start = text.find("Type:") + 5
                    type_end = text.find("\n", type_start)
                    if type_end == -1:
                        type_end = len(text)
                    type_info = text[type_start:type_end].strip()

                options.append(
                    {
                        "name": name,
                        "description": description[:200] if len(description) > 200 else description,
                        "type": type_info,
                    }
                )

                if len(options) >= limit:
                    break

        return options
    except Exception as exc:
        raise DocumentParseError(f"Failed to fetch docs: {str(exc)}") from exc


@mcp.tool()
async def search(
    query: Annotated[
        str,
        Field(
            description="Package/option name or keyword. Supports partial matches. "
            "Examples: 'firefox', 'python3', 'networking.firewall'"
        ),
    ],
    search_type: Annotated[
        str,
        Field(
            description="What to search: 'packages' (like nix search), 'options' "
            "(like man configuration.nix), 'programs', or 'flakes'"
        ),
    ] = "packages",
    limit: Annotated[int, Field(description="Maximum number of results to return (1-100)", ge=1, le=100)] = 20,
    channel: Annotated[
        str,
        Field(description="NixOS channel to search in. Use 'stable' for current stable, 'unstable' for latest"),
    ] = "unstable",
    concise: Annotated[
        bool,
        Field(description="Return minimal output without tutorials and next steps. Good for experienced users."),
    ] = False,
) -> str:
    """Find packages, configuration options, programs, or flakes instantly.

    WHAT IT DOES:
    • Searches NixOS packages by name or description
    • Finds configuration options (services.nginx.enable, etc)
    • Discovers which package provides a command/program
    • Searches flakes from both NixOS index and GitHub (sorted by stars)
    • Searches community flakes

    USE THIS TO:
    • Find packages: search("firefox")
    • Find options: search("firewall", search_type="options")
    • Find commands: search("gcc", search_type="programs")
    • Search flakes: search("home-manager", search_type="flakes")

    Args:
        query: Package/option name or keyword. Supports partial matches.
               Examples: 'firefox', 'python3', 'networking.firewall'
        search_type: What to search: 'packages' (like nix search), 'options' (like man configuration.nix),
                     'programs', or 'flakes'
        limit: Maximum number of results to return (1-100)
        channel: NixOS channel to search in. Use 'stable' for current stable, 'unstable' for latest

    Returns:
        Plain text results with bullet points or error message
    """
    if search_type not in ["packages", "options", "programs", "flakes"]:
        return error(
            f"Invalid type '{search_type}'",
            "INVALID_TYPE",
            [
                "search(query='...', search_type='packages') - search for packages",
                "search(query='...', search_type='options') - search for configuration options",
                "search(query='...', search_type='programs') - find which package provides a command",
                "search(query='...', search_type='flakes') - search flake packages",
            ],
        )
    channels = get_channels()
    if channel not in channels:
        channel_suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {channel_suggestions}")
    if not 1 <= limit <= 100:
        return error(
            "Limit must be 1-100",
            "INVALID_LIMIT",
            [
                "search(query='...', limit=20) - get 20 results",
                "search(query='...', limit=50) - get more results",
                "search(query='...', limit=100) - get maximum results",
            ],
        )

    # Redirect flakes to dedicated function
    if search_type == "flakes":
        return await _flake_search_impl(query, limit, channel)

    try:
        # Build query with correct field names
        if search_type == "packages":
            q = {
                "bool": {
                    "must": [{"term": {"type": "package"}}],
                    "should": [
                        {"match": {"package_pname": {"query": query, "boost": 3}}},
                        {"match": {"package_description": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        elif search_type == "options":
            # Use wildcard for option names to handle hierarchical names like services.nginx.enable
            q = {
                "bool": {
                    "must": [{"term": {"type": "option"}}],
                    "should": [
                        {"wildcard": {"option_name": f"*{query}*"}},
                        {"match": {"option_description": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        else:  # programs
            q = {
                "bool": {
                    "must": [{"term": {"type": "package"}}],
                    "should": [
                        {"match": {"package_programs": {"query": query, "boost": 2}}},
                        {"match": {"package_pname": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }

        hits = es_query(channels[channel], q, limit)

        # Update context with search results
        context.update_search_context(query, search_type, hits)
        context.last_channel = channel

        # Format results as plain text
        if not hits:
            # Try to find closest matches for better suggestions
            closest_matches = []
            if search_type == "packages":
                # Do a broader search to find similar names
                fuzzy_q = {
                    "bool": {
                        "must": [{"term": {"type": "package"}}],
                        "should": [
                            {"prefix": {"package_pname": query[:3] if len(query) >= 3 else query}},
                            {"wildcard": {"package_pname": f"*{query}*"}},
                            {"fuzzy": {"package_pname": {"value": query, "fuzziness": "AUTO"}}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
                fuzzy_hits = es_query(channels[channel], fuzzy_q, 10)
                if fuzzy_hits:
                    # Extract unique package names
                    seen_names = set()
                    for hit in fuzzy_hits:
                        name = hit.get("_source", {}).get("package_pname", "")
                        if name and name not in seen_names:
                            seen_names.add(name)
                    closest_matches = get_closest_matches(query, list(seen_names), 5)

            suggestions = get_did_you_mean_suggestions(query, search_type, closest_matches)
            return error(f"No {search_type} found matching '{query}'", "NOT_FOUND", suggestions)

        results = []
        results.append(f"Query: '{query}'")
        results.append(f"Channel: {channel}")

        # Adjust count for grouped packages
        if search_type == "packages":
            # Count will be done after grouping
            pass  # Will update below
        else:
            results.append(f"Results: {len(hits)} {search_type} found")
        results.append("")

        # Track programs found for NEXT STEPS logic
        programs_found = []

        # For packages, group by package name to avoid duplicates
        if search_type == "packages":
            # Group packages by name
            package_groups = {}
            for hit in hits:
                src = hit.get("_source", {})
                name = src.get("package_pname", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")

                if name not in package_groups:
                    package_groups[name] = {"versions": [], "description": desc, "latest_version": version}
                package_groups[name]["versions"].append(version)

                # Keep the longest/best description
                if desc and len(desc) > len(package_groups[name]["description"] or ""):
                    package_groups[name]["description"] = desc

            # Add result count for packages
            unique_count = len(package_groups)
            if unique_count < len(hits):
                results.insert(-1, f"Results: {unique_count} unique packages ({len(hits)} versions total)")
            else:
                results.insert(-1, f"Results: {unique_count} packages found")

            # Display grouped results with relevance indicators
            # First, let's check if exact matches exist
            exact_matches = []
            partial_matches = []
            other_matches = []

            for name, info in package_groups.items():
                if name.lower() == query.lower():
                    exact_matches.append((name, info))
                elif name.lower().startswith(query.lower()):
                    partial_matches.append((name, info))
                else:
                    other_matches.append((name, info))

            # Sort each group and combine
            all_results = exact_matches + partial_matches + other_matches

            for _idx, (name, info) in enumerate(all_results):
                versions = info["versions"]
                # Add relevance indicator
                relevance = ""
                if (name, info) in exact_matches:
                    relevance = " ⭐"  # Exact match
                elif (name, info) in partial_matches:
                    relevance = " ✓"  # Starts with query

                if len(versions) == 1:
                    results.append(f"• {name} ({versions[0]}){relevance}")
                else:
                    # Show latest and count
                    results.append(f"• {name}{relevance}")
                    results.append(
                        f"   Versions: {', '.join(versions[:3])}"
                        + (f" ... ({len(versions)} total)" if len(versions) > 3 else "")
                    )

                desc = info["description"]
                if desc:
                    # Truncate long descriptions
                    if len(desc) > 80:
                        desc = desc[:77] + "..."
                    results.append(f"   {desc}")
                results.append("")
        else:
            # Non-package results (options, programs)
            for hit in hits:
                src = hit.get("_source", {})
                if search_type == "options":
                    name = src.get("option_name", "")
                    opt_type = src.get("option_type", "")
                    desc = src.get("option_description", "")
                    # Strip HTML tags from description
                    if desc and "<rendered-html>" in desc:
                        # Remove outer rendered-html tags
                        desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                        # Remove common HTML tags
                        desc = re.sub(r"<[^>]+>", "", desc)
                        desc = desc.strip()
                    results.append(f"• {name}")
                    if opt_type:
                        results.append(f"   Type: {opt_type}")
                    if desc:
                        # Truncate long descriptions
                        if len(desc) > 80:
                            desc = desc[:77] + "..."
                        results.append(f"   {desc}")
                    results.append("")
                else:  # programs
                    programs = src.get("package_programs", [])
                    pkg_name = src.get("package_pname", "")

                    # Check if query matches any program exactly (case-insensitive)
                    query_lower = query.lower()
                    matched_programs = [p for p in programs if p.lower() == query_lower]

                    for prog in matched_programs:
                        results.append(f"• {prog} -> provided by {pkg_name}")
                        results.append("")
                        programs_found.append((prog, pkg_name))

        # Generate context-aware next steps
        next_steps = get_search_next_steps(query, search_type, hits, channel)

        # Special handling for programs search
        if search_type == "programs" and programs_found:
            first_pkg = programs_found[0][1]
            next_steps = [
                f'• Try it now: try_package(package_name="{first_pkg}")',
                f'• Get details: show(name="{first_pkg}")',
                f'• Install permanently: install(package_name="{first_pkg}")',
            ]

        # Use standardized formatting
        style = "concise" if concise else "normal"
        action = f"{search_type} matching '{query}'"
        return format_tool_output("SEARCH", action, results, next_steps, style)

    except Exception as e:
        return error(str(e))


@mcp.tool()
async def show(
    name: Annotated[
        str | None,
        Field(
            description="Package/option name, or index from search results (1, 2, etc). "
            "If omitted, uses first result from last search."
        ),
    ] = None,
    type: Annotated[
        str, Field(description="Type to show: 'package' (nix package) or 'option' (NixOS configuration option)")
    ] = "package",
    channel: Annotated[
        str, Field(description="NixOS channel. Use 'stable' for current stable, 'unstable' for latest")
    ] = "unstable",
    concise: Annotated[bool, Field(description="Return minimal output without detailed sections")] = False,
) -> str:  # pylint: disable=redefined-builtin
    """Get detailed information about any package or option.

    WHAT IT DOES:
    • Shows package version, description, homepage, license
    • Displays option type, default value, and description
    • Works with index numbers from search results
    • No derivation evaluation needed

    USE THIS TO:
    • Check package details: show("firefox")
    • View option info: show("services.nginx.enable", type="option")
    • Use search results: show("2") - shows 2nd result from last search

    Args:
        name: Exact package or option name. Examples: 'firefox' (package), 'services.nginx.enable' (option)
        type: Type of lookup - "package" or "option"
        channel: NixOS channel to search in. Use 'stable' for current stable, 'unstable' for latest

    Returns:
        Plain text details about the package/option or error message
    """
    # Handle context-aware name resolution
    actual_name = name
    if name is None:
        # Try to get from context
        actual_name = context.get_recent_package()
        if not actual_name:
            return error(
                "No package/option name provided and no recent search results",
                "NO_CONTEXT",
                [
                    "search(query='firefox') - search for a package first",
                    "show(name='firefox') - or provide explicit name",
                ],
            )
    elif name.isdigit():
        # Handle index-based lookup (1, 2, 3, etc)
        index = int(name)
        result = context.get_result_by_index(index)
        if result:
            src = result.get("_source", {})
            if context.last_search_type == "packages":
                actual_name = src.get("package_pname", "")
            elif context.last_search_type == "options":
                actual_name = src.get("option_name", "")
                type = "option"  # Override type for options
        else:
            return error(
                f"Invalid index {index}. Last search had {len(context.last_search_results)} results",
                "INVALID_INDEX",
                [f"show(1) - use index 1 to {len(context.last_search_results)}"],
            )

    info_type = type  # Avoid shadowing built-in
    if info_type not in ["package", "option"]:
        return error(
            "Type must be 'package' or 'option'",
            "INVALID_TYPE",
            [
                "show(name='...', type='package') - show package details",
                "show(name='...', type='option') - show configuration option details",
            ],
        )
    channels = get_channels()
    if channel not in channels:
        channel_suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {channel_suggestions}")

    try:
        # Exact match query with correct field names
        field = "package_pname" if info_type == "package" else "option_name"
        query = {"bool": {"must": [{"term": {"type": info_type}}, {"term": {field: actual_name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            # Try to find similar packages/options
            closest_matches = []
            if info_type == "package":
                # Search for similar packages
                wildcard_query = {
                    "bool": {
                        "must": [{"term": {"type": "package"}}, {"wildcard": {"package_pname": f"*{actual_name}*"}}]
                    }
                }
                similar_hits = es_query(channels[channel], wildcard_query, 10)
                if similar_hits:
                    seen_names = set()
                    for hit in similar_hits:
                        name = hit.get("_source", {}).get("package_pname", "")
                        if name and name not in seen_names:
                            seen_names.add(name)
                    closest_matches = get_closest_matches(actual_name or "", list(seen_names), 3)

            suggestions = get_did_you_mean_suggestions(actual_name or "", info_type + "s", closest_matches)
            # Add type-specific suggestion
            if info_type == "package":
                suggestions.insert(0, f'search(query="{actual_name}") - to find similar packages')
            else:
                suggestions.insert(0, f'Use partial option name: show(name="services.{actual_name}")')
            return error(f"{info_type.capitalize()} '{actual_name}' not found", "NOT_FOUND", suggestions)

        src = hits[0].get("_source", {})

        if info_type == "package":
            pkg_name = src.get("package_pname", "")
            version = src.get("package_pversion", "")
            desc = src.get("package_description", "")

            # Build structured output
            output = []
            output.append(f"Name: {pkg_name}")
            output.append(f"Version: {version}")
            output.append(f"Channel: {channel}")
            if desc:
                output.append(f"Description: {desc}")

            homepage = src.get("package_homepage", [])
            if homepage:
                if isinstance(homepage, list):
                    homepage = homepage[0] if homepage else ""
                output.append(f"Homepage: {homepage}")

            licenses = src.get("package_license_set", [])
            if licenses:
                output.append(f"License: {', '.join(licenses)}")

            # Context-aware next steps
            next_steps = []

            # Check if package has multiple versions in our context
            has_multiple_versions = False
            if context.last_search_results:
                pkg_names = [r.get("_source", {}).get("package_pname", "") for r in context.last_search_results]
                has_multiple_versions = pkg_names.count(pkg_name) > 1

            next_steps.extend(
                [
                    f"• Try it: nix-shell -p {pkg_name}",
                    f"• Install: install(package_name='{pkg_name}')",
                ]
            )

            if has_multiple_versions:
                next_steps.append(f"• Check versions: versions(package_name='{pkg_name}')")

            next_steps.append(f"• Compare channels: compare(package_name='{pkg_name}')")

            style = "concise" if concise else "normal"
            action = f"package '{pkg_name}'"
            return format_tool_output("SHOW", action, output, next_steps, style)

        # Option type
        opt_name = src.get("option_name", "")
        info = []
        info.append(f"Option: {opt_name}")

        opt_type = src.get("option_type", "")
        if opt_type:
            info.append(f"Type: {opt_type}")

        desc = src.get("option_description", "")
        if desc:
            # Strip HTML tags from description
            if "<rendered-html>" in desc:
                desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                desc = re.sub(r"<[^>]+>", "", desc)
                desc = desc.strip()
            info.append(f"Description: {desc}")

        default = src.get("option_default", "")
        if default:
            info.append(f"Default: {default}")

        example = src.get("option_example", "")
        if example:
            info.append(f"Example: {example}")

        # Context-aware next steps for options
        next_steps = []

        # Extract service/program name if possible
        prefix = opt_name.split(".")[0] if "." in opt_name else opt_name

        next_steps.extend(
            [
                "• Add to your configuration.nix",
                f"• Find related: search(query='{prefix}', search_type='options')",
                "• Test with nixos-rebuild dry-build",
            ]
        )

        style = "concise" if concise else "normal"
        action = f"option '{opt_name}'"
        return format_tool_output("SHOW", action, info, next_steps, style)

    except Exception as e:
        return error(str(e))


@mcp.tool()
async def channels() -> str:
    """See all available NixOS channels and their status.

    WHAT IT DOES:
    • Lists all channels (stable, unstable, version-specific)
    • Shows real-time availability status
    • Displays package/option counts
    • Identifies current stable version

    USE THIS TO:
    • Check available channels: channels()
    • See which version is stable
    • Verify channel availability before searching

    Returns:
        Plain text list showing channel names, versions, and availability
    """
    try:
        # Get resolved channels and available raw data
        configured = get_channels()
        available = channel_cache.get_available()

        # Build content for standardized output
        content = []

        # Show user-friendly channel names
        for name, index in sorted(configured.items()):
            status = "[Available]" if index in available else "[Unavailable]"
            doc_count = available.get(index, "Unknown")

            # Mark stable channel clearly
            label = f"• {name}"
            if name == "stable":
                # Extract version from index
                parts = index.split("-")
                if len(parts) >= 4:
                    version = parts[3]
                    label = f"• {name} (current: {version})"

            content.append(f"{label} -> {index}")
            if index in available:
                content.append(f"  Status: {status} ({doc_count})")
            else:
                content.append(f"  Status: {status}")
            content.append("")

        # Show additional discovered channels not in our mapping
        discovered_only = set(available.keys()) - set(configured.values())
        if discovered_only:
            content.append("Additional available channels:")
            for index in sorted(discovered_only):
                content.append(f"• {index} ({available[index]})")
            content.append("")

        content.append("Note: Channels are dynamically discovered.")
        content.append("'stable' always points to the current stable release.")

        next_steps = [
            '• Use search(channel="<channel>") to search a specific channel',
            '• Use stats(channel="<channel>") to see package counts',
            "• Use compare() to compare package versions across channels",
        ]

        return format_tool_output("CHANNELS", "Available", content, next_steps)
    except Exception as e:
        return error(str(e))


@mcp.tool()
async def stats(
    channel: Annotated[
        str, Field(description="NixOS channel to get stats for. Examples: 'unstable', 'stable', '25.05'")
    ] = "unstable",
) -> str:
    """Get package and option counts for any channel.

    WHAT IT DOES:
    • Shows total packages available
    • Shows total configuration options
    • Provides instant metrics without downloads
    • Works with any valid channel

    USE THIS TO:
    • Check channel size: stats()
    • Compare channels: stats("stable") vs stats("unstable")
    • Verify channel has content before searching

    Args:
        channel: NixOS channel to get stats for (e.g., "unstable", "stable", "25.05")

    Returns:
        Plain text statistics including package/option counts
    """
    channels = get_channels()
    if channel not in channels:
        channel_suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {channel_suggestions}")

    try:
        index = channels[channel]
        url = f"{NIXOS_API}/{index}/_count"

        # Get counts with error handling
        try:
            pkg_resp = requests.post(url, json={"query": {"term": {"type": "package"}}}, auth=NIXOS_AUTH, timeout=10)
            pkg_resp.raise_for_status()
            pkg_count = pkg_resp.json().get("count", 0)
        except Exception:
            pkg_count = 0

        try:
            opt_resp = requests.post(url, json={"query": {"term": {"type": "option"}}}, auth=NIXOS_AUTH, timeout=10)
            opt_resp.raise_for_status()
            opt_count = opt_resp.json().get("count", 0)
        except Exception:
            opt_count = 0

        if pkg_count == 0 and opt_count == 0:
            return error(
                "Failed to retrieve statistics",
                "FETCH_ERROR",
                [
                    "channels() - check channel availability",
                    "stats(channel='unstable') - try a different channel",
                    "search(channel='unstable') - test channel connectivity",
                ],
            )

        # Format results using standardized output
        content = [
            f"Channel: {channel}",
            f"• Packages: {pkg_count:,}",
            f"• Options: {opt_count:,}",
            "",
            f"Total indexed items: {pkg_count + opt_count:,}",
        ]

        next_steps = [
            f"• Find packages: search(query='package', channel='{channel}')",
            f"• Browse options: search(query='services', search_type='options', channel='{channel}')",
            "• See all channels: channels()",
            f'• Compare with: stats(channel="{"unstable" if channel == "stable" else "stable"}")',
        ]

        return format_tool_output("STATS", channel, content, next_steps)

    except Exception as e:
        return error(str(e))


@mcp.tool(name="hm_search")
async def hm_search(
    query: Annotated[
        str, Field(description="Search query for Home Manager options. Examples: 'git', 'vim', 'firefox'")
    ],
    limit: Annotated[int, Field(description="Maximum number of results to return (1-100)", ge=1, le=100)] = 20,
) -> str:
    """Search Home Manager configuration options.

    WHAT IT DOES:
    • Searches all Home Manager options
    • Finds by name or description
    • Shows option types and descriptions
    • Works without Home Manager installed

    USE THIS TO:
    • Configure programs: hm_search("git")
    • Find settings: hm_search("vim plugins")
    • Discover options: hm_search("shell")

    Args:
        query: Option name or keyword. Examples: 'git', 'vim', 'programs.firefox'
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        Plain text list of matching options with name, type, and description
    """
    if not 1 <= limit <= 100:
        return error(
            "Limit must be 1-100",
            "INVALID_LIMIT",
            [
                "hm_search(query='...', limit=20) - get 20 results",
                "hm_search(query='...', limit=50) - get more results",
                "hm_search(query='...', limit=100) - get maximum results",
            ],
        )

    try:
        options = parse_html_options(HOME_MANAGER_URL, query, "", limit)

        if not options:
            return f"No Home Manager options found matching '{query}'"

        results = []
        results.append(f"Found {len(options)} Home Manager options matching '{query}':\n")

        for opt in options:
            results.append(f"• {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")

        # Add helpful next steps
        results.append("NEXT STEPS:")
        results.append("━" * 11)
        if len(options) > 0:
            first_opt = options[0]["name"]
            results.append(f'• Use hm_show(name="{first_opt}") for full details')
            # Extract prefix for browsing
            prefix = first_opt.split(".")[0] if "." in first_opt else first_opt
            results.append(f'• Use hm_browse(option_prefix="{prefix}") to explore related options')
            results.append("• Add to your home.nix to configure")
            results.append("• Use hm_options() to see all categories")
        else:
            results.append(f'• Try broader search: hm_search(query="{query[:3]}", limit=50)')
            results.append("• Browse categories: hm_options()")
            results.append(f'• Try searching for packages instead: search(query="{query}")')
            results.append(f'• Check if this is a Darwin option: darwin_search(query="{query}")')

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool(name="hm_show")
async def hm_show(
    name: Annotated[
        str,
        Field(description="Exact Home Manager option name. Examples: 'programs.git.enable', 'services.dunst.enable'"),
    ],
) -> str:
    """Get complete details for a Home Manager option.

    WHAT IT DOES:
    • Shows option type and description
    • Displays default values if available
    • Requires exact option name
    • Suggests alternatives if not found

    USE THIS TO:
    • View option details: hm_show("programs.git.enable")
    • Check types: hm_show("programs.vim.plugins")
    • Get configuration help: hm_show("home.file")

    Args:
        name: Exact option name. Must match exactly. Example: 'programs.git.enable' not just 'git.enable'

    Returns:
        Plain text with option details (name, type, description) or error with suggestions
    """
    try:
        # First try the basic search to check if option exists
        options = parse_html_options(HOME_MANAGER_URL, name, "", 100)

        # Check for exact match in parsed options
        exact_match = None
        for opt in options:
            if opt["name"] == name:
                exact_match = opt
                break

        # If found, try enhanced parsing for more details
        if exact_match:
            # Try to get more details from full HTML
            try:
                resp = requests.get(HOME_MANAGER_URL, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Find the specific option by its anchor ID
                anchor_id = f"opt-{name.replace('<name>', '_name_')}"
                anchor = soup.find("a", id=anchor_id)

                if anchor:
                    # Found the anchor, get its parent dt and next dd
                    dt = anchor.find_parent("dt")
                    if dt:
                        dd = dt.find_next_sibling("dd")
                        if dd and hasattr(dd, "find_all"):  # Ensure dd is a Tag, not NavigableString
                            info = []
                            info.append(f"Option: {name}")

                            # Extract all available information
                            # First, clean up any HTML tags from content
                            for tag in dd.find_all("span", class_="filename"):
                                tag.decompose()  # Remove file references
                            for tag in dd.find_all("a", class_="filename"):
                                tag.decompose()  # Remove file references

                            content = dd.get_text("\n", strip=True)
                            lines = content.split("\n")

                            # Parse structured information
                            current_section = None
                            type_info = ""
                            default_value = ""
                            example_value = ""
                            description_lines = []

                            for i, line in enumerate(lines):
                                line_stripped = line.strip()
                                if line_stripped.startswith("Type:"):
                                    type_info = line_stripped[5:].strip()
                                    current_section = "type"
                                elif line_stripped.startswith("Default:"):
                                    default_value = line_stripped[8:].strip()
                                    current_section = "default"
                                    # If empty, capture next non-empty line preserving some formatting
                                    if not default_value and i + 1 < len(lines):
                                        for j in range(i + 1, len(lines)):
                                            next_line = lines[j].strip()
                                            if next_line and not any(
                                                next_line.startswith(p)
                                                for p in ["Type:", "Default:", "Example:", "Declared"]
                                            ):
                                                default_value = next_line
                                                break
                                            elif any(
                                                next_line.startswith(p)
                                                for p in ["Type:", "Default:", "Example:", "Declared"]
                                            ):
                                                break
                                elif line_stripped.startswith("Example:"):
                                    example_value = line_stripped[8:].strip()
                                    current_section = "example"
                                    # If empty, capture next non-empty line preserving some formatting
                                    if not example_value and i + 1 < len(lines):
                                        for j in range(i + 1, len(lines)):
                                            next_line = lines[j].strip()
                                            if next_line and not any(
                                                next_line.startswith(p)
                                                for p in ["Type:", "Default:", "Example:", "Declared"]
                                            ):
                                                example_value = next_line
                                                break
                                            elif any(
                                                next_line.startswith(p)
                                                for p in ["Type:", "Default:", "Example:", "Declared"]
                                            ):
                                                break
                                elif line_stripped.startswith("Declared"):
                                    current_section = None  # Stop capturing
                                elif line_stripped and not any(
                                    line_stripped.startswith(p) for p in ["Type:", "Default:", "Example:"]
                                ):
                                    # Handle multiline values - but only continue if we already started capturing
                                    # Skip if we just captured this line as the initial value
                                    if (
                                        current_section == "default"
                                        and default_value
                                        and not default_value.endswith(line_stripped)
                                    ):
                                        # Only add if it looks like a continuation (e.g., for multi-line JSON)
                                        if not default_value.endswith("}") and (
                                            line_stripped.startswith("{")
                                            or line_stripped.startswith("}")
                                            or ":" in line_stripped
                                        ):
                                            default_value += " " + line_stripped
                                    elif (
                                        current_section == "example"
                                        and example_value
                                        and not example_value.endswith(line_stripped)
                                    ):
                                        # Only add if it looks like a continuation
                                        if not example_value.endswith("}") and (
                                            line_stripped.startswith("{")
                                            or line_stripped.startswith("}")
                                            or ":" in line_stripped
                                            or "=" in line_stripped
                                        ):
                                            example_value += " " + line_stripped
                                    elif current_section is None or current_section == "description":
                                        description_lines.append(line_stripped)
                                        current_section = "description"

                            # Build formatted output
                            if type_info:
                                info.append(f"Type: {type_info}")

                            if description_lines:
                                desc = " ".join(description_lines[:3])  # First few lines
                                # Remove any XML-like tags (except allowed ones)
                                import re

                                desc = re.sub(r"<(?!(?:command|package|tool)>)[^>]+>", "", desc)
                                if len(desc) > 200:
                                    desc = desc[:197] + "..."
                                info.append(f"Description: {desc}")

                            if default_value and default_value != "null":
                                info.append(f"Default: {default_value}")

                            if example_value:
                                info.append(f"Example: {example_value}")

                            return "\n".join(info)
            except Exception:
                # If enhanced parsing fails, fall through to basic parsing
                pass

        # If not found by exact match, still show the basic info
        if exact_match:
            info = []
            info.append(f"Option: {name}")
            if exact_match.get("type"):
                info.append(f"Type: {exact_match['type']}")
            if exact_match.get("description"):
                info.append(f"Description: {exact_match['description']}")
            return "\n".join(info)

        # If still not found, check if there are similar options to suggest
        if options:
            suggestions = []
            for opt in options[:5]:  # Show up to 5 suggestions
                if name in opt["name"] or opt["name"].startswith(name + "."):
                    suggestions.append(opt["name"])

            if suggestions:
                return error(
                    f"Option '{name}' not found. Did you mean one of these?\n"
                    + "\n".join(f"  • {s}" for s in suggestions)
                    + f"\n\nTip: Use hm_browse() with prefix '{name}' to browse all options with this prefix.",
                    "NOT_FOUND",
                )

        return error(
            f"Option '{name}' not found.\n" + f"Tip: Use hm_browse('{name}') to browse available options.",
            "NOT_FOUND",
        )

    except Exception as e:
        return error(str(e))


@mcp.tool(name="hm_stats")
async def hm_stats() -> str:
    """Get Home Manager statistics overview.

    WHAT IT DOES:
    • Shows total option count
    • Lists top categories with counts
    • Provides instant metrics
    • No manual counting needed

    USE THIS TO:
    • Get overview: hm_stats()
    • See category distribution
    • Check Home Manager complexity

    Returns:
        Plain text summary with total options, category count, and top 5 categories
    """
    try:
        # Parse all options to get statistics
        options = parse_html_options(HOME_MANAGER_URL, limit=5000)

        if not options:
            return error(
                "Failed to fetch Home Manager statistics",
                "FETCH_ERROR",
                [
                    "hm_search(query='programs') - test Home Manager connectivity",
                    "hm_options() - check if documentation is accessible",
                    "Check network connectivity to Home Manager docs",
                ],
            )

        # Count categories
        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        # Count types
        types: dict[str, int] = {}
        for opt in options:
            opt_type = opt.get("type", "unknown")
            if opt_type:
                # Simplify complex types
                if "null or" in opt_type:
                    opt_type = "nullable"
                elif "list of" in opt_type:
                    opt_type = "list"
                elif "attribute set" in opt_type:
                    opt_type = "attribute set"
                types[opt_type] = types.get(opt_type, 0) + 1

        # Build statistics
        return f"""Home Manager Statistics:
• Total options: {len(options):,}
• Categories: {len(categories)}
• Top categories:
  - programs: {categories.get("programs", 0):,} options
  - services: {categories.get("services", 0):,} options
  - home: {categories.get("home", 0):,} options
  - wayland: {categories.get("wayland", 0):,} options
  - xsession: {categories.get("xsession", 0):,} options"""
    except Exception as e:
        return error(str(e))


@mcp.tool(name="hm_options")
async def hm_options() -> str:
    """List all Home Manager option categories.

    WHAT IT DOES:
    • Shows all top-level categories
    • Displays option count per category
    • Sorted by popularity
    • Perfect starting point for exploration

    USE THIS TO:
    • Browse categories: hm_options()
    • Find configuration areas
    • Start Home Manager setup

    Returns:
        Plain text list of categories sorted alphabetically with option counts
    """
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(HOME_MANAGER_URL, limit=5000)
        categories: dict[str, int] = {}

        for opt in options:
            name = opt["name"]
            # Process option names
            if name and not name.startswith("."):
                if "." in name:
                    cat = name.split(".")[0]
                else:
                    cat = name  # Option without dot is its own category
                # Valid categories should:
                # - Be more than 1 character
                # - Be a valid identifier (allows underscores)
                # - Not be common value words
                # - Match typical nix option category patterns
                if (
                    len(cat) > 1 and cat.isidentifier() and (cat.islower() or cat.startswith("_"))
                ):  # This ensures valid identifier
                    # Additional filtering for known valid categories
                    valid_categories = {
                        "accounts",
                        "dconf",
                        "editorconfig",
                        "fonts",
                        "gtk",
                        "home",
                        "i18n",
                        "launchd",
                        "lib",
                        "manual",
                        "news",
                        "nix",
                        "nixgl",
                        "nixpkgs",
                        "pam",
                        "programs",
                        "qt",
                        "services",
                        "specialisation",
                        "systemd",
                        "targets",
                        "wayland",
                        "xdg",
                        "xresources",
                        "xsession",
                    }
                    # Only include if it's in the known valid list or looks like a typical category
                    if cat in valid_categories or (len(cat) >= 3 and not any(char.isdigit() for char in cat)):
                        categories[cat] = categories.get(cat, 0) + 1

        results = []
        results.append(f"Home Manager option categories ({len(categories)} total):\n")

        # Sort by count descending, then alphabetically
        sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))

        for cat, count in sorted_cats:
            results.append(f"• {cat} ({count} options)")

        return "\n".join(results)

    except Exception as e:
        return error(str(e))


@mcp.tool(name="hm_browse")
async def hm_browse(
    option_prefix: Annotated[
        str, Field(description="Option prefix to browse. Examples: 'programs.git', 'services', 'home.file'")
    ],
) -> str:
    """Browse Home Manager options by prefix.

    WHAT IT DOES:
    • Lists all options under a prefix
    • Shows sub-options and descriptions
    • Enables hierarchical exploration
    • Perfect for discovering related options

    USE THIS TO:
    • Browse programs: hm_browse("programs.git")
    • Explore services: hm_browse("services")
    • Find sub-options: hm_browse("home.file")

    Args:
        option_prefix: Option category or prefix. Examples: 'programs.git', 'services', 'home.file'

    Returns:
        Plain text list of options with the given prefix, including descriptions
    """
    try:
        options = parse_html_options(HOME_MANAGER_URL, "", option_prefix)

        if not options:
            return f"No Home Manager options found with prefix '{option_prefix}'"

        results = []
        results.append(f"Home Manager options with prefix '{option_prefix}' ({len(options)} found):\n")

        for opt in sorted(options, key=lambda x: x["name"]):
            results.append(f"• {opt['name']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool(name="darwin_search")
async def darwin_search(
    query: Annotated[
        str, Field(description="Search query for nix-darwin options. Examples: 'homebrew', 'dock', 'system'")
    ],
    limit: Annotated[int, Field(description="Maximum number of results to return (1-100)", ge=1, le=100)] = 20,
) -> str:
    """Search nix-darwin (macOS) configuration options.

    WHAT IT DOES:
    • Searches macOS-specific options
    • Finds system defaults and services
    • Shows option types and descriptions
    • No nix-darwin installation needed

    USE THIS TO:
    • Configure macOS: darwin_search("dock")
    • Find settings: darwin_search("homebrew")
    • Discover options: darwin_search("system")

    Args:
        query: Option name or keyword. Examples: 'git', 'vim', 'programs.firefox'
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        Plain text list of matching options with name, type, and description
    """
    if not 1 <= limit <= 100:
        return error(
            "Limit must be 1-100",
            "INVALID_LIMIT",
            [
                "darwin_search(query='...', limit=20) - get 20 results",
                "darwin_search(query='...', limit=50) - get more results",
                "darwin_search(query='...', limit=100) - get maximum results",
            ],
        )

    try:
        # Fetch more results to allow for better sorting
        raw_options = parse_html_options(DARWIN_URL, query, "", limit * 3)

        if not raw_options:
            return f"No nix-darwin options found matching '{query}'"

        # Sort by relevance for macOS-specific queries
        query_lower = query.lower()

        def relevance_score(opt: dict[str, str]) -> tuple[int, str]:
            """Score options by relevance, especially for macOS system settings."""
            name = opt["name"].lower()
            score = 0

            # Exact word match in option path gets highest priority
            parts = name.split(".")
            if query_lower in parts:
                score += 100

            # Prioritize system.defaults for macOS settings
            if query_lower == "dock" and name.startswith("system.defaults.dock"):
                score += 50
            elif name.startswith("system.defaults.") and query_lower in name:
                score += 30

            # Lower score for partial matches in unrelated contexts
            if query_lower in name:
                score += 10

            return (-score, name)  # Negative for descending sort

        # Sort and limit results
        sorted_options = sorted(raw_options, key=relevance_score)[:limit]

        results = []
        results.append(f"Found {len(sorted_options)} nix-darwin options matching '{query}':\n")

        for opt in sorted_options:
            results.append(f"• {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")

        # Add helpful next steps
        results.append("NEXT STEPS:")
        results.append("━" * 11)
        if len(sorted_options) > 0:
            first_opt = sorted_options[0]["name"]
            results.append(f'• Use darwin_show(name="{first_opt}") for full details')
            # Extract prefix for browsing
            prefix = first_opt.split(".")[0] if "." in first_opt else first_opt
            results.append(f'• Use darwin_browse(option_prefix="{prefix}") to explore related options')
            results.append("• Add to your darwin-configuration.nix")
            results.append("• Use darwin_options() to see all categories")
        else:
            results.append(f'• Try broader search: darwin_search(query="{query[:3]}", limit=50)')
            results.append("• Browse categories: darwin_options()")
            results.append(f'• Try Home Manager instead: hm_search(query="{query}")')
            results.append(f'• Check packages: search(query="{query}", search_type="packages")')

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool(name="darwin_show")
async def darwin_show(
    name: Annotated[
        str,
        Field(description="Exact nix-darwin option name. Examples: 'system.defaults.dock.autohide', 'homebrew.enable'"),
    ],
) -> str:
    """Get complete details for a nix-darwin option.

    WHAT IT DOES:
    • Shows option type and description
    • Displays macOS-specific settings
    • Requires exact option name
    • Suggests alternatives if not found

    USE THIS TO:
    • View option details: darwin_show("system.defaults.dock.autohide")
    • Check types: darwin_show("homebrew.enable")
    • Get help: darwin_show("launchd.agents")

    Args:
        name: Exact darwin option name. Example: 'system.defaults.dock.autohide'

    Returns:
        Plain text with option details (name, type, description) or error with suggestions
    """
    try:
        # Search more broadly first
        options = parse_html_options(DARWIN_URL, name, "", 100)

        # Look for exact match
        for opt in options:
            if opt["name"] == name:
                info = []
                info.append(f"Option: {name}")
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        # If not found, check if there are similar options to suggest
        if options:
            suggestions = []
            for opt in options[:5]:  # Show up to 5 suggestions
                if name in opt["name"] or opt["name"].startswith(name + "."):
                    suggestions.append(opt["name"])

            if suggestions:
                return error(
                    f"Option '{name}' not found. Did you mean one of these?\n"
                    + "\n".join(f"  • {s}" for s in suggestions)
                    + f"\n\nTip: Use darwin_browse() with prefix '{name}' to browse all options with this prefix.",
                    "NOT_FOUND",
                )

        return error(
            f"Option '{name}' not found.\n"
            + f"Tip: Use darwin_browse() with prefix '{name}' to browse available options.",
            "NOT_FOUND",
        )

    except Exception as e:
        return error(str(e))


@mcp.tool(name="darwin_stats")
async def darwin_stats() -> str:
    """Get nix-darwin statistics overview.

    WHAT IT DOES:
    • Shows total option count
    • Lists top categories with counts
    • Provides instant metrics
    • macOS configuration complexity

    USE THIS TO:
    • Get overview: darwin_stats()
    • See category distribution
    • Check nix-darwin scope

    Returns:
        Plain text summary with total options, category count, and top 5 categories
    """
    try:
        # Parse all options to get statistics
        options = parse_html_options(DARWIN_URL, limit=3000)

        if not options:
            return error("Failed to fetch nix-darwin statistics")

        # Count categories
        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        # Count types
        types: dict[str, int] = {}
        for opt in options:
            opt_type = opt.get("type", "unknown")
            if opt_type:
                # Simplify complex types
                if "null or" in opt_type:
                    opt_type = "nullable"
                elif "list of" in opt_type:
                    opt_type = "list"
                elif "attribute set" in opt_type:
                    opt_type = "attribute set"
                types[opt_type] = types.get(opt_type, 0) + 1

        # Build statistics
        return f"""nix-darwin Statistics:
• Total options: {len(options):,}
• Categories: {len(categories)}
• Top categories:
  - services: {categories.get("services", 0):,} options
  - system: {categories.get("system", 0):,} options
  - launchd: {categories.get("launchd", 0):,} options
  - programs: {categories.get("programs", 0):,} options
  - homebrew: {categories.get("homebrew", 0):,} options"""
    except Exception as e:
        return error(str(e))


@mcp.tool(name="darwin_options")
async def darwin_options() -> str:
    """List all nix-darwin option categories.

    WHAT IT DOES:
    • Shows all top-level categories
    • Displays option count per category
    • macOS-specific organization
    • Perfect starting point

    USE THIS TO:
    • Browse categories: darwin_options()
    • Find macOS settings areas
    • Start nix-darwin setup

    Returns:
        Plain text list of categories sorted alphabetically with option counts
    """
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(DARWIN_URL, limit=2000)
        categories: dict[str, int] = {}

        for opt in options:
            name = opt["name"]
            # Process option names
            if name and not name.startswith("."):
                if "." in name:
                    cat = name.split(".")[0]
                else:
                    cat = name  # Option without dot is its own category
                # Valid categories should:
                # - Be more than 1 character
                # - Be a valid identifier (allows underscores)
                # - Not be common value words
                # - Match typical nix option category patterns
                if (
                    len(cat) > 1 and cat.isidentifier() and (cat.islower() or cat.startswith("_"))
                ):  # This ensures valid identifier
                    # Additional filtering for known valid Darwin categories
                    valid_categories = {
                        "documentation",
                        "environment",
                        "fonts",
                        "homebrew",
                        "ids",
                        "launchd",
                        "networking",
                        "nix",
                        "nixpkgs",
                        "power",
                        "programs",
                        "security",
                        "services",
                        "system",
                        "targets",
                        "time",
                        "users",
                    }
                    # Only include if it's in the known valid list or looks like a typical category
                    if cat in valid_categories or (len(cat) >= 3 and not any(char.isdigit() for char in cat)):
                        categories[cat] = categories.get(cat, 0) + 1

        results = []
        results.append(f"nix-darwin option categories ({len(categories)} total):\n")

        # Sort by count descending, then alphabetically
        sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))

        for cat, count in sorted_cats:
            results.append(f"• {cat} ({count} options)")

        return "\n".join(results)

    except Exception as e:
        return error(str(e))


@mcp.tool(name="darwin_browse")
async def darwin_browse(
    option_prefix: Annotated[
        str, Field(description="Option prefix to browse. Examples: 'system.defaults.dock', 'homebrew', 'services'")
    ],
) -> str:
    """Browse nix-darwin options by prefix.

    WHAT IT DOES:
    • Lists all options under a prefix
    • Shows macOS-specific sub-options
    • Enables deep exploration
    • Discovers related settings

    USE THIS TO:
    • Browse system: darwin_browse("system.defaults")
    • Explore homebrew: darwin_browse("homebrew")
    • Find services: darwin_browse("services")

    Args:
        option_prefix: Darwin option prefix. Examples: 'system.defaults', 'services', 'homebrew'

    Returns:
        Plain text list of options with the given prefix, including descriptions
    """
    try:
        options = parse_html_options(DARWIN_URL, "", option_prefix)

        if not options:
            return f"No nix-darwin options found with prefix '{option_prefix}'"

        results = []
        results.append(f"nix-darwin options with prefix '{option_prefix}' ({len(options)} found):\n")

        for opt in sorted(options, key=lambda x: x["name"]):
            results.append(f"• {opt['name']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool()
async def flakes() -> str:
    """Replaces browsing GitHub/FlakeHub manually.
    Get comprehensive flake ecosystem statistics.
    • Aggregated data from all indexed flakes
    • Top contributors and repository types
    • No need to search multiple platforms
    Use this to understand the flake ecosystem.

    Returns:
        Plain text summary with flake statistics and top contributors
    """
    try:
        # Use the same alias as the web UI for accurate counts
        flake_index = "latest-43-group-manual"

        # Get total count of flake packages (not options or apps)
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_count",
                json={"query": {"term": {"type": "package"}}},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            total_packages = resp.json().get("count", 0)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return error("Flake indices not found. Flake search may be temporarily unavailable.")
            raise

        # Get unique flakes by sampling documents
        # Since aggregations on text fields don't work, we'll sample and count manually
        unique_urls = set()
        type_counts: dict[str, int] = {}
        contributor_counts: dict[str, int] = {}

        try:
            # Get a large sample of documents to count unique flakes
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={
                    "size": 10000,  # Get a large sample
                    "query": {"term": {"type": "package"}},  # Only packages
                    "_source": ["flake_resolved", "flake_name", "package_pname"],
                },
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            # Process hits to extract unique URLs
            for hit in hits:
                src = hit.get("_source", {})
                resolved = src.get("flake_resolved", {})

                if isinstance(resolved, dict) and "url" in resolved:
                    url = resolved["url"]
                    unique_urls.add(url)

                    # Count types
                    flake_type = resolved.get("type", "unknown")
                    type_counts[flake_type] = type_counts.get(flake_type, 0) + 1

                    # Extract contributor from URL
                    contributor = None
                    if "github.com/" in url:
                        parts = url.split("github.com/")[1].split("/")
                        if parts:
                            contributor = parts[0]
                    elif "codeberg.org/" in url:
                        parts = url.split("codeberg.org/")[1].split("/")
                        if parts:
                            contributor = parts[0]
                    elif "sr.ht/~" in url:
                        parts = url.split("sr.ht/~")[1].split("/")
                        if parts:
                            contributor = parts[0]

                    if contributor:
                        contributor_counts[contributor] = contributor_counts.get(contributor, 0) + 1

            unique_count = len(unique_urls)

            # Format type info
            type_info = []
            for type_name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                if type_name:
                    type_info.append(f"  - {type_name}: {count:,}")

            # Format contributor info
            owner_info = []
            for contributor, count in sorted(contributor_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                owner_info.append(f"  - {contributor}: {count:,} packages")

        except Exception:
            # Fallback if query fails
            unique_count = 0
            type_info = []
            owner_info = []

        # Build statistics
        results = []
        results.append("NixOS Flakes Statistics:")
        results.append(f"• Available flakes: {total_packages:,}")
        if unique_count > 0:
            results.append(f"• Unique repositories: {unique_count:,}")

        if type_info:
            results.append("• Flake types:")
            results.extend(type_info)

        if owner_info:
            results.append("• Top contributors:")
            results.extend(owner_info)

        results.append("\nNote: Flakes are community-contributed and indexed separately from official packages.")

        return "\n".join(results)

    except Exception as e:
        return error(str(e))


async def _search_github_flakes(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search GitHub for repositories with nix-flake topic."""
    github_flakes = []

    try:
        # Build GitHub search query
        search_query = "topic:nix-flake"
        if query and query.strip() and query != "*":
            search_query += f" {query}"

        # Use aiohttp for async request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(limit, 30),  # GitHub limits to 30
                },
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    for repo in data.get("items", []):
                        github_flakes.append(
                            {
                                "name": repo["name"],
                                "full_name": repo["full_name"],
                                "description": repo.get("description", ""),
                                "stars": repo["stargazers_count"],
                                "topics": repo.get("topics", []),
                                "html_url": repo["html_url"],
                                "owner": repo["owner"]["login"],
                                "repo": repo["name"],
                                "updated_at": repo["updated_at"],
                                "source": "github",
                            }
                        )
    except Exception:
        # Silently fail GitHub search - we still have NixOS index
        pass

    return github_flakes


async def _flake_search_impl(query: str, limit: int = 20, channel: str = "unstable") -> str:
    """Internal implementation for flakes search."""
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    try:
        # Search both NixOS index and GitHub in parallel
        import asyncio

        # Start both searches concurrently
        github_task = asyncio.create_task(_search_github_flakes(query, limit))

        # Use the same alias as the web UI to get only flake packages
        flake_index = "latest-43-group-manual"

        # Build query for flakes
        if query.strip() == "" or query == "*":
            # Empty or wildcard query - get all flakes
            q: dict[str, Any] = {"match_all": {}}
        else:
            # Search query with multiple fields, including nested queries for flake_resolved
            q = {
                "bool": {
                    "should": [
                        {"match": {"flake_name": {"query": query, "boost": 3}}},
                        {"match": {"flake_description": {"query": query, "boost": 2}}},
                        {"match": {"package_pname": {"query": query, "boost": 1.5}}},
                        {"match": {"package_description": query}},
                        {"wildcard": {"flake_name": {"value": f"*{query}*", "boost": 2.5}}},
                        {"wildcard": {"package_pname": {"value": f"*{query}*", "boost": 1}}},
                        {"prefix": {"flake_name": {"value": query, "boost": 2}}},
                        # Nested queries for flake_resolved fields
                        {
                            "nested": {
                                "path": "flake_resolved",
                                "query": {"term": {"flake_resolved.owner": query.lower()}},
                                "boost": 2,
                            }
                        },
                        {
                            "nested": {
                                "path": "flake_resolved",
                                "query": {"term": {"flake_resolved.repo": query.lower()}},
                                "boost": 2,
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                }
            }

        # Execute search with package filter to match web UI
        search_query = {"bool": {"filter": [{"term": {"type": "package"}}], "must": [q]}}

        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={"query": search_query, "size": limit * 5, "track_total_hits": True},  # Get more results
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 404:
                # No flake indices found
                return error("Flake indices not found. Flake search may be temporarily unavailable.")
            raise

        # Wait for GitHub results before processing
        github_results = await github_task

        # Format results as plain text
        if not hits and not github_results:
            return f"""No flakes found matching '{query}'.

Try searching for:
• Popular flakes: nixpkgs, home-manager, flake-utils, devenv
• By owner: nix-community, numtide, cachix
• By topic: python, rust, nodejs, devops

Browse flakes at:
• GitHub: https://github.com/topics/nix-flakes
• FlakeHub: https://flakehub.com/"""

        # Group hits by flake to avoid duplicates
        flakes = {}
        packages_only = []  # For entries without flake metadata

        for hit in hits:
            src = hit.get("_source", {})

            # Get flake information
            flake_name = src.get("flake_name", "").strip()
            package_pname = src.get("package_pname", "")
            resolved = src.get("flake_resolved", {})

            # Skip entries without any useful name
            if not flake_name and not package_pname:
                continue

            # If we have flake metadata (resolved), use it to create unique key
            if isinstance(resolved, dict) and (resolved.get("owner") or resolved.get("repo") or resolved.get("url")):
                owner = resolved.get("owner", "")
                repo = resolved.get("repo", "")
                url = resolved.get("url", "")

                # Create a unique key based on available info
                if owner and repo:
                    flake_key = f"{owner}/{repo}"
                    display_name = flake_name or repo or package_pname
                elif url:
                    # Extract name from URL for git repos
                    flake_key = url
                    if "/" in url:
                        display_name = flake_name or url.rstrip("/").split("/")[-1].replace(".git", "") or package_pname
                    else:
                        display_name = flake_name or package_pname
                else:
                    flake_key = flake_name or package_pname
                    display_name = flake_key

                # Initialize flake entry if not seen
                if flake_key not in flakes:
                    flakes[flake_key] = {
                        "name": display_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": owner,
                        "repo": repo,
                        "url": url,
                        "type": resolved.get("type", ""),
                        "packages": set(),  # Use set to avoid duplicates
                    }

                # Add package if available
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_key]["packages"].add(attr_name)

            elif flake_name:
                # Has flake_name but no resolved metadata
                flake_key = flake_name

                if flake_key not in flakes:
                    flakes[flake_key] = {
                        "name": flake_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": "",
                        "repo": "",
                        "type": "",
                        "packages": set(),
                    }

                # Add package if available
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_key]["packages"].add(attr_name)

            else:
                # Package without flake metadata - might still be relevant
                packages_only.append(
                    {
                        "name": package_pname,
                        "description": src.get("package_description", ""),
                        "attr_name": src.get("package_attr_name", ""),
                    }
                )

        # Merge GitHub results into flakes dict
        for gh_flake in github_results:
            flake_key = f"{gh_flake['owner']}/{gh_flake['repo']}"

            # Skip if we already have this flake from NixOS index
            if flake_key not in flakes:
                flakes[flake_key] = {
                    "name": gh_flake["name"],
                    "description": gh_flake["description"],
                    "owner": gh_flake["owner"],
                    "repo": gh_flake["repo"],
                    "url": gh_flake["html_url"],
                    "type": "github",
                    "packages": set(),
                    "stars": gh_flake["stars"],
                    "topics": gh_flake["topics"],
                    "source": "github",
                }
            else:
                # Enrich existing entry with GitHub data
                flakes[flake_key]["stars"] = gh_flake["stars"]
                flakes[flake_key]["topics"] = gh_flake["topics"]

        # Build results
        results = []

        # Sort flakes by relevance (GitHub stars if available, then alphabetically)
        sorted_flakes = sorted(flakes.items(), key=lambda x: (-x[1].get("stars", 0), x[0]))

        # Show both total hits and unique flakes
        total_count = len(flakes)
        if github_results:
            total_count_str = f"{total_count} unique flakes"
            if total > len(flakes):
                total_count_str += f" ({total:,} indexed packages)"
        else:
            if total > len(flakes):
                total_count_str = f"{total:,} total matches ({len(flakes)} unique flakes)"
            else:
                total_count_str = f"{len(flakes)} unique flakes"

        results.append(f"Found {total_count_str} matching '{query}':\n")

        for _flake_key, flake in sorted_flakes[:limit]:
            # Add star count for GitHub repos
            name_prefix = ""
            if flake.get("stars", 0) > 0:
                name_prefix = f"[{flake['stars']} stars] "

            results.append(f"• {name_prefix}{flake['name']}")

            if flake.get("owner") and flake.get("repo"):
                repo_info = f"  Repository: {flake['owner']}/{flake['repo']}"
                if flake.get("type") and flake["type"] != "github":
                    repo_info += f" ({flake['type']})"
                elif flake.get("source") == "github":
                    repo_info += " (GitHub)"
                results.append(repo_info)
            elif flake.get("url"):
                results.append(f"  URL: {flake['url']}")

            if flake.get("description"):
                desc = flake["description"]
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                results.append(f"  Description: {desc}")

            # Show topics for GitHub flakes
            if flake.get("topics") and len(flake["topics"]) > 1:  # Don't show if only nix-flake
                other_topics = [t for t in flake["topics"] if t != "nix-flake"]
                if other_topics:
                    results.append(f"  Topics: {', '.join(other_topics[:5])}")

            # Show packages if available
            if flake["packages"]:
                # Show max 5 packages, sorted
                packages = sorted(flake["packages"])[:5]
                if len(flake["packages"]) > 5:
                    results.append(f"  Packages: {', '.join(packages)}, ... ({len(flake['packages'])} total)")
                else:
                    results.append(f"  Packages: {', '.join(packages)}")

            # Show flake reference
            if flake.get("owner") and flake.get("repo"):
                results.append(f"  Flake: github:{flake['owner']}/{flake['repo']}")

            results.append("")

        # Add helpful next steps
        results.append("NEXT STEPS:")
        results.append("━" * 11)
        if flakes:  # Changed from unique_flakes to flakes
            first_flake = next(iter(flakes.values()))
            if first_flake.get("url"):
                results.append(f"• Clone: git clone {first_flake['url']}")
            results.append("• Add flake input to your flake.nix")
        results.append("• Use search() to find packages in nixpkgs")
        results.append("• Browse more at: https://github.com/topics/nix-flakes")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


def _version_key(version_str: str) -> tuple[int, int, int]:
    """Convert version string to tuple for proper sorting."""
    try:
        parts = version_str.split(".")
        # Handle versions like "3.9.9" or "3.10.0-rc1"
        numeric_parts = []
        for part in parts[:3]:  # Major.Minor.Patch
            # Extract numeric part
            numeric = ""
            for char in part:
                if char.isdigit():
                    numeric += char
                else:
                    break
            if numeric:
                numeric_parts.append(int(numeric))
            else:
                numeric_parts.append(0)
        # Pad with zeros if needed
        while len(numeric_parts) < 3:
            numeric_parts.append(0)
        return (numeric_parts[0], numeric_parts[1], numeric_parts[2])
    except Exception:
        return (0, 0, 0)


def _format_nixhub_found_version(package_name: str, version: str, found_version: dict[str, Any]) -> str:
    """Format a found version for display."""
    results = []
    results.append(f"Found {package_name} version {version}\n")

    last_updated = found_version.get("last_updated", "")
    if last_updated:
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
            results.append(f"Last updated: {formatted_date}")
        except Exception:
            results.append(f"Last updated: {last_updated}")

    platforms_summary = found_version.get("platforms_summary", "")
    if platforms_summary:
        results.append(f"Platforms: {platforms_summary}")

    # Show commit hashes
    platforms = found_version.get("platforms", [])
    if platforms:
        results.append("\nNixpkgs commits:")
        seen_commits = set()

        for platform in platforms:
            attr_path = platform.get("attribute_path", "")
            commit_hash = platform.get("commit_hash", "")

            if commit_hash and commit_hash not in seen_commits:
                seen_commits.add(commit_hash)
                if re.match(r"^[a-fA-F0-9]{40}$", commit_hash):
                    results.append(f"• {commit_hash}")
                    if attr_path:
                        results.append(f"  Attribute: {attr_path}")

    results.append("\nTo use this version:")
    results.append("1. Pin nixpkgs to one of the commit hashes above")
    results.append("2. Install using the attribute path")

    return "\n".join(results)


def _format_nixhub_release(release: dict[str, Any], package_name: str | None = None) -> list[str]:
    """Format a single NixHub release for display."""
    results = []
    version = release.get("version", "unknown")
    last_updated = release.get("last_updated", "")
    platforms_summary = release.get("platforms_summary", "")
    platforms = release.get("platforms", [])

    results.append(f"• Version {version}")

    if last_updated:
        # Format date nicely
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
            results.append(f"  Last updated: {formatted_date}")
        except Exception:
            results.append(f"  Last updated: {last_updated}")

    if platforms_summary:
        results.append(f"  Platforms: {platforms_summary}")

    # Show commit hashes and attribute paths for each platform (avoid duplicates)
    if platforms:
        seen_commits = set()
        for platform in platforms:
            commit_hash = platform.get("commit_hash", "")
            attr_path = platform.get("attribute_path", "")

            if commit_hash and commit_hash not in seen_commits:
                seen_commits.add(commit_hash)
                # Validate commit hash format (40 hex chars)
                if re.match(r"^[a-fA-F0-9]{40}$", commit_hash):
                    results.append(f"  Nixpkgs commit: {commit_hash}")
                else:
                    results.append(f"  Nixpkgs commit: {commit_hash} (warning: invalid format)")

                # Show attribute path if different from package name
                if attr_path and package_name and attr_path != package_name:
                    results.append(f"  Attribute: {attr_path}")

    return results


@mcp.tool(name="flake_search")
async def flake_search(
    query: Annotated[
        str,
        Field(
            description="Flake name, owner, or keyword to search for. "
            "Examples: 'home-manager', 'nix-community', 'devenv'"
        ),
    ],
    limit: Annotated[int, Field(description="Maximum number of results to return (1-100)", ge=1, le=100)] = 20,
    channel: Annotated[str, Field(description="Ignored - flakes use a separate indexing system")] = "unstable",
) -> str:
    """Replaces browsing GitHub/FlakeHub manually.
    Search the entire flake ecosystem instantly.
    • Aggregated from all indexed flakes
    • Find by name, owner, or description
    • Discover community packages
    Use this to find flakes and community contributions.

    Args:
        query: Flake name, owner, or keyword. Examples: 'home-manager', 'nix-community', 'devenv'
        limit: Maximum number of results to return (default: 20, max: 100)
        channel: Ignored - flakes use a separate indexing system

    Returns:
        Plain text list of unique flakes with their packages and metadata
    """
    return await _flake_search_impl(query, limit, channel)


@mcp.tool()
async def versions(
    package_name: Annotated[
        str | None,
        Field(
            description="Exact package name to get version history for. "
            "Examples: 'ruby', 'python3', 'nodejs'. If omitted, uses last searched package."
        ),
    ] = None,
    limit: Annotated[int, Field(description="Maximum number of versions to return (1-50)", ge=1, le=50)] = 10,
) -> str:
    """View complete version history for any package.

    WHAT IT DOES:
    • Lists all versions ever in nixpkgs
    • Shows exact commit hashes for each version
    • Includes release dates and platforms
    • Perfect for pinning specific versions

    USE THIS TO:
    • Find old versions: versions("ruby")
    • Get commit for pinning: versions("python3", limit=20)
    • Check version availability before using find_version

    Args:
        package_name: Exact package name. Examples: 'ruby', 'python3', 'nodejs'. Note: use 'python3' not 'python'
        limit: Maximum number of versions to return (default: 10, max: 50)

    Returns:
        Plain text with package info and version history including commit hashes
    """
    # Validate inputs
    if not package_name or not package_name.strip():
        # Try to use context
        if context.last_package_name:
            package_name = context.last_package_name
        else:
            return error("Package name is required. Use search() first or provide package_name.")

    # Sanitize package name - only allow alphanumeric, hyphens, underscores, dots
    if not re.match(r"^[a-zA-Z0-9\-_.]+$", package_name):
        return error("Invalid package name. Only letters, numbers, hyphens, underscores, and dots are allowed")

    if not 1 <= limit <= 50:
        return error("Limit must be between 1 and 50")

    try:
        # Construct NixHub API URL with the _data parameter
        url = f"https://www.nixhub.io/packages/{package_name}?_data=routes%2F_nixhub.packages.%24pkg._index"

        # Make request with timeout and proper headers
        headers = {"Accept": "application/json", "User-Agent": "mcp-nixos/1.0.0"}  # Identify ourselves

        resp = requests.get(url, headers=headers, timeout=15)

        # Handle different HTTP status codes
        if resp.status_code == 404:
            return error(f"Package '{package_name}' not found in NixHub", "NOT_FOUND")
        if resp.status_code >= 500:
            # NixHub returns 500 for non-existent packages with unusual names
            # Check if the package name looks suspicious
            if len(package_name) > 30 or package_name.count("-") > 5:
                return error(f"Package '{package_name}' not found in NixHub", "NOT_FOUND")
            return error("NixHub service temporarily unavailable", "SERVICE_ERROR")

        resp.raise_for_status()

        # Parse JSON response
        data = resp.json()

        # Validate response structure
        if not isinstance(data, dict):
            return error("Invalid response format from NixHub")

        # Extract package info
        # Use the requested package name, not what API returns (e.g., user asks for python3, API returns python)
        name = package_name
        summary = data.get("summary", "")
        releases = data.get("releases", [])

        if not releases:
            return f"Package: {name}\nNo version history available in NixHub"

        # Build results
        results = []
        results.append(f"Package: {name}")
        if summary:
            results.append(f"Description: {summary}")
        results.append(f"Total versions: {len(releases)}")
        results.append("")

        # Limit results
        shown_releases = releases[:limit]

        results.append(f"Version history (showing {len(shown_releases)} of {len(releases)}):\n")

        for release in shown_releases:
            results.extend(_format_nixhub_release(release, name))
            results.append("")

        # Add helpful next steps
        results.append("NEXT STEPS:")
        results.append("━" * 11)
        if shown_releases and any(r.get("platforms", [{}])[0].get("commit_hash") for r in shown_releases):
            results.append("• Pin nixpkgs to a specific commit hash shown above")
            results.append("• Use the attribute path in your configuration")
        results.append(f'• Use find_version(package_name="{name}", version="X.Y.Z") to find a specific version')
        results.append(f'• Use show(name="{name}") to see current package details')
        results.append(f'• Use compare(package_name="{name}") to compare across channels')

        return "\n".join(results).strip()

    except requests.Timeout:
        return error("Request to NixHub timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Network error accessing NixHub: {str(e)}", "NETWORK_ERROR")
    except ValueError as e:
        return error(f"Failed to parse NixHub response: {str(e)}", "PARSE_ERROR")
    except Exception as e:
        return error(f"Unexpected error: {str(e)}")


@mcp.tool(name="find_version")
async def find_version(
    package_name: Annotated[str, Field(description="Exact package name. Examples: 'ruby', 'python3', 'nodejs'")],
    version: Annotated[str, Field(description="Exact version string to find. Examples: '2.6.7', '3.5.9', '16.14.0'")],
) -> str:
    """Find the exact commit hash for a specific package version.

    WHAT IT DOES:
    • Searches for exact version match
    • Returns nixpkgs commit hash if found
    • Shows available alternatives if not found
    • Uses smart incremental search

    USE THIS TO:
    • Pin exact version: find_version("ruby", "2.6.7")
    • Get reproducible builds: find_version("python3", "3.9.7")
    • Find legacy versions for compatibility

    Args:
        package_name: Exact package name. Examples: 'ruby', 'python3', 'nodejs'
        version: Exact version string. Examples: '2.6.7', '3.5.9', '16.14.0'

    Returns:
        Plain text with version info and commit hash if found, or helpful message if not
    """
    # Validate inputs
    if not package_name or not package_name.strip():
        return error("Package name is required")

    if not version or not version.strip():
        return error("Version is required")

    # Sanitize inputs
    if not re.match(r"^[a-zA-Z0-9\-_.]+$", package_name):
        return error("Invalid package name. Only letters, numbers, hyphens, underscores, and dots are allowed")

    # Try with incremental limits
    limits_to_try = [10, 25, 50]
    found_version = None
    all_versions: list[dict[str, Any]] = []

    for limit in limits_to_try:
        try:
            # Make request - handle special cases for package names
            nixhub_name = package_name
            # Common package name mappings
            if package_name == "python":
                nixhub_name = "python3"
            elif package_name == "python2":
                nixhub_name = "python"

            url = f"https://www.nixhub.io/packages/{nixhub_name}?_data=routes%2F_nixhub.packages.%24pkg._index"
            headers = {"Accept": "application/json", "User-Agent": "mcp-nixos/1.0.0"}

            resp = requests.get(url, headers=headers, timeout=15)

            if resp.status_code == 404:
                return error(f"Package '{package_name}' not found in NixHub", "NOT_FOUND")
            if resp.status_code >= 500:
                return error("NixHub service temporarily unavailable", "SERVICE_ERROR")

            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, dict):
                return error("Invalid response format from NixHub")

            releases = data.get("releases", [])

            # Collect all versions seen
            for release in releases[:limit]:
                release_version = release.get("version", "")
                if release_version and release_version not in [v["version"] for v in all_versions]:
                    all_versions.append({"version": release_version, "release": release})

                # Check if this is the version we're looking for
                if release_version == version:
                    found_version = release
                    break

            if found_version:
                break

        except requests.Timeout:
            return error("Request to NixHub timed out", "TIMEOUT")
        except requests.RequestException as e:
            return error(f"Network error accessing NixHub: {str(e)}", "NETWORK_ERROR")
        except Exception as e:
            return error(f"Unexpected error: {str(e)}")

    # Format response
    if found_version:
        return _format_nixhub_found_version(package_name, version, found_version)

    # Version not found - provide helpful information
    results = []
    results.append(f"[NOT FOUND] {package_name} version {version} not found in NixHub\n")

    # Show available versions
    if all_versions:
        results.append(f"Available versions (checked {len(all_versions)} total):")

        # Sort versions properly using version comparison
        sorted_versions = sorted(all_versions, key=lambda x: _version_key(x["version"]), reverse=True)

        # Find newest and oldest
        newest = sorted_versions[0]["version"]
        oldest = sorted_versions[-1]["version"]

        results.append(f"• Newest: {newest}")
        results.append(f"• Oldest: {oldest}")

        # Show version range summary
        major_versions = set()
        for v in all_versions:
            parts = v["version"].split(".")
            if parts:
                major_versions.add(parts[0])

        if major_versions:
            results.append(f"• Major versions available: {', '.join(sorted(major_versions, reverse=True))}")

        # Check if requested version is older than available
        try:
            requested_parts = version.split(".")
            oldest_parts = oldest.split(".")

            if len(requested_parts) >= 2 and len(oldest_parts) >= 2:
                req_major = int(requested_parts[0])
                req_minor = int(requested_parts[1])
                old_major = int(oldest_parts[0])
                old_minor = int(oldest_parts[1])

                if req_major < old_major or (req_major == old_major and req_minor < old_minor):
                    results.append(f"\nVersion {version} is older than the oldest available ({oldest})")
                    results.append("This version may have been removed after reaching end-of-life.")
        except (ValueError, IndexError):
            pass

        results.append("\nAlternatives:")
        results.append("• Use a newer version if possible")
        results.append("• Build from source with a custom derivation")
        results.append("• Use Docker/containers with the specific version")
        results.append("• Find an old nixpkgs commit from before the version was removed")

    return "\n".join(results)


@mcp.tool()
async def which(
    package_name: Annotated[str, Field(description="Command or file name to find. Examples: 'gcc', 'vim', 'make'")],
    concise: Annotated[bool, Field(description="Return only the most relevant package without details")] = False,
) -> str:
    """Find which package provides a command or binary.

    WHAT IT DOES:
    • Identifies package that provides a command
    • Shows exact matches first
    • Includes related packages
    • Works instantly without channel setup

    USE THIS TO:
    • Find missing commands: which("gcc")
    • Resolve "command not found": which("rg")
    • Discover package names: which("make")

    Args:
        package_name: Command or binary name to search for

    Returns:
        Plain text with packages that provide the command
    """
    # Search for packages that might provide this command
    # First try exact match in programs
    query = package_name
    limit = 20
    channel = "unstable"

    try:
        # Build query specifically for program names
        # Prioritize exact matches over partial matches
        q = {
            "bool": {
                "must": [{"term": {"type": "package"}}],
                "should": [
                    # Highest priority: exact program match
                    {"term": {"package_programs": {"value": query, "boost": 10}}},
                    # High priority: package name matches query
                    {"term": {"package_pname": {"value": query, "boost": 5}}},
                    # Medium priority: program contains query
                    {"match": {"package_programs": {"query": query, "boost": 3}}},
                    # Lower priority: description mentions as command
                    {"match_phrase": {"package_description": {"query": f"command {query}", "boost": 2}}},
                    # Lowest priority: wildcard match
                    {"wildcard": {"package_programs": {"value": f"*{query}*", "boost": 1}}},
                ],
                "minimum_should_match": 1,
            }
        }

        channels = get_channels()
        if channel not in channels:
            return error(f"Invalid channel '{channel}'")

        hits = es_query(channels[channel], q, limit)

        if not hits:
            # Try broader search
            suggestions = [
                f'search(query="{query}") - search for packages by name',
                f'search(query="{query} command") - search descriptions',
                "Check common command mappings: python -> python3, node -> nodejs, vi -> vim",
            ]
            return error(f"No packages found providing '{query}'", "NOT_FOUND", suggestions)

        # In concise mode, just return the best match
        exact_matches = []
        partial_matches = []

        for hit in hits:
            src = hit.get("_source", {})
            programs = src.get("package_programs", [])
            pkg_name = src.get("package_pname", "")
            version = src.get("package_pversion", "")

            # Check if query matches any program exactly
            query_lower = query.lower()
            has_exact = any(p.lower() == query_lower for p in programs)

            if has_exact:
                exact_matches.append({"name": pkg_name, "version": version, "programs": programs})
            else:
                partial_matches.append({"name": pkg_name, "version": version, "programs": programs})

        if concise and exact_matches:
            pkg = exact_matches[0]["name"]
            return f"{query} -> {pkg}"

        # Build content
        content = [f"Command: '{query}'", f"Results: {len(hits)} packages found", ""]

        # Show exact matches first
        if exact_matches:
            content.append("EXACT MATCHES:")
            # Limit to top 3 exact matches
            for match in exact_matches[:3]:
                content.append(f"• {match['name']} ({match['version']})")
                # Show which programs it provides
                matching_progs = [p for p in match["programs"] if p.lower() == query.lower()]
                if matching_progs:
                    content.append(f"  Provides: {', '.join(matching_progs)}")
                content.append("")

        # Show partial matches only if few exact matches
        if partial_matches and len(exact_matches) < 3:
            content.append("RELATED PACKAGES:")
            # Filter to only show packages where the query is actually in a program name
            relevant_partials = []
            for match in partial_matches:
                if any(query.lower() in p.lower() for p in match["programs"]):
                    relevant_partials.append(match)

            for match in relevant_partials[:3]:
                content.append(f"• {match['name']} ({match['version']})")
                relevant_progs = [p for p in match["programs"] if query.lower() in p.lower()][:2]
                if relevant_progs:
                    content.append(f"  Provides: {', '.join(relevant_progs)}")
                content.append("")

        # Prepare next steps
        next_steps = []
        if exact_matches:
            pkg = exact_matches[0]["name"]
            next_steps.extend(
                [
                    f"• Install: nix-env -iA nixpkgs.{pkg}",
                    f"• Add to config: environment.systemPackages = [ pkgs.{pkg} ];",
                    f'• Try first: try_package(package_name="{pkg}")',
                ]
            )
        else:
            next_steps.extend(
                [
                    "• Use search() to find the correct package name",
                    "• Check if the command has a different name in Nix",
                    "• Common mappings: python->python3, node->nodejs, vi->vim",
                ]
            )

        style = "concise" if concise else "normal"
        return format_tool_output("WHICH", query, content, next_steps, style)

    except Exception as e:
        return error(str(e))


@mcp.tool(name="discourse_search")
async def discourse_search(query: str, limit: int = 10) -> str:
    """Replaces manual forum browsing for NixOS help.
    Search NixOS Discourse for community discussions and solutions.
    • Real user experiences and solutions
    • Common problems and workarounds
    • Configuration examples from the community
    Use this when official docs don't have the answer.

    Args:
        query: Search terms. Examples: 'flakes tutorial', 'nvidia drivers', 'home-manager git'
        limit: Maximum results to return (default: 10, max: 30)

    Returns:
        Plain text list of relevant forum discussions with links
    """
    if not query.strip():
        return error("Search query cannot be empty")

    if limit < 1 or limit > 30:
        return error("Limit must be between 1 and 30")

    try:
        # Search NixOS Discourse
        url = "https://discourse.nixos.org/search.json"
        params: dict[str, str | int] = {"q": query, "page": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return error(f"Discourse API error: {response.status}")

                data = await response.json()

        if not data.get("topics"):
            return (
                f"No discussions found for '{query}'.\n\n"
                "Try:\n"
                "• Different keywords\n"
                "• Broader search terms\n"
                "• Checking the NixOS manual instead"
            )

        results = []
        results.append(f"NixOS Discourse discussions for '{query}':\n")

        topics = data["topics"][:limit]
        for topic in topics:
            title = topic.get("title", "Untitled")
            topic_id = topic.get("id")
            posts_count = topic.get("posts_count", 0)
            created = topic.get("created_at", "")[:10]  # Just the date

            # Build topic URL
            topic_url = f"https://discourse.nixos.org/t/{topic_id}"

            results.append(f"• {title}")
            results.append(f"  Posts: {posts_count} | Created: {created}")
            results.append(f"  {topic_url}")
            results.append("")

        if len(topics) == limit and len(data["topics"]) > limit:
            results.append(f"Showing first {limit} results. Use higher limit for more.")

        return "\n".join(results).strip()

    except TimeoutError:
        return error("Request timeout - Discourse may be slow")
    except Exception as e:
        return error(f"Failed to search Discourse: {str(e)}")


@mcp.tool(name="github_search")
async def github_search(query: str, repo: str = "NixOS/nixpkgs", search_type: str = "issues", limit: int = 10) -> str:
    """Replaces manual GitHub issue browsing.
    Search GitHub for NixOS-related issues, PRs, and discussions.
    • Bug reports and known issues
    • Feature requests and RFCs
    • Pull requests with fixes
    • Community discussions
    Use this to find known problems or ongoing work.

    Args:
        query: Search terms. Examples: 'segfault', 'python broken', 'flakes RFC'
        repo: Repository to search (default: 'NixOS/nixpkgs'). Also try: 'NixOS/nix', 'nix-community/home-manager'
        search_type: Type of items - 'issues', 'prs', or 'discussions' (default: 'issues')
        limit: Maximum results (default: 10, max: 30)

    Returns:
        Plain text list of relevant GitHub items with links
    """
    if not query.strip():
        return error("Search query cannot be empty")

    if limit < 1 or limit > 30:
        return error("Limit must be between 1 and 30")

    valid_types = ["issues", "prs", "discussions"]
    if search_type not in valid_types:
        return error(f"Invalid search_type. Must be one of: {', '.join(valid_types)}")

    try:
        # Map search_type to GitHub API type parameter
        type_map = {"issues": "issue", "prs": "pr", "discussions": "discussions"}

        # GitHub Search API
        if search_type == "discussions":
            # Discussions use GraphQL API - for now, return a helpful message
            return f"""GitHub Discussions search requires GraphQL API.

For now, you can browse discussions directly:
• https://github.com/{repo}/discussions

Or search issues instead with:
github_search("{query}", repo="{repo}", search_type="issues")"""

        url = "https://api.github.com/search/issues"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "mcp-nixos"}

        # Build search query
        github_query = f"{query} repo:{repo} type:{type_map[search_type]}"
        params: dict[str, str | int] = {"q": github_query, "sort": "updated", "order": "desc", "per_page": limit}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 403:
                    return error("GitHub API rate limit exceeded. Try again later.")
                if response.status != 200:
                    return error(f"GitHub API error: {response.status}")

                data = await response.json()

        items = data.get("items", [])
        if not items:
            return f"""No {search_type} found for '{query}' in {repo}.

Try:
• Different keywords
• Checking other repos: 'NixOS/nix', 'nix-community/home-manager'
• Using discourse_search() for community discussions"""

        results = []
        results.append(f"GitHub {search_type} in {repo} for '{query}':\n")

        for item in items:
            title = item.get("title", "Untitled")
            number = item.get("number")
            state = item.get("state", "unknown")
            created = item.get("created_at", "")[:10]
            comments = item.get("comments", 0)
            url = item.get("html_url", "")
            labels = [label["name"] for label in item.get("labels", [])][:3]

            # Format state
            state_icon = "🟢" if state == "open" else "🔴"

            results.append(f"• {state_icon} {title}")
            results.append(f"  #{number} | {state} | Comments: {comments} | Created: {created}")
            if labels:
                results.append(f"  Labels: {', '.join(labels)}")
            results.append(f"  {url}")
            results.append("")

        total = data.get("total_count", 0)
        if total > limit:
            results.append(f"Showing {limit} of {total} results. Use higher limit for more.")

        return "\n".join(results).strip()

    except TimeoutError:
        return error("Request timeout - GitHub may be slow")
    except Exception as e:
        return error(f"Failed to search GitHub: {str(e)}")


@mcp.tool()
async def help() -> str:
    """Complete guide to all NixOS MCP tools.

    WHAT IT DOES:
    • Lists all available tools by category
    • Shows example usage for each tool
    • Explains when to use MCP vs shell
    • Perfect starting point for new users

    USE THIS TO:
    • Learn available tools: help()
    • Find the right tool for your task
    • See usage examples

    Returns:
        Categorized guide to all NixOS MCP tools with examples
    """
    return """NixOS MCP Tools - Complete Reference Guide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEARCHING & DISCOVERY
━━━━━━━━━━━━━━━━━━━━━━━
• search        - Find packages/options (replaces: nix search, nix-env -qa)
                  Example: search(query="firefox")
• which         - Find package for command (replaces: command-not-found, nix-locate)
                  Example: which(package_name="rg")
• flake_search  - Search community flakes (replaces: browsing GitHub/FlakeHub)
                  Example: flake_search(query="home-manager")

PACKAGE OPERATIONS
━━━━━━━━━━━━━━━━━━━━
• show          - Package/option details (replaces: nix show-derivation, nix eval)
                  Example: show(name="firefox")
• install       - Installation commands (replaces: memorizing nix syntax)
                  Example: install(package_name="firefox", method="system")
• try_package   - Test without installing (replaces: nix-shell -p)
                  Example: try_package(package_name="neovim")
• why           - Why package is needed (replaces: nix why-depends)
                  Example: why(package_name="perl")

VERSION MANAGEMENT
━━━━━━━━━━━━━━━━━━━━
• versions      - Version history (replaces: nixpkgs git archaeology)
                  Example: versions(package_name="ruby")
• find_version  - Find specific version (replaces: manual commit searching)
                  Example: find_version(package_name="python3", version="3.9.7")
• compare       - Compare channels (replaces: manual version checking)
                  Example: compare(package_name="firefox")

CHANNELS & STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━
• channels      - List all channels (replaces: nix-channel --list)
                  Example: channels()
• stats         - Channel statistics (replaces: manual counting)
                  Example: stats(channel="stable")
• flakes        - Flake ecosystem stats (replaces: manual aggregation)
                  Example: flakes()

HOME MANAGER TOOLS
━━━━━━━━━━━━━━━━━━━━━
• hm_search     - Search options (replaces: man home-configuration.nix)
                  Example: hm_search(query="git")
• hm_show       - Option details (replaces: manual documentation lookup)
                  Example: hm_show(name="programs.git.enable")
• hm_browse     - Browse by prefix (replaces: tab completion)
                  Example: hm_browse(option_prefix="programs.git")
• hm_options    - List categories (replaces: doc structure browsing)
                  Example: hm_options()
• hm_stats      - Statistics (replaces: manual counting)
                  Example: hm_stats()

DARWIN (macOS) TOOLS
━━━━━━━━━━━━━━━━━━━━━━
• darwin_search - Search options (replaces: nix-darwin manual)
                  Example: darwin_search(query="dock")
• darwin_show   - Option details (replaces: source code checking)
                  Example: darwin_show(name="system.defaults.dock.autohide")
• darwin_browse - Browse by prefix (replaces: manual exploration)
                  Example: darwin_browse(option_prefix="system.defaults")
• darwin_options- List categories (replaces: doc navigation)
                  Example: darwin_options()
• darwin_stats  - Statistics (replaces: counting)
                  Example: darwin_stats()

COMMUNITY & HELP
━━━━━━━━━━━━━━━━━━
• discourse_search - Search forum (replaces: manual forum browsing)
                     Example: discourse_search(query="nvidia drivers")
• github_search    - Search issues/PRs (replaces: GitHub web search)
                     Example: github_search(query="buildPythonPackage")
• quick_start      - Common task examples (replaces: tutorial hunting)
                     Example: quick_start()
• help             - This guide (replaces: scattered documentation)
                     Example: help()

GETTING STARTED
━━━━━━━━━━━━━━━━━
1. Find a package:     search(query="firefox")
2. Get details:        show(name="firefox")
3. Try it out:         try_package(package_name="firefox")
4. Install it:         install(package_name="firefox")
5. Wonder why perl?    why(package_name="perl")

WHEN TO USE MCP TOOLS
━━━━━━━━━━━━━━━━━━━━━━
• Always for searching - 10x faster, pre-indexed
• Package discovery - no channel setup needed
• Version history - all versions ever in nixpkgs
• Configuration help - find any NixOS option
• Installation help - never guess syntax again

WHEN TO USE SHELL COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Actual installation: nix-env -iA, nixos-rebuild
• Building locally: nix-build, nix build
• Managing channels: nix-channel --add/--update
• Custom derivations: writing .nix files

PRO TIPS
━━━━━━━━━
• Start with search() - it's the primary discovery tool
• Use TAB completion with tool names
• Chain tools: search → show → try_package → install
• Check discourse_search() for real-world solutions

Type quick_start() for hands-on examples!"""


@mcp.tool()
async def why(
    package_name: Annotated[
        str,
        Field(description="Package that was installed unexpectedly. Examples: 'gcc', 'python3', 'perl', 'systemd'"),
    ],
) -> str:
    """Understand why a package was installed.

    WHAT IT DOES:
    • Explains common dependency chains
    • Shows which packages typically pull it in
    • Provides closure reduction tips
    • Clarifies unexpected installations

    USE THIS TO:
    • Understand dependencies: why("perl")
    • Reduce closure size: why("gcc")
    • Debug installations: why("python3")

    Args:
        package_name: Package name you're wondering about

    Returns:
        Plain text explanation of why the package is commonly needed
    """
    # Common dependency patterns in NixOS
    dependency_patterns: dict[str, dict[str, Any]] = {
        "gcc": {
            "reason": "GNU Compiler Collection - build dependency",
            "common_pullers": ["stdenv", "most compiled packages", "development environments"],
            "explanation": "GCC is part of the standard build environment (stdenv) in NixOS. "
            "It's needed to compile C/C++ code during package builds.",
            "reduce": "Use binary caches to avoid building from source, or use minimal stdenv variants.",
        },
        "perl": {
            "reason": "Perl interpreter - build scripts and tools",
            "common_pullers": ["openssl", "git", "texlive", "autoconf/automake"],
            "explanation": "Many packages use Perl scripts during their build process. "
            "OpenSSL, Git, and TeX distributions commonly require Perl.",
            "reduce": "Hard to avoid - Perl is deeply embedded in many build systems.",
        },
        "python3": {
            "reason": "Python 3 interpreter - scripts and applications",
            "common_pullers": ["glib", "mesa", "llvm", "many applications"],
            "explanation": "Python is used for build scripts, code generation, and as a runtime "
            "dependency for many applications.",
            "reduce": "Check if you can use packages without Python extensions/plugins.",
        },
        "systemd": {
            "reason": "System and service manager",
            "common_pullers": ["most services", "udev", "dbus", "networkmanager"],
            "explanation": "Systemd provides core system functionality on NixOS. "
            "Most services and system components depend on it.",
            "reduce": "Cannot be removed on standard NixOS - it's the init system.",
        },
        "bash": {
            "reason": "Bourne Again Shell - scripts everywhere",
            "common_pullers": ["stdenv", "activation scripts", "most packages"],
            "explanation": "Bash is the default shell for package scripts and system activation. "
            "Nearly every package uses bash scripts.",
            "reduce": "Cannot be avoided - fundamental to NixOS operation.",
        },
        "coreutils": {
            "reason": "GNU core utilities - basic commands",
            "common_pullers": ["stdenv", "all shell scripts", "system"],
            "explanation": "Provides essential commands like ls, cp, mv, etc. Required by virtually all packages.",
            "reduce": "Cannot be removed - fundamental utilities.",
        },
        "glibc": {
            "reason": "GNU C Library - system calls and basic functions",
            "common_pullers": ["all compiled programs", "dynamic linking"],
            "explanation": "The C library providing core functionality for all programs. "
            "Every compiled program links against it.",
            "reduce": "Use musl or static linking for specialized cases only.",
        },
        "openssl": {
            "reason": "Cryptography library",
            "common_pullers": ["curl", "git", "python", "nodejs", "many networked apps"],
            "explanation": "Provides SSL/TLS and general cryptography. Required by most network-enabled software.",
            "reduce": "Some packages can use alternative crypto libraries.",
        },
    }

    # Check if we have specific information
    if package_name.lower() in dependency_patterns:
        info = dependency_patterns[package_name.lower()]
        output = []
        output.append(f"WHY: {package_name}")
        output.append("━" * len(f"WHY: {package_name}"))
        output.append("")
        output.append(f"Reason: {info['reason']}")
        output.append("")
        output.append("Commonly pulled in by:")
        for puller in info["common_pullers"]:
            output.append(f"• {puller}")
        output.append("")
        output.append("EXPLANATION")
        output.append("━" * 11)
        output.append(info["explanation"])
        output.append("")
        output.append("TO REDUCE CLOSURE SIZE")
        output.append("━" * 22)
        output.append(info["reduce"])
        output.append("")
        output.append("NEXT STEPS:")
        output.append("━" * 11)
        output.append(f"• Check reverse dependencies: nix why-depends /run/current-system {package_name}")
        output.append(f"• Search for alternatives: search(query='{package_name} alternative')")
        output.append("• Minimize your configuration: remove unnecessary packages")

        return "\n".join(output)
    else:
        # Generic response for unknown packages
        output = []
        output.append(f"WHY: {package_name}")
        output.append("━" * len(f"WHY: {package_name}"))
        output.append("")
        output.append("This package might be installed because:")
        output.append("")
        output.append("COMMON REASONS")
        output.append("━" * 13)
        output.append("• Build dependency - needed to compile other packages")
        output.append("• Runtime dependency - required by installed programs")
        output.append("• Plugin/extension - provides functionality to other packages")
        output.append("• System component - part of NixOS base system")
        output.append("")
        output.append("TO INVESTIGATE")
        output.append("━" * 13)
        output.append("1. Check what depends on it:")
        output.append(f"   nix why-depends /run/current-system {package_name}")
        output.append("")
        output.append("2. Search for information:")
        output.append(f"   show(name='{package_name}') - see package details")
        output.append(f"   discourse_search(query='{package_name} dependency') - community insights")
        output.append("")
        output.append("3. Check if it's in your configuration:")
        output.append("   grep -r '{package_name}' /etc/nixos/")
        output.append("   grep '{package_name}' ~/.config/nixpkgs/home.nix")
        output.append("")
        output.append("NEXT STEPS:")
        output.append("━" * 11)
        output.append("• Use 'nix why-depends' for precise dependency chain")
        output.append("• Review your environment.systemPackages")
        output.append("• Check if packages have '...withoutX' variants")

        return "\n".join(output)


@mcp.tool()
async def install(
    package_name: Annotated[
        str | None,
        Field(description="Package name or index from search. If omitted, uses last searched package."),
    ] = None,
    method: Annotated[
        str | None,
        Field(
            description="Installation method: 'user' (nix-env), 'system' (configuration.nix), "
            "'shell' (nix-shell), or 'home' (home-manager). Auto-detected if not specified.",
            pattern="^(user|system|shell|home)$",
        ),
    ] = None,
) -> str:
    """Get exact installation commands for any package.

    WHAT IT DOES:
    • Verifies package exists before showing commands
    • Provides method-specific instructions
    • Auto-detects best installation method
    • Shows configuration examples

    USE THIS TO:
    • Install user packages: install("firefox")
    • System-wide install: install("firefox", method="system")
    • Home Manager: install("firefox", method="home")
    • Try first: install("firefox", method="shell")

    Args:
        package_name: Package to install
        method: How to install - 'user', 'system', 'shell', or 'home'

    Returns:
        Installation commands and configuration examples
    """
    # Handle context-aware package name
    actual_name = package_name
    if package_name is None:
        actual_name = context.get_recent_package()
        if not actual_name:
            return error(
                "No package name provided and no recent search results",
                "NO_CONTEXT",
                [
                    "search(query='firefox') - search for a package first",
                    "install(package_name='firefox') - or provide explicit name",
                ],
            )
    elif package_name and package_name.isdigit():
        # Handle index-based lookup
        index = int(package_name)
        result = context.get_result_by_index(index)
        if result:
            actual_name = result.get("_source", {}).get("package_pname", "")
            if not actual_name:
                return error(f"No package name found for index {index}", "NO_PACKAGE_NAME")
        else:
            return error(
                f"Invalid index {index}. Last search had {len(context.last_search_results)} results", "INVALID_INDEX"
            )

    # Auto-detect method if not specified
    if method is None:
        # Check environment to suggest appropriate method
        import os

        # If running as root or in /etc/nixos, suggest system
        if os.getuid() == 0 or os.getcwd().startswith("/etc/nixos"):
            method = "system"
        # If HOME_MANAGER_CONFIG is set, suggest home
        elif os.environ.get("HOME_MANAGER_CONFIG"):
            method = "home"
        # Default to user install
        else:
            method = "user"

    # First verify the package exists
    channels = get_channels()
    channel = "unstable"  # Default to unstable

    try:
        # Check if package exists
        field = "package_pname"
        query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {field: actual_name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            # Try to find similar packages
            closest_matches = []
            wildcard_query = {
                "bool": {"must": [{"term": {"type": "package"}}, {"wildcard": {"package_pname": f"*{actual_name}*"}}]}
            }
            similar_hits = es_query(channels[channel], wildcard_query, 10)
            if similar_hits:
                seen_names = set()
                for hit in similar_hits:
                    name = hit.get("_source", {}).get("package_pname", "")
                    if name and name not in seen_names:
                        seen_names.add(name)
                closest_matches = get_closest_matches(actual_name or "", list(seen_names), 3)

            suggestions = get_did_you_mean_suggestions(actual_name or "", "packages", closest_matches)
            return error(f"Package '{actual_name}' not found", "NOT_FOUND", suggestions)

        # Package exists, provide installation instructions
        content = []

        if method == "user":
            content.extend(
                [
                    "USER INSTALL (nix-env)",
                    "━" * 21,
                    "Install for current user only:",
                    f"  nix-env -iA nixpkgs.{actual_name}",
                    "",
                    "To uninstall later:",
                    f"  nix-env -e {actual_name}",
                    "",
                    "List installed packages:",
                    "  nix-env -q",
                ]
            )

        elif method == "system":
            content.extend(
                [
                    "SYSTEM INSTALL (configuration.nix)",
                    "━" * 33,
                    "Add to /etc/nixos/configuration.nix:",
                    "",
                    "  environment.systemPackages = with pkgs; [",
                    f"    {actual_name}",
                    "  ];",
                    "",
                    "Then rebuild:",
                    "  sudo nixos-rebuild switch",
                    "",
                    "This installs system-wide for all users.",
                ]
            )

        elif method == "shell":
            content.extend(
                [
                    "TEMPORARY SHELL (nix-shell)",
                    "━" * 26,
                    "Try without installing:",
                    f"  nix-shell -p {actual_name}",
                    "",
                    "Run a command directly:",
                    f"  nix-shell -p {actual_name} --run '{actual_name} --help'",
                    "",
                    "With multiple packages:",
                    f"  nix-shell -p {actual_name} git vim",
                ]
            )

        elif method == "home":
            content.extend(
                [
                    "HOME MANAGER INSTALL",
                    "━" * 19,
                    "Add to ~/.config/nixpkgs/home.nix:",
                    "",
                    "  home.packages = with pkgs; [",
                    f"    {actual_name}",
                    "  ];",
                    "",
                    "Then apply:",
                    "  home-manager switch",
                    "",
                    "Or search for program-specific options:",
                    f"  hm_search(query='{actual_name}')",
                ]
            )

        content.extend(["", "OTHER METHODS", "━" * 12])

        methods_to_show = [m for m in ["user", "system", "shell", "home"] if m != method]
        for m in methods_to_show:
            content.append(f"• For {m} install: install(package_name='{actual_name}', method='{m}')")

        next_steps = [
            f"• Try first: try_package(package_name='{actual_name}')",
            f"• Get details: show(name='{actual_name}')",
            f"• Check versions: versions(package_name='{actual_name}')",
            f"• Compare channels: compare(package_name='{actual_name}')",
        ]

        return format_tool_output("INSTALL", actual_name or "package", content, next_steps)

    except Exception as e:
        return error(str(e))


@mcp.tool(name="quick_start")
async def quick_start() -> str:
    """Quick start guide with practical examples.

    WHAT IT DOES:
    • Shows common task examples
    • Demonstrates tool workflows
    • Provides copy-paste commands
    • Gets you productive fast

    USE THIS TO:
    • Learn by example: quick_start()
    • See common workflows
    • Start using tools immediately

    Returns:
        Plain text guide with practical examples
    """
    return """NixOS MCP Quick Start Guide

COMMON TASKS WITH EXAMPLES:

1. Find a package:
   search(query="firefox")
   -> Returns: firefox (128.0.3), firefox-esr (115.13.0), etc.

2. Get package details:
   show(name="firefox")
   -> Returns: Version, description, homepage, license

3. Find what provides a command:
   which(package_name="rg")
   -> Returns: ripgrep provides 'rg'

4. Check available channels:
   channels()
   -> Returns: stable (24.05), unstable, etc.

5. Search configuration options:
   search(query="networking", search_type="options")
   -> Returns: networking.firewall.enable, networking.hostName, etc.

6. Find a specific version:
   versions(package_name="ruby")
   -> Returns: Version history with nixpkgs commits

7. Search Home Manager options:
   hm_search(query="git")
   -> Returns: programs.git.enable, programs.git.userName, etc.

8. Find community solutions:
   discourse_search(query="nvidia drivers")
   -> Returns: Forum discussions about nvidia setup

9. Try before installing:
   try_package(package_name="neovim")
   -> Returns: nix-shell command with instructions

10. Compare versions:
    compare(package_name="firefox")
    -> Returns: Version comparison between stable/unstable

TIPS:
• Use search() first - it's the primary discovery tool
• Try packages with try_package() before installing
• Compare channels with compare() for version differences
• Use which() when a command is missing
• Check discourse_search() for real-world solutions

NEXT STEPS:
After finding a package with search(), you can:
• Try it: try_package(package_name="firefox")
• Install: nix-env -iA nixpkgs.firefox
• Or add to configuration.nix: environment.systemPackages = [ pkgs.firefox ];

Type help() for the complete tool reference."""


@mcp.tool(name="try_package")
async def try_package(
    package_name: Annotated[str, Field(description="Package name to try. Examples: 'htop', 'neovim', 'ripgrep'")],
) -> str:
    """Try any package without installing it.

    WHAT IT DOES:
    • Creates temporary shell with package
    • Downloads if needed, but doesn't install
    • Leaves system completely unchanged
    • Perfect for testing before committing

    USE THIS TO:
    • Test packages: try_package("neovim")
    • Run one command: shown in output
    • Experiment safely before installing

    Args:
        package_name: Package to try (e.g., 'firefox', 'neovim')

    Returns:
        Shell command to try the package with instructions
    """
    # First verify the package exists
    channels = get_channels()
    channel = "unstable"  # Default to unstable for trying packages

    try:
        # Check if package exists
        field = "package_pname"
        query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {field: package_name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            # Try to find similar packages
            closest_matches = []
            wildcard_query = {
                "bool": {"must": [{"term": {"type": "package"}}, {"wildcard": {"package_pname": f"*{package_name}*"}}]}
            }
            similar_hits = es_query(channels[channel], wildcard_query, 10)
            if similar_hits:
                seen_names = set()
                for hit in similar_hits:
                    name = hit.get("_source", {}).get("package_pname", "")
                    if name and name not in seen_names:
                        seen_names.add(name)
                closest_matches = get_closest_matches(package_name, list(seen_names), 3)

            suggestions = get_did_you_mean_suggestions(package_name, "packages", closest_matches)
            return error(f"Package '{package_name}' not found", "NOT_FOUND", suggestions)

        # Package exists, provide try instructions
        content = [
            "Run this command:",
            f"  nix-shell -p {package_name}",
            "",
            "This will:",
            "• Download the package if needed",
            "• Start a new shell with the package available",
            "• Leave your system unchanged",
            "",
            "To exit:",
            "• Type 'exit' or press Ctrl+D",
            "",
            "TIP: Add --run '<command>' to run a specific command:",
            f"  nix-shell -p {package_name} --run '{package_name} --version'",
        ]

        next_steps = [
            f"• If you like it: nix-env -iA nixpkgs.{package_name}",
            f"• Or add to config: install(package_name='{package_name}')",
            f"• Check details: show(name='{package_name}')",
        ]

        return format_tool_output("TRY-PACKAGE", package_name, content, next_steps)

    except Exception as e:
        return error(str(e))


@mcp.tool()
async def compare(
    package_name: Annotated[
        str | None,
        Field(
            description="Package name to compare. Examples: 'firefox', 'postgresql', 'gcc'. "
            "If omitted, uses last searched package."
        ),
    ] = None,
    channel1: Annotated[
        str, Field(description="First channel to compare. Examples: 'stable', '25.05', '24.11'")
    ] = "stable",
    channel2: Annotated[
        str, Field(description="Second channel to compare. Examples: 'unstable', 'stable', '25.05'")
    ] = "unstable",
) -> str:
    """Compare package versions across different channels.

    WHAT IT DOES:
    • Shows version in each channel
    • Identifies version differences
    • Helps choose between stability and features
    • Works with any two channels

    USE THIS TO:
    • Check stable vs unstable: compare("firefox")
    • Compare specific channels: compare("postgresql", "24.11", "25.05")
    • Decide which channel to use for a package

    Args:
        package_name: Package to compare
        channel1: First channel (default: stable)
        channel2: Second channel (default: unstable)

    Returns:
        Comparison table with versions and changes
    """
    # Use context if package name not provided
    if not package_name:
        if context.last_package_name:
            package_name = context.last_package_name
        else:
            return error("Package name is required. Use search() first or provide package_name.")

    channels = get_channels()

    # Validate channels
    for ch in [channel1, channel2]:
        if ch not in channels:
            channel_suggestions = get_channel_suggestions(ch)
            return error(f"Invalid channel '{ch}'. {channel_suggestions}")

    try:
        # Query both channels
        field = "package_pname"
        query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {field: package_name}}]}}

        hits1 = es_query(channels[channel1], query, 1)
        hits2 = es_query(channels[channel2], query, 1)

        # Build comparison output
        content = [f"Package: {package_name}", f"Channels: {channel1} vs {channel2}", ""]

        # Channel 1 info
        content.append(f"CHANNEL: {channel1.upper()}")
        if hits1:
            src1 = hits1[0].get("_source", {})
            version1 = src1.get("package_pversion", "")
            desc1 = src1.get("package_description", "")
            content.append(f"   Version: {version1}")
            if desc1 and len(desc1) > 60:
                desc1 = desc1[:57] + "..."
            content.append(f"   {desc1}")
        else:
            content.append("   [Not available]")
            version1 = None

        content.append("")

        # Channel 2 info
        content.append(f"CHANNEL: {channel2.upper()}")
        if hits2:
            src2 = hits2[0].get("_source", {})
            version2 = src2.get("package_pversion", "")
            desc2 = src2.get("package_description", "")
            content.append(f"   Version: {version2}")
            if desc2 and len(desc2) > 60:
                desc2 = desc2[:57] + "..."
            content.append(f"   {desc2}")
        else:
            content.append("   [Not available]")
            version2 = None

        content.extend(["", "ANALYSIS", "━━━━━━━━"])

        if version1 and version2:
            if version1 == version2:
                content.append("✅ Same version in both channels")
            else:
                content.extend(["[Different versions]", f"   {channel1}: {version1}", f"   {channel2}: {version2}"])
        elif version1 and not version2:
            content.append(f"[Only available in {channel1}]")
        elif version2 and not version1:
            content.append(f"[Only available in {channel2}]")
        else:
            content.append("[Not found in either channel]")

        next_steps = []
        if version1 or version2:
            next_steps.extend(
                [
                    f'• Use versions(package_name="{package_name}") for full history',
                    f'• Use try_package(package_name="{package_name}") to test',
                ]
            )
            if version1 and version2 and version1 != version2:
                next_steps.extend(
                    [
                        "• Install specific version:",
                        f"  From {channel1}: nix-env -iA nixos-{channel1}.{package_name}",
                        f"  From {channel2}: nix-env -iA nixpkgs.{package_name}",
                    ]
                )
        else:
            next_steps.append(f'• Use search(query="{package_name}") to find similar packages')

        return format_tool_output("COMPARE", package_name, content, next_steps)

    except Exception as e:
        return error(str(e))


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
