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
CHANNELS = {
    "unstable": "latest-43-nixos-unstable",
    "stable": "latest-43-nixos-24.11",
    "24.11": "latest-43-nixos-24.11",
    "25.05": "latest-43-nixos-25.05",
    "beta": "latest-43-nixos-25.05",
}
HOME_MANAGER_URL = "https://nix-community.github.io/home-manager/options.xhtml"
DARWIN_URL = "https://nix-darwin.github.io/nix-darwin/manual/index.html"


def error(msg: str, code: str = "ERROR") -> str:
    """Format error as plain text."""
    # Ensure msg is always a string, even if empty
    msg = str(msg) if msg is not None else ""
    return f"Error ({code}): {msg}"


def es_query(index: str, query: dict, size: int = 20) -> List[dict]:
    """Execute Elasticsearch query."""
    try:
        resp = requests.post(
            f"{NIXOS_API}/{index}/_search", json={"query": query, "size": size}, auth=NIXOS_AUTH, timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])
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
                    name = dt.get_text(strip=True)
            else:
                # Darwin and fallback - use text content
                name = dt.get_text(strip=True)

            # Skip if it doesn't look like an option (must contain a dot)
            if "." not in name:
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
                    # Get first text node
                    description = dd.get_text(strip=True).split("\n")[0]

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
    if channel not in CHANNELS:
        return error(f"Invalid channel '{channel}'")
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

        hits = es_query(CHANNELS[channel], q, limit)

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
                # For programs, show the package that provides them
                programs = src.get("package_programs", [])
                if programs and query.lower() in [p.lower() for p in programs]:
                    pkg_name = src.get("package_pname", "")
                    results.append(f"• {query} (provided by {pkg_name})")
                    results.append("")

        return "\n".join(results).strip()

    except Exception as e:
        return error(str(e))


@mcp.tool()
def nixos_info(name: str, type: str = "package", channel: str = "unstable") -> str:
    """Get detailed info about a NixOS package or option."""
    if type not in ["package", "option"]:
        return error("Type must be 'package' or 'option'")
    if channel not in CHANNELS:
        return error(f"Invalid channel '{channel}'")

    try:
        # Exact match query with correct field names
        field = "package_pname" if type == "package" else "option_name.keyword"
        query = {"bool": {"must": [{"term": {"type": type}}, {"term": {field: name}}]}}
        hits = es_query(CHANNELS[channel], query, 1)

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
def nixos_stats(channel: str = "unstable") -> str:
    """Get NixOS statistics."""
    if channel not in CHANNELS:
        return error(f"Invalid channel '{channel}'")

    try:
        index = CHANNELS[channel]
        url = f"{NIXOS_API}/{index}/_count"

        # Get counts
        pkg_resp = requests.post(url, json={"query": {"term": {"type": "package"}}}, auth=NIXOS_AUTH, timeout=10)
        opt_resp = requests.post(url, json={"query": {"term": {"type": "option"}}}, auth=NIXOS_AUTH, timeout=10)

        pkg_count = pkg_resp.json().get("count", 0)
        opt_count = opt_resp.json().get("count", 0)

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
        options = parse_html_options(HOME_MANAGER_URL, name, "", 1)

        for opt in options:
            if opt["name"] == name:
                info = []
                info.append(f"Option: {name}")
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        return error(f"Option '{name}' not found", "NOT_FOUND")

    except Exception as e:
        return error(str(e))


@mcp.tool()
def home_manager_stats() -> str:
    """Get Home Manager statistics."""
    return """Home Manager statistics require parsing the full documentation.
Use home_manager_list_options to see available option categories."""


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
        options = parse_html_options(DARWIN_URL, name, "", 1)

        for opt in options:
            if opt["name"] == name:
                info = []
                info.append(f"Option: {name}")
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        return error(f"Option '{name}' not found", "NOT_FOUND")

    except Exception as e:
        return error(str(e))


@mcp.tool()
def darwin_stats() -> str:
    """Get nix-darwin statistics."""
    return """nix-darwin statistics require parsing the full documentation.
Use darwin_list_options to see available option categories."""


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


if __name__ == "__main__":
    mcp.run()
