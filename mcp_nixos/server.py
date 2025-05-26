#!/usr/bin/env python3
"""MCP-NixOS Server - Simple, direct implementation."""

from mcp.server.fastmcp import FastMCP
import requests
from typing import Dict, List
from bs4 import BeautifulSoup

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

# Cache for discovered channels and resolved mappings
_available_channels_cache = None
_resolved_channels_cache = None
HOME_MANAGER_URL = "https://nix-community.github.io/home-manager/options.xhtml"
DARWIN_URL = "https://nix-darwin.github.io/nix-darwin/manual/index.html"


def error(msg: str, code: str = "ERROR") -> str:
    """Format error as plain text."""
    # Ensure msg is always a string, even if empty
    msg = str(msg) if msg is not None else ""
    return f"Error ({code}): {msg}"


def discover_available_channels() -> Dict[str, str]:
    """Discover available NixOS channels by testing API patterns."""
    global _available_channels_cache

    if _available_channels_cache is not None:
        return _available_channels_cache

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

    _available_channels_cache = available
    return available


def resolve_channels() -> Dict[str, str]:
    """Resolve user-friendly channel names to actual indices."""
    global _resolved_channels_cache

    if _resolved_channels_cache is not None:
        return _resolved_channels_cache

    available = discover_available_channels()
    resolved = {}

    # Find unstable (should be consistent)
    unstable_pattern = None
    for pattern in available.keys():
        if "unstable" in pattern:
            unstable_pattern = pattern
            break

    if unstable_pattern:
        resolved["unstable"] = unstable_pattern

    # Find stable release (highest version number with most documents)
    stable_candidates = []
    for pattern in available.keys():
        if "unstable" not in pattern:
            # Extract version (e.g., "25.05" from "latest-43-nixos-25.05")
            parts = pattern.split("-")
            if len(parts) >= 4:
                version = parts[3]  # "25.05"
                try:
                    # Parse version for comparison (25.05 -> 25.05)
                    major, minor = map(int, version.split("."))
                    count_str = available[pattern]
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

    _resolved_channels_cache = resolved
    return resolved


def get_channels() -> Dict[str, str]:
    """Get current channel mappings (cached and resolved)."""
    return resolve_channels()


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
    except requests.Timeout:
        raise Exception("API error: Connection timed out")
    except requests.HTTPError as e:
        raise Exception(f"API error: {str(e)}")
    except Exception as e:
        raise Exception(f"API error: {str(e)}")


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
    except Exception as e:
        raise Exception(f"Failed to fetch docs: {str(e)}")


@mcp.tool()
def nixos_search(query: str, type: str = "packages", limit: int = 20, channel: str = "unstable") -> str:
    """Search NixOS packages, options, or programs."""
    if type not in ["packages", "options", "programs"]:
        return error(f"Invalid type '{type}'")
    channels = get_channels()
    if channel not in channels:
        suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {suggestions}")
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    try:
        # Build query with correct field names
        if type == "packages":
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
        elif type == "options":
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
            return f"No {type} found matching '{query}'"

        results = []
        results.append(f"Found {len(hits)} {type} matching '{query}':\n")

        for hit in hits:
            src = hit.get("_source", {})
            if type == "packages":
                name = src.get("package_pname", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")
                results.append(f"• {name} ({version})")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            elif type == "options":
                name = src.get("option_name", "")
                opt_type = src.get("option_type", "")
                desc = src.get("option_description", "")
                # Strip HTML tags from description
                if desc and "<rendered-html>" in desc:
                    # Remove outer rendered-html tags
                    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                    # Remove common HTML tags
                    import re

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
def nixos_info(name: str, type: str = "package", channel: str = "unstable") -> str:
    """Get detailed info about a NixOS package or option."""
    if type not in ["package", "option"]:
        return error("Type must be 'package' or 'option'")
    channels = get_channels()
    if channel not in channels:
        suggestions = get_channel_suggestions(channel)
        return error(f"Invalid channel '{channel}'. {suggestions}")

    try:
        # Exact match query with correct field names
        field = "package_pname" if type == "package" else "option_name"
        query = {"bool": {"must": [{"term": {"type": type}}, {"term": {field: name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            return error(f"{type.capitalize()} '{name}' not found", "NOT_FOUND")

        src = hits[0].get("_source", {})

        if type == "package":
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
        else:
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
                    import re

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
    """List available NixOS channels with their status."""
    try:
        # Get resolved channels and available raw data
        configured = get_channels()
        available = discover_available_channels()

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
    """Get NixOS statistics."""
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
    """Search Home Manager options."""
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
    """Get Home Manager option details."""
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
    """Get Home Manager statistics."""
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
    """List Home Manager categories."""
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(HOME_MANAGER_URL, limit=4000)
        categories = {}

        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        results = []
        results.append(f"Home Manager option categories ({len(categories)} total):\n")

        for cat, count in sorted(categories.items()):
            results.append(f"• {cat} ({count} options)")

        return "\n".join(results)

    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_options_by_prefix(option_prefix: str) -> str:
    """Get Home Manager options by prefix."""
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
    """Search nix-darwin options."""
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
    """Get nix-darwin option details."""
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
    """Get nix-darwin statistics."""
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
    """List nix-darwin categories."""
    try:
        # Get more options to see all categories (default 100 is too few)
        options = parse_html_options(DARWIN_URL, limit=2000)
        categories = {}

        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        results = []
        results.append(f"nix-darwin option categories ({len(categories)} total):\n")

        for cat, count in sorted(categories.items()):
            results.append(f"• {cat} ({count} options)")

        return "\n".join(results)

    except Exception as e:
        return error(str(e))


@mcp.tool()
def darwin_options_by_prefix(option_prefix: str) -> str:
    """Get nix-darwin options by prefix."""
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
    """Get statistics about available flakes in the search index."""
    try:
        # Flakes are indexed in separate indices with pattern group-*-manual-*
        flake_index = "group-43-manual-*"  # Same pattern as flakes_search
        
        # Get total count of all flakes
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_count",
                json={"query": {"match_all": {}}},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            total_docs = resp.json().get("count", 0)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return error("Flake indices not found. Flake search may be temporarily unavailable.")
            raise
        
        # Get count of unique flakes by aggregating on flake_name
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={
                    "size": 0,
                    "aggs": {
                        "unique_flakes": {
                            "cardinality": {
                                "field": "flake_name.keyword",
                                "precision_threshold": 10000
                            }
                        },
                        "flake_types": {
                            "terms": {
                                "field": "flake_resolved.type.keyword",
                                "size": 20
                            }
                        },
                        "top_owners": {
                            "terms": {
                                "field": "flake_resolved.owner.keyword",
                                "size": 10
                            }
                        }
                    }
                },
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            aggs = data.get("aggregations", {})
            unique_count = aggs.get("unique_flakes", {}).get("value", 0)
            
            # Get type distribution
            types = aggs.get("flake_types", {}).get("buckets", [])
            type_info = []
            for t in types[:5]:  # Top 5 types
                type_name = t.get("key", "unknown")
                count = t.get("doc_count", 0)
                if type_name:
                    type_info.append(f"  - {type_name}: {count:,}")
            
            # Get top owners
            owners = aggs.get("top_owners", {}).get("buckets", [])
            owner_info = []
            for o in owners[:5]:  # Top 5 owners
                owner_name = o.get("key", "")
                count = o.get("doc_count", 0)
                if owner_name:
                    owner_info.append(f"  - {owner_name}: {count:,} packages")
            
        except Exception:
            # Fallback if aggregations fail
            unique_count = 0
            type_info = []
            owner_info = []
        
        # Build statistics
        results = []
        results.append("NixOS Flakes Statistics:")
        results.append(f"• Total indexed documents: {total_docs:,}")
        if unique_count > 0:
            results.append(f"• Unique flakes: ~{unique_count:,}")
        
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

    Note: Flakes are indexed separately from packages/options. Channel parameter
    is ignored as flakes use a different indexing system.
    """
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    try:
        # Flakes are indexed in separate indices with pattern group-*-manual-*
        # We search across all of them
        flake_index = "group-43-manual-*"  # Updated to use version 43

        # Build query for flakes
        if query.strip() == "" or query == "*":
            # Empty or wildcard query - get all flakes
            q = {"match_all": {}}
        else:
            # Search query with multiple fields
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
                        {"term": {"flake_resolved.owner": {"value": query.lower(), "boost": 2}}},
                        {"term": {"flake_resolved.repo": {"value": query.lower(), "boost": 2}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

        # Execute search directly against flake indices
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={"query": q, "size": limit * 5, "track_total_hits": True},  # Get more results
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
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


if __name__ == "__main__":
    mcp.run()
