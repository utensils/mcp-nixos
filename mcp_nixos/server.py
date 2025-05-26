#!/usr/bin/env python3
"""MCP-NixOS Server - Model Context Protocol tools for NixOS, Home Manager, and nix-darwin.

Provides search and query capabilities for:
- NixOS packages, options, and programs via Elasticsearch API
- Home Manager configuration options via HTML documentation parsing
- nix-darwin (macOS) configuration options via HTML documentation parsing

All responses are formatted as human-readable plain text for optimal LLM interaction.
"""

from mcp.server.fastmcp import FastMCP
import requests
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


class APIError(Exception):
    """Custom exception for API-related errors."""


class DocumentParseError(Exception):
    """Custom exception for document parsing errors."""


# Note: formatters.py functions were inlined for simplicity
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

    def __init__(self):
        """Initialize empty cache."""
        self.available_channels = None
        self.resolved_channels = None

    def get_available(self) -> Dict[str, str]:
        """Get available channels, discovering if needed."""
        if self.available_channels is None:
            self.available_channels = self._discover_available_channels()
        return self.available_channels

    def get_resolved(self) -> Dict[str, str]:
        """Get resolved channel mappings, resolving if needed."""
        if self.resolved_channels is None:
            self.resolved_channels = self._resolve_channels()
        return self.resolved_channels

    def _discover_available_channels(self) -> Dict[str, str]:
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

    def _resolve_channels(self) -> Dict[str, str]:
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
            version_patterns = {}
            for major, minor, version, pattern, count in stable_candidates:
                if version not in version_patterns or count > version_patterns[version][1]:
                    version_patterns[version] = (pattern, count)

            for version, (pattern, count) in version_patterns.items():
                resolved[version] = pattern

        # Add beta (alias for stable)
        if "stable" in resolved:
            resolved["beta"] = resolved["stable"]

        return resolved


# Create a single instance of the cache
channel_cache = ChannelCache()


def error(msg: str, code: str = "ERROR") -> str:
    """Format error as plain text."""
    # Ensure msg is always a string, even if empty
    msg = str(msg) if msg is not None else ""
    return f"Error ({code}): {msg}"


def get_channels() -> Dict[str, str]:
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


def es_query(index: str, query: dict, size: int = 20) -> List[dict]:
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
                return hits.get("hits", [])
        return []
    except requests.Timeout as exc:
        raise APIError("API error: Connection timed out") from exc
    except requests.HTTPError as exc:
        raise APIError(f"API error: {str(exc)}") from exc
    except Exception as exc:
        raise APIError(f"API error: {str(exc)}") from exc


def parse_html_options(url: str, query: str = "", prefix: str = "", limit: int = 100) -> List[Dict[str, str]]:
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
def nixos_search(query: str, search_type: str = "packages", limit: int = 20, channel: str = "unstable") -> str:
    """Search NixOS packages, options, or programs.

    Args:
        query: Search term to look for
        search_type: Type of search - "packages", "options", "programs", or "flakes"
        limit: Maximum number of results to return (1-100)
        channel: NixOS channel to search in (e.g., "unstable", "stable", "25.05")

    Returns:
        Plain text results with bullet points or error message
    """
    if search_type not in ["packages", "options", "programs", "flakes"]:
        return error(f"Invalid type '{search_type}'")
    channels = get_channels()
    if channel not in channels:
        suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {suggestions}")
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    # Redirect flakes to dedicated function
    if search_type == "flakes":
        return nixos_flakes_search(query, limit)

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

        # Format results as plain text
        if not hits:
            return f"No {search_type} found matching '{query}'"

        results = []
        results.append(f"Found {len(hits)} {search_type} matching '{query}':\n")

        for hit in hits:
            src = hit.get("_source", {})
            if search_type == "packages":
                name = src.get("package_pname", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")
                results.append(f"• {name} ({version})")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            elif search_type == "options":
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
                    results.append(f"  Type: {opt_type}")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            else:  # programs
                programs = src.get("package_programs", [])
                pkg_name = src.get("package_pname", "")

                # Check if query matches any program exactly (case-insensitive)
                query_lower = query.lower()
                matched_programs = [p for p in programs if p.lower() == query_lower]

                for prog in matched_programs:
                    results.append(f"• {prog} (provided by {pkg_name})")
                    results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool()
def nixos_info(name: str, type: str = "package", channel: str = "unstable") -> str:  # pylint: disable=redefined-builtin
    """Get detailed info about a NixOS package or option.

    Args:
        name: Name of the package or option to look up
        type: Type of lookup - "package" or "option"
        channel: NixOS channel to search in (e.g., "unstable", "stable", "25.05")

    Returns:
        Plain text details about the package/option or error message
    """
    info_type = type  # Avoid shadowing built-in
    if info_type not in ["package", "option"]:
        return error("Type must be 'package' or 'option'")
    channels = get_channels()
    if channel not in channels:
        suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {suggestions}")

    try:
        # Exact match query with correct field names
        field = "package_pname" if info_type == "package" else "option_name"
        query = {"bool": {"must": [{"term": {"type": info_type}}, {"term": {field: name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            return error(f"{info_type.capitalize()} '{name}' not found", "NOT_FOUND")

        src = hits[0].get("_source", {})

        if info_type == "package":
            info = []
            info.append(f"Package: {src.get('package_pname', '')}")
            info.append(f"Version: {src.get('package_pversion', '')}")

            desc = src.get("package_description", "")
            if desc:
                info.append(f"Description: {desc}")

            homepage = src.get("package_homepage", [])
            if homepage:
                if isinstance(homepage, list):
                    homepage = homepage[0] if homepage else ""
                info.append(f"Homepage: {homepage}")

            licenses = src.get("package_license_set", [])
            if licenses:
                info.append(f"License: {', '.join(licenses)}")

            return "\n".join(info)

        # Option type
        info = []
        info.append(f"Option: {src.get('option_name', '')}")

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

        return "\n".join(info)

    except Exception as e:
        return error(str(e))


@mcp.tool()
def nixos_channels() -> str:
    """List available NixOS channels with their status.

    Returns:
        Plain text list showing channel names, versions, and availability
    """
    try:
        # Get resolved channels and available raw data
        configured = get_channels()
        available = channel_cache.get_available()

        results = []
        results.append("NixOS Channels (auto-discovered):\n")

        # Show user-friendly channel names
        for name, index in sorted(configured.items()):
            status = "✓ Available" if index in available else "✗ Unavailable"
            doc_count = available.get(index, "Unknown")

            # Mark stable channel clearly
            label = f"• {name}"
            if name == "stable":
                # Extract version from index
                parts = index.split("-")
                if len(parts) >= 4:
                    version = parts[3]
                    label = f"• {name} (current: {version})"

            results.append(f"{label} → {index}")
            if index in available:
                results.append(f"  Status: {status} ({doc_count})")
            else:
                results.append(f"  Status: {status}")
            results.append("")

        # Show additional discovered channels not in our mapping
        discovered_only = set(available.keys()) - set(configured.values())
        if discovered_only:
            results.append("Additional available channels:")
            for index in sorted(discovered_only):
                results.append(f"• {index} ({available[index]})")

        # Add deprecation warnings
        results.append("\nNote: Channels are dynamically discovered.")
        results.append("'stable' always points to the current stable release.")

        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


@mcp.tool()
def nixos_stats(channel: str = "unstable") -> str:
    """Get NixOS statistics for a channel.

    Args:
        channel: NixOS channel to get stats for (e.g., "unstable", "stable", "25.05")

    Returns:
        Plain text statistics including package/option counts
    """
    channels = get_channels()
    if channel not in channels:
        suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {suggestions}")

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
            return error("Failed to retrieve statistics")

        return f"""NixOS Statistics for {channel} channel:
• Packages: {pkg_count:,}
• Options: {opt_count:,}"""

    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_search(query: str, limit: int = 20) -> str:
    """Search Home Manager configuration options.

    Searches through available Home Manager options by name and description.

    Args:
        query: The search query string to match against option names and descriptions
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        Plain text list of matching options with name, type, and description
    """
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

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

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_info(name: str) -> str:
    """Get detailed information about a specific Home Manager option.

    Requires an exact option name match. If not found, suggests similar options.

    Args:
        name: The exact option name (e.g., 'programs.git.enable')

    Returns:
        Plain text with option details (name, type, description) or error with suggestions
    """
    try:
        # Search more broadly first
        options = parse_html_options(HOME_MANAGER_URL, name, "", 100)

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
                    + f"\n\nTip: Use home_manager_options_by_prefix('{name}') to browse all options with this prefix.",
                    "NOT_FOUND",
                )

        return error(
            f"Option '{name}' not found.\n"
            + f"Tip: Use home_manager_options_by_prefix('{name}') to browse available options.",
            "NOT_FOUND",
        )

    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_stats() -> str:
    """Get statistics about Home Manager options.

    Retrieves overall statistics including total options, categories, and top categories.

    Returns:
        Plain text summary with total options, category count, and top 5 categories
    """
    try:
        # Parse all options to get statistics
        options = parse_html_options(HOME_MANAGER_URL, limit=5000)

        if not options:
            return error("Failed to fetch Home Manager statistics")

        # Count categories
        categories = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        # Count types
        types = {}
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
  - programs: {categories.get('programs', 0):,} options
  - services: {categories.get('services', 0):,} options
  - home: {categories.get('home', 0):,} options
  - wayland: {categories.get('wayland', 0):,} options
  - xsession: {categories.get('xsession', 0):,} options"""
    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_list_options() -> str:
    """List all Home Manager option categories.

    Enumerates all top-level categories with their option counts.

    Returns:
        Plain text list of categories sorted alphabetically with option counts
    """
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(HOME_MANAGER_URL, limit=4000)
        categories = {}

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


@mcp.tool()
def home_manager_options_by_prefix(option_prefix: str) -> str:
    """Get Home Manager options matching a specific prefix.

    Useful for browsing options under a category or finding exact option names.

    Args:
        option_prefix: The prefix to match (e.g., 'programs.git' or 'services')

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


@mcp.tool()
def darwin_search(query: str, limit: int = 20) -> str:
    """Search nix-darwin (macOS) configuration options.

    Searches through available nix-darwin options by name and description.

    Args:
        query: The search query string to match against option names and descriptions
        limit: Maximum number of results to return (default: 20, max: 100)

    Returns:
        Plain text list of matching options with name, type, and description
    """
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    try:
        options = parse_html_options(DARWIN_URL, query, "", limit)

        if not options:
            return f"No nix-darwin options found matching '{query}'"

        results = []
        results.append(f"Found {len(options)} nix-darwin options matching '{query}':\n")

        for opt in options:
            results.append(f"• {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool()
def darwin_info(name: str) -> str:
    """Get detailed information about a specific nix-darwin option.

    Requires an exact option name match. If not found, suggests similar options.

    Args:
        name: The exact option name (e.g., 'system.defaults.dock.autohide')

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
                    + f"\n\nTip: Use darwin_options_by_prefix('{name}') to browse all options with this prefix.",
                    "NOT_FOUND",
                )

        return error(
            f"Option '{name}' not found.\n"
            + f"Tip: Use darwin_options_by_prefix('{name}') to browse available options.",
            "NOT_FOUND",
        )

    except Exception as e:
        return error(str(e))


@mcp.tool()
def darwin_stats() -> str:
    """Get statistics about nix-darwin options.

    Retrieves overall statistics including total options, categories, and top categories.

    Returns:
        Plain text summary with total options, category count, and top 5 categories
    """
    try:
        # Parse all options to get statistics
        options = parse_html_options(DARWIN_URL, limit=3000)

        if not options:
            return error("Failed to fetch nix-darwin statistics")

        # Count categories
        categories = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        # Count types
        types = {}
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
  - services: {categories.get('services', 0):,} options
  - system: {categories.get('system', 0):,} options
  - launchd: {categories.get('launchd', 0):,} options
  - programs: {categories.get('programs', 0):,} options
  - homebrew: {categories.get('homebrew', 0):,} options"""
    except Exception as e:
        return error(str(e))


@mcp.tool()
def darwin_list_options() -> str:
    """List all nix-darwin option categories.

    Enumerates all top-level categories with their option counts.

    Returns:
        Plain text list of categories sorted alphabetically with option counts
    """
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(DARWIN_URL, limit=2000)
        categories = {}

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


@mcp.tool()
def darwin_options_by_prefix(option_prefix: str) -> str:
    """Get nix-darwin options matching a specific prefix.

    Useful for browsing options under a category or finding exact option names.

    Args:
        option_prefix: The prefix to match (e.g., 'system.defaults' or 'services')

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
def nixos_flakes_stats() -> str:
    """Get statistics about available NixOS flakes.

    Retrieves statistics from the flake search index including total packages,
    unique repositories, flake types, and top contributors.

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
        type_counts = {}
        contributor_counts = {}

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


@mcp.tool()
def nixos_flakes_search(query: str, limit: int = 20, channel: str = "unstable") -> str:
    """Search NixOS flakes by name, description, owner, or repository.

    Searches the flake index for community-contributed packages and configurations.
    Flakes are indexed separately from official packages.

    Args:
        query: The search query (flake name, description, owner, or repository)
        limit: Maximum number of results to return (default: 20, max: 100)
        channel: Ignored - flakes use a separate indexing system

    Returns:
        Plain text list of unique flakes with their packages and metadata
    """
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    try:
        # Use the same alias as the web UI to get only flake packages
        flake_index = "latest-43-group-manual"

        # Build query for flakes
        if query.strip() == "" or query == "*":
            # Empty or wildcard query - get all flakes
            q = {"match_all": {}}
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

        # Format results as plain text
        if not hits:
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

        # Build results
        results = []
        # Show both total hits and unique flakes
        if total > len(flakes):
            results.append(f"Found {total:,} total matches ({len(flakes)} unique flakes) matching '{query}':\n")
        else:
            results.append(f"Found {len(flakes)} unique flakes matching '{query}':\n")

        for flake in flakes.values():
            results.append(f"• {flake['name']}")
            if flake.get("owner") and flake.get("repo"):
                results.append(
                    f"  Repository: {flake['owner']}/{flake['repo']}"
                    + (f" ({flake['type']})" if flake.get("type") else "")
                )
            elif flake.get("url"):
                results.append(f"  URL: {flake['url']}")
            if flake.get("description"):
                desc = flake["description"]
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                results.append(f"  {desc}")
            if flake["packages"]:
                # Show max 5 packages, sorted
                packages = sorted(list(flake["packages"]))[:5]
                if len(flake["packages"]) > 5:
                    results.append(f"  Packages: {', '.join(packages)}, ... ({len(flake['packages'])} total)")
                else:
                    results.append(f"  Packages: {', '.join(packages)}")
            results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


def _version_key(version_str: str) -> tuple:
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
        return tuple(numeric_parts)
    except Exception:
        return (0, 0, 0)


def _format_nixhub_found_version(package_name: str, version: str, found_version: Dict) -> str:
    """Format a found version for display."""
    results = []
    results.append(f"✓ Found {package_name} version {version}\n")

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


def _format_nixhub_release(release: Dict, package_name: Optional[str] = None) -> List[str]:
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


@mcp.tool()
def nixhub_package_versions(package_name: str, limit: int = 10) -> str:
    """Get version history and nixpkgs commit hashes for a specific package from NixHub.io.

    Use this tool when users need specific package versions or commit hashes for reproducible builds.

    Args:
        package_name: Name of the package to query (e.g., "firefox", "python")
        limit: Maximum number of versions to return (default: 10, max: 50)

    Returns:
        Plain text with package info and version history including commit hashes
    """
    # Validate inputs
    if not package_name or not package_name.strip():
        return error("Package name is required")

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

        # Add usage hint
        if shown_releases and any(r.get("platforms", [{}])[0].get("commit_hash") for r in shown_releases):
            results.append("To use a specific version in your Nix configuration:")
            results.append("1. Pin nixpkgs to the commit hash")
            results.append("2. Use the attribute path to install the package")

        return "\n".join(results).strip()

    except requests.Timeout:
        return error("Request to NixHub timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Network error accessing NixHub: {str(e)}", "NETWORK_ERROR")
    except ValueError as e:
        return error(f"Failed to parse NixHub response: {str(e)}", "PARSE_ERROR")
    except Exception as e:
        return error(f"Unexpected error: {str(e)}")


@mcp.tool()
def nixhub_find_version(package_name: str, version: str) -> str:
    """Find a specific version of a package in NixHub with smart search.

    Automatically searches with increasing limits to find the requested version.

    Args:
        package_name: Name of the package to query (e.g., "ruby", "python")
        version: Specific version to find (e.g., "2.6.7", "3.5.9")

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
    all_versions = []

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
    results.append(f"✗ {package_name} version {version} not found in NixHub\n")

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


if __name__ == "__main__":
    mcp.run()
