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

import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP


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

# Nixvim options via NuschtOS search infrastructure (paginated, ~300 options per chunk)
# Credit: https://github.com/NuschtOS/search - Simple and fast static-page NixOS option search
NIXVIM_META_BASE = "https://nix-community.github.io/nixvim/search/meta"


class ChannelCache:
    """Cache for discovered channels and resolved mappings."""

    def __init__(self) -> None:
        self.available_channels: dict[str, str] | None = None
        self.resolved_channels: dict[str, str] | None = None
        self.using_fallback: bool = False

    def get_available(self) -> dict[str, str]:
        if self.available_channels is None:
            self.available_channels = self._discover_available_channels()
        return self.available_channels if self.available_channels is not None else {}

    def get_resolved(self) -> dict[str, str]:
        if self.resolved_channels is None:
            self.resolved_channels = self._resolve_channels()
        return self.resolved_channels if self.resolved_channels is not None else {}

    def _discover_available_channels(self) -> dict[str, str]:
        generations = [43, 44, 45, 46]
        versions = ["unstable", "25.05", "25.11", "26.05", "26.11"]
        available = {}
        for gen in generations:
            for version in versions:
                pattern = f"latest-{gen}-nixos-{version}"
                try:
                    resp = requests.post(
                        f"{NIXOS_API}/{pattern}/_count",
                        json={"query": {"match_all": {}}},
                        auth=NIXOS_AUTH,
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        count = resp.json().get("count", 0)
                        if count > 0:
                            available[pattern] = f"{count:,} documents"
                except Exception:
                    continue
        return available

    def _resolve_channels(self) -> dict[str, str]:
        available = self.get_available()
        if not available:
            self.using_fallback = True
            return FALLBACK_CHANNELS.copy()

        resolved = {}
        unstable_pattern = None
        for pattern in available:
            if "unstable" in pattern:
                unstable_pattern = pattern
                break
        if unstable_pattern:
            resolved["unstable"] = unstable_pattern

        stable_candidates = []
        for pattern, count_str in available.items():
            if "unstable" not in pattern:
                parts = pattern.split("-")
                if len(parts) >= 4:
                    version = parts[3]
                    try:
                        major, minor = map(int, version.split("."))
                        count = int(count_str.replace(",", "").replace(" documents", ""))
                        stable_candidates.append((major, minor, version, pattern, count))
                    except (ValueError, IndexError):
                        continue

        if stable_candidates:
            stable_candidates.sort(key=lambda x: (x[0], x[1], x[4]), reverse=True)
            current_stable = stable_candidates[0]
            resolved["stable"] = current_stable[3]
            resolved[current_stable[2]] = current_stable[3]

            version_patterns: dict[str, tuple[str, int]] = {}
            for _major, _minor, version, pattern, count in stable_candidates:
                if version not in version_patterns or count > version_patterns[version][1]:
                    version_patterns[version] = (pattern, count)
            for version, (pattern, _count) in version_patterns.items():
                resolved[version] = pattern

        if "stable" in resolved:
            resolved["beta"] = resolved["stable"]

        if not resolved:
            self.using_fallback = True
            return FALLBACK_CHANNELS.copy()
        return resolved


channel_cache = ChannelCache()


class NixvimCache:
    """Cache for Nixvim options fetched from NuschtOS meta JSON (paginated)."""

    def __init__(self) -> None:
        self.options: list[dict[str, Any]] | None = None

    def get_options(self) -> list[dict[str, Any]]:
        """Fetch and cache all Nixvim options from NuschtOS meta JSON chunks."""
        if self.options is not None:
            return self.options

        try:
            all_options: list[dict[str, Any]] = []
            chunk_id = 0

            while True:
                url = f"{NIXVIM_META_BASE}/{chunk_id}.json"
                resp = requests.get(url, timeout=30)

                if resp.status_code == 404:
                    break  # No more chunks

                resp.raise_for_status()
                chunk_data = resp.json()

                if isinstance(chunk_data, list):
                    all_options.extend(chunk_data)
                else:
                    break  # Unexpected format

                chunk_id += 1

            self.options = all_options
            return self.options
        except requests.Timeout as exc:
            raise APIError("Timeout fetching Nixvim options") from exc
        except requests.RequestException as exc:
            raise APIError(f"Failed to fetch Nixvim options: {exc}") from exc
        except Exception as exc:
            raise APIError(f"Failed to parse Nixvim options: {exc}") from exc


nixvim_cache = NixvimCache()


def strip_html(html: str | None) -> str:
    """Strip HTML tags and clean up text for plain text output."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")
    # Clean up whitespace
    text = " ".join(text.split())
    return text.strip()


def error(msg: str, code: str = "ERROR") -> str:
    msg = str(msg) if msg is not None else ""
    return f"Error ({code}): {msg}"


def get_channels() -> dict[str, str]:
    return channel_cache.get_resolved()


def validate_channel(channel: str) -> bool:
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
    channels = get_channels()
    available = list(channels.keys())
    suggestions = []
    invalid_lower = invalid_channel.lower()
    for channel in available:
        if invalid_lower in channel.lower() or channel.lower() in invalid_lower:
            suggestions.append(channel)
    if not suggestions:
        common = ["unstable", "stable", "beta"]
        version_channels = [ch for ch in available if "." in ch and ch.replace(".", "").isdigit()]
        common.extend(version_channels[:2])
        suggestions = [ch for ch in common if ch in available]
        if not suggestions:
            suggestions = available[:4]
    return f"Available channels: {', '.join(suggestions)}"


def es_query(index: str, query: dict[str, Any], size: int = 20) -> list[dict[str, Any]]:
    try:
        resp = requests.post(
            f"{NIXOS_API}/{index}/_search", json={"query": query, "size": size}, auth=NIXOS_AUTH, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
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
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        options = []
        dts = soup.find_all("dt")

        for dt in dts:
            name = ""
            if "home-manager" in url:
                anchor = dt.find("a", id=True)
                if anchor:
                    anchor_id = anchor.get("id", "")
                    if anchor_id.startswith("opt-"):
                        name = anchor_id[4:]
                        name = name.replace("_name_", "<name>")
                else:
                    name_elem = dt.find(string=True, recursive=False)
                    if name_elem:
                        name = name_elem.strip()
                    else:
                        name = dt.get_text(strip=True)
            else:
                name = dt.get_text(strip=True)

            if "." not in name and len(name.split()) > 1:
                continue
            if query and query.lower() not in name.lower():
                continue
            if prefix and not (name.startswith(prefix + ".") or name == prefix):
                continue

            dd = dt.find_next_sibling("dd")
            if dd:
                desc_elem = dd.find("p")
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                else:
                    text = dd.get_text(strip=True)
                    description = text.split("\n")[0] if text else ""

                type_info = ""
                type_elem = dd.find("span", class_="term")
                if type_elem and "Type:" in type_elem.get_text():
                    type_info = type_elem.get_text(strip=True).replace("Type:", "").strip()
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


# =============================================================================
# Internal implementation functions (not exposed as MCP tools)
# =============================================================================


def _search_nixos(query: str, search_type: str, limit: int, channel: str) -> str:
    """Search NixOS packages, options, or programs via Elasticsearch."""
    if search_type == "flakes":
        # Delegate to flakes search
        return _search_flakes(query, limit)

    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
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
        if not hits:
            return f"No {search_type} found matching '{query}'"

        results = [f"Found {len(hits)} {search_type} matching '{query}':\n"]
        for hit in hits:
            src = hit.get("_source", {})
            if search_type == "packages":
                name = src.get("package_pname", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")
                results.append(f"* {name} ({version})")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            elif search_type == "options":
                name = src.get("option_name", "")
                opt_type = src.get("option_type", "")
                desc = src.get("option_description", "")
                if desc and "<rendered-html>" in desc:
                    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                    desc = re.sub(r"<[^>]+>", "", desc).strip()
                results.append(f"* {name}")
                if opt_type:
                    results.append(f"  Type: {opt_type}")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            else:  # programs
                programs = src.get("package_programs", [])
                pkg_name = src.get("package_pname", "")
                query_lower = query.lower()
                matched_programs = [p for p in programs if p.lower() == query_lower]
                for prog in matched_programs:
                    results.append(f"* {prog} (provided by {pkg_name})")
                    results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _search_home_manager(query: str, limit: int) -> str:
    """Search Home Manager options by parsing HTML documentation."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, query, "", limit)
        if not options:
            return f"No Home Manager options found matching '{query}'"
        results = [f"Found {len(options)} Home Manager options matching '{query}':\n"]
        for opt in options:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _search_darwin(query: str, limit: int) -> str:
    """Search nix-darwin options by parsing HTML documentation."""
    try:
        options = parse_html_options(DARWIN_URL, query, "", limit)
        if not options:
            return f"No nix-darwin options found matching '{query}'"
        results = [f"Found {len(options)} nix-darwin options matching '{query}':\n"]
        for opt in options:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _search_flakes(query: str, limit: int) -> str:
    """Search NixOS flakes by name or description."""
    try:
        flake_index = FLAKE_INDEX
        if query.strip() == "" or query == "*":
            q: dict[str, Any] = {"match_all": {}}
        else:
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
                    ],
                    "minimum_should_match": 1,
                }
            }

        search_query = {"bool": {"filter": [{"term": {"type": "package"}}], "must": [q]}}
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={"query": search_query, "size": limit * 5, "track_total_hits": True},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 404:
                return error("Flake indices not found. Flake search may be temporarily unavailable.")
            raise

        if not hits:
            return f"No flakes found matching '{query}'"

        flakes: dict[str, dict[str, Any]] = {}
        for hit in hits:
            src = hit.get("_source", {})
            flake_name = src.get("flake_name", "").strip()
            package_pname = src.get("package_pname", "")
            resolved = src.get("flake_resolved", {})

            if not flake_name and not package_pname:
                continue

            if isinstance(resolved, dict) and (resolved.get("owner") or resolved.get("repo") or resolved.get("url")):
                owner = resolved.get("owner", "")
                repo = resolved.get("repo", "")
                url = resolved.get("url", "")
                if owner and repo:
                    flake_key = f"{owner}/{repo}"
                    display_name = flake_name or repo or package_pname
                elif url:
                    flake_key = url
                    display_name = flake_name or url.rstrip("/").split("/")[-1].replace(".git", "") or package_pname
                else:
                    flake_key = flake_name or package_pname
                    display_name = flake_key

                if flake_key not in flakes:
                    flakes[flake_key] = {
                        "name": display_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": owner,
                        "repo": repo,
                        "url": url,
                        "type": resolved.get("type", ""),
                        "packages": set(),
                    }
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_key]["packages"].add(attr_name)
            elif flake_name:
                if flake_name not in flakes:
                    flakes[flake_name] = {
                        "name": flake_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": "",
                        "repo": "",
                        "type": "",
                        "packages": set(),
                    }
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_name]["packages"].add(attr_name)

        results = []
        if total > len(flakes):
            results.append(f"Found {total:,} matches ({len(flakes)} unique flakes) for '{query}':\n")
        else:
            results.append(f"Found {len(flakes)} flakes matching '{query}':\n")

        for flake in flakes.values():
            results.append(f"* {flake['name']}")
            if flake.get("owner") and flake.get("repo"):
                results.append(f"  Repository: {flake['owner']}/{flake['repo']}")
            elif flake.get("url"):
                results.append(f"  URL: {flake['url']}")
            if flake.get("description"):
                desc = flake["description"][:200] + "..." if len(flake["description"]) > 200 else flake["description"]
                results.append(f"  {desc}")
            if flake["packages"]:
                packages = sorted(flake["packages"])[:5]
                if len(flake["packages"]) > 5:
                    results.append(f"  Packages: {', '.join(packages)}, ... ({len(flake['packages'])} total)")
                else:
                    results.append(f"  Packages: {', '.join(packages)}")
            results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _info_nixos(name: str, info_type: str, channel: str) -> str:
    """Get detailed info for a NixOS package or option."""
    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
        field = "package_pname" if info_type == "package" else "option_name"
        query = {"bool": {"must": [{"term": {"type": info_type}}, {"term": {field: name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            return error(f"{info_type.capitalize()} '{name}' not found", "NOT_FOUND")

        src = hits[0].get("_source", {})
        if info_type == "package":
            info = [f"Package: {src.get('package_pname', '')}", f"Version: {src.get('package_pversion', '')}"]
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
            info = [f"Option: {src.get('option_name', '')}"]
            opt_type = src.get("option_type", "")
            if opt_type:
                info.append(f"Type: {opt_type}")
            desc = src.get("option_description", "")
            if desc:
                if "<rendered-html>" in desc:
                    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                    desc = re.sub(r"<[^>]+>", "", desc).strip()
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


def _info_home_manager(name: str) -> str:
    """Get detailed info for a Home Manager option."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, name, "", 100)
        for opt in options:
            if opt["name"] == name:
                info = [f"Option: {name}"]
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        if options:
            suggestions = [opt["name"] for opt in options[:5] if name in opt["name"]]
            if suggestions:
                return error(f"Option '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")
        return error(f"Option '{name}' not found", "NOT_FOUND")
    except Exception as e:
        return error(str(e))


def _info_darwin(name: str) -> str:
    """Get detailed info for a nix-darwin option."""
    try:
        options = parse_html_options(DARWIN_URL, name, "", 100)
        for opt in options:
            if opt["name"] == name:
                info = [f"Option: {name}"]
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        if options:
            suggestions = [opt["name"] for opt in options[:5] if name in opt["name"]]
            if suggestions:
                return error(f"Option '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")
        return error(f"Option '{name}' not found", "NOT_FOUND")
    except Exception as e:
        return error(str(e))


def _stats_nixos(channel: str) -> str:
    """Get NixOS package and option counts for a channel."""
    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
        index = channels[channel]
        url = f"{NIXOS_API}/{index}/_count"
        try:
            pkg_resp = requests.post(url, json={"query": {"term": {"type": "package"}}}, auth=NIXOS_AUTH, timeout=10)
            pkg_count = pkg_resp.json().get("count", 0)
        except Exception:
            pkg_count = 0
        try:
            opt_resp = requests.post(url, json={"query": {"term": {"type": "option"}}}, auth=NIXOS_AUTH, timeout=10)
            opt_count = opt_resp.json().get("count", 0)
        except Exception:
            opt_count = 0

        if pkg_count == 0 and opt_count == 0:
            return error("Failed to retrieve statistics")
        return f"NixOS Statistics ({channel}):\n* Packages: {pkg_count:,}\n* Options: {opt_count:,}"
    except Exception as e:
        return error(str(e))


def _stats_home_manager() -> str:
    """Get Home Manager option counts and top categories."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, limit=5000)
        if not options:
            return error("Failed to fetch Home Manager statistics")

        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = ["Home Manager Statistics:", f"* Total options: {len(options):,}", f"* Categories: {len(categories)}"]
        result.append("* Top categories:")
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except Exception as e:
        return error(str(e))


def _stats_darwin() -> str:
    """Get nix-darwin option counts and top categories."""
    try:
        options = parse_html_options(DARWIN_URL, limit=3000)
        if not options:
            return error("Failed to fetch nix-darwin statistics")

        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = ["nix-darwin Statistics:", f"* Total options: {len(options):,}", f"* Categories: {len(categories)}"]
        result.append("* Top categories:")
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except Exception as e:
        return error(str(e))


def _stats_flakes() -> str:
    """Get flake ecosystem statistics."""
    try:
        flake_index = FLAKE_INDEX
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_count",
                json={"query": {"term": {"type": "package"}}},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            total_packages = resp.json().get("count", 0)
        except Exception:
            return error("Flake indices not found")

        return f"NixOS Flakes Statistics:\n* Available packages: {total_packages:,}"
    except Exception as e:
        return error(str(e))


def _search_nixvim(query: str, limit: int) -> str:
    """Search Nixvim options from NuschtOS meta JSON."""
    try:
        options = nixvim_cache.get_options()
        query_lower = query.lower()

        matches = []
        for opt in options:
            name = opt.get("name", "")
            desc = strip_html(opt.get("description", ""))
            if query_lower in name.lower() or query_lower in desc.lower():
                matches.append(
                    {
                        "name": name,
                        "type": opt.get("type", ""),
                        "description": desc,
                    }
                )
                if len(matches) >= limit:
                    break

        if not matches:
            return f"No Nixvim options found matching '{query}'"

        results = [f"Found {len(matches)} Nixvim options matching '{query}':\n"]
        for opt in matches:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                desc = opt["description"][:200] + "..." if len(opt["description"]) > 200 else opt["description"]
                results.append(f"  {desc}")
            results.append("")
        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _info_nixvim(name: str) -> str:
    """Get detailed info for a Nixvim option."""
    try:
        options = nixvim_cache.get_options()

        # Exact match first
        for opt in options:
            if opt.get("name") == name:
                return _format_nixvim_option(opt)

        # Try case-insensitive match
        name_lower = name.lower()
        for opt in options:
            if opt.get("name", "").lower() == name_lower:
                return _format_nixvim_option(opt)

        # Suggest similar options
        similar = [o["name"] for o in options if name_lower in o.get("name", "").lower()][:5]
        if similar:
            return error(f"Option '{name}' not found. Similar: {', '.join(similar)}", "NOT_FOUND")
        return error(f"Nixvim option '{name}' not found", "NOT_FOUND")
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _format_nixvim_option(opt: dict[str, Any]) -> str:
    """Format a Nixvim option for detailed display."""
    lines = [f"Nixvim Option: {opt.get('name', '')}"]

    if opt.get("type"):
        lines.append(f"Type: {opt['type']}")

    desc = strip_html(opt.get("description", ""))
    if desc:
        lines.append(f"Description: {desc}")

    default = strip_html(opt.get("default", ""))
    if default:
        lines.append(f"Default: {default}")

    example = strip_html(opt.get("example", ""))
    if example:
        # Truncate long examples
        if len(example) > 500:
            example = example[:500] + "..."
        lines.append(f"Example: {example}")

    declarations = opt.get("declarations", [])
    if declarations:
        lines.append(f"Declared in: {declarations[0]}")

    return "\n".join(lines)


def _stats_nixvim() -> str:
    """Get Nixvim option statistics."""
    try:
        options = nixvim_cache.get_options()

        # Count top-level categories
        categories: dict[str, int] = {}
        for opt in options:
            name = opt.get("name", "")
            if "." in name:
                cat = name.split(".")[0]
            else:
                cat = name
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = [
            "Nixvim Statistics:",
            f"* Total options: {len(options):,}",
            f"* Categories: {len(categories)}",
            "* Top categories:",
        ]
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _browse_nixvim_options(prefix: str) -> str:
    """Browse Nixvim options by prefix, or list categories if no prefix."""
    try:
        options = nixvim_cache.get_options()

        if not prefix:
            # List top-level categories with counts
            categories: dict[str, int] = {}
            for opt in options:
                name = opt.get("name", "")
                if "." in name:
                    cat = name.split(".")[0]
                else:
                    cat = name
                categories[cat] = categories.get(cat, 0) + 1

            sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            results = [f"Nixvim option categories ({len(categories)} total):\n"]
            for cat, count in sorted_cats:
                results.append(f"* {cat} ({count} options)")
            return "\n".join(results)

        # List options under prefix
        prefix_dot = prefix if prefix.endswith(".") else prefix + "."
        matches = []
        for opt in options:
            name = opt.get("name", "")
            if name.startswith(prefix_dot) or name == prefix:
                matches.append(
                    {
                        "name": name,
                        "type": opt.get("type", ""),
                        "description": strip_html(opt.get("description", "")),
                    }
                )

        if not matches:
            return f"No Nixvim options found with prefix '{prefix}'"

        results = [f"Nixvim options with prefix '{prefix}' ({len(matches)} found):\n"]
        for opt in sorted(matches, key=lambda x: x["name"])[:100]:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                desc = opt["description"][:150] + "..." if len(opt["description"]) > 150 else opt["description"]
                results.append(f"  {desc}")
            results.append("")

        if len(matches) > 100:
            results.append(f"... and {len(matches) - 100} more options")
        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _list_channels() -> str:
    """List available NixOS channels with status and document counts."""
    try:
        configured = get_channels()
        available = channel_cache.get_available()
        results = []

        if channel_cache.using_fallback:
            results.append("WARNING: Using fallback channels (API discovery failed)\n")

        results.append("NixOS Channels:\n")
        for name, index in sorted(configured.items()):
            status = "Available" if index in available else "Unavailable"
            doc_count = available.get(index, "Unknown")
            label = f"* {name}"
            if name == "stable":
                parts = index.split("-")
                if len(parts) >= 4:
                    label = f"* {name} (current: {parts[3]})"
            results.append(f"{label} -> {index}")
            results.append(f"  Status: {status} ({doc_count})")
            results.append("")

        results.append("Note: 'stable' always points to current stable release.")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _browse_options(source: str, prefix: str) -> str:
    """Browse Home Manager or nix-darwin options by prefix, or list categories."""
    url = HOME_MANAGER_URL if source == "home-manager" else DARWIN_URL
    source_name = "Home Manager" if source == "home-manager" else "nix-darwin"

    try:
        if prefix:
            options = parse_html_options(url, "", prefix)
            if not options:
                return f"No {source_name} options found with prefix '{prefix}'"
            results = [f"{source_name} options with prefix '{prefix}' ({len(options)} found):\n"]
            for opt in sorted(options, key=lambda x: x["name"]):
                results.append(f"* {opt['name']}")
                if opt["description"]:
                    results.append(f"  {opt['description']}")
                results.append("")
            return "\n".join(results).strip()
        else:
            options = parse_html_options(url, limit=5000)
            categories: dict[str, int] = {}
            for opt in options:
                name = opt["name"]
                if name and "." in name:
                    cat = name.split(".")[0]
                    if len(cat) > 1 and cat.isidentifier() and cat.islower():
                        categories[cat] = categories.get(cat, 0) + 1

            results = [f"{source_name} categories ({len(categories)} total):\n"]
            sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            for cat, count in sorted_cats:
                results.append(f"* {cat} ({count} options)")
            return "\n".join(results)
    except Exception as e:
        return error(str(e))


# =============================================================================
# NixHub version helpers
# =============================================================================


def _version_key(version_str: str) -> tuple[int, int, int]:
    try:
        parts = version_str.split(".")
        numeric_parts = []
        for part in parts[:3]:
            numeric = ""
            for char in part:
                if char.isdigit():
                    numeric += char
                else:
                    break
            numeric_parts.append(int(numeric) if numeric else 0)
        while len(numeric_parts) < 3:
            numeric_parts.append(0)
        return (numeric_parts[0], numeric_parts[1], numeric_parts[2])
    except Exception:
        return (0, 0, 0)


def _format_release(release: dict[str, Any], package_name: str | None = None) -> list[str]:
    results = []
    version = release.get("version", "unknown")
    platforms = release.get("platforms", [])

    results.append(f"* Version {version}")
    last_updated = release.get("last_updated", "")
    if last_updated:
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            results.append(f"  Updated: {dt.strftime('%Y-%m-%d')}")
        except Exception:
            pass

    if platforms:
        seen = set()
        for p in platforms:
            commit = p.get("commit_hash", "")
            if commit and commit not in seen and re.match(r"^[a-fA-F0-9]{40}$", commit):
                seen.add(commit)
                results.append(f"  Commit: {commit}")
    return results


# =============================================================================
# MCP Tools (only 2 exposed)
# =============================================================================


@mcp.tool()
async def nix(
    action: Annotated[str, "search|info|stats|options|channels"],
    query: Annotated[str, "Search term, name, or prefix"] = "",
    source: Annotated[str, "nixos|home-manager|darwin|flakes|nixvim"] = "nixos",
    type: Annotated[str, "packages|options|programs"] = "packages",
    channel: Annotated[str, "unstable|stable|25.05"] = "unstable",
    limit: Annotated[int, "1-100"] = 20,
) -> str:
    """Query NixOS, Home Manager, Darwin, flakes, or Nixvim."""
    if not 1 <= limit <= 100:
        return error("Limit must be 1-100")

    if action == "search":
        if not query:
            return error("Query required for search")
        if source == "nixos":
            if type not in ["packages", "options", "programs", "flakes"]:
                return error("Type must be packages|options|programs|flakes")
            return _search_nixos(query, type, limit, channel)
        elif source == "home-manager":
            return _search_home_manager(query, limit)
        elif source == "darwin":
            return _search_darwin(query, limit)
        elif source == "flakes":
            return _search_flakes(query, limit)
        elif source == "nixvim":
            return _search_nixvim(query, limit)
        else:
            return error("Source must be nixos|home-manager|darwin|flakes|nixvim")

    elif action == "info":
        if not query:
            return error("Name required for info")
        if source == "nixos":
            if type not in ["package", "packages", "option", "options"]:
                return error("Type must be package|option")
            info_type = "package" if type in ["package", "packages"] else "option"
            return _info_nixos(query, info_type, channel)
        elif source == "home-manager":
            return _info_home_manager(query)
        elif source == "darwin":
            return _info_darwin(query)
        elif source == "nixvim":
            return _info_nixvim(query)
        else:
            return error("Source must be nixos|home-manager|darwin|nixvim")

    elif action == "stats":
        if source == "nixos":
            return _stats_nixos(channel)
        elif source == "home-manager":
            return _stats_home_manager()
        elif source == "darwin":
            return _stats_darwin()
        elif source == "flakes":
            return _stats_flakes()
        elif source == "nixvim":
            return _stats_nixvim()
        else:
            return error("Source must be nixos|home-manager|darwin|flakes|nixvim")

    elif action == "options":
        if source not in ["home-manager", "darwin", "nixvim"]:
            return error("Options browsing only for home-manager|darwin|nixvim")
        if source == "nixvim":
            return _browse_nixvim_options(query)
        return _browse_options(source, query)

    elif action == "channels":
        return _list_channels()

    else:
        return error("Action must be search|info|stats|options|channels")


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

    try:
        url = f"https://search.devbox.sh/v2/pkg?name={package}"
        headers = {"Accept": "application/json", "User-Agent": "mcp-nixos/1.1.0"}
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 404:
            return error(f"Package '{package}' not found", "NOT_FOUND")
        if resp.status_code >= 500:
            return error("NixHub API temporarily unavailable", "SERVICE_ERROR")
        resp.raise_for_status()

        data = resp.json()
        if not isinstance(data, dict):
            return error("Invalid response from NixHub")

        releases = data.get("releases", [])
        if not releases:
            return f"Package: {package}\nNo version history available"

        # If specific version requested, find it
        if version:
            for release in releases:
                if release.get("version") == version:
                    results = [f"Found {package} version {version}\n"]
                    platforms = release.get("platforms", [])
                    if platforms:
                        seen = set()
                        for p in platforms:
                            commit = p.get("commit_hash", "")
                            if commit and commit not in seen and re.match(r"^[a-fA-F0-9]{40}$", commit):
                                seen.add(commit)
                                results.append(f"Nixpkgs commit: {commit}")
                                attr = p.get("attribute_path", "")
                                if attr:
                                    results.append(f"  Attribute: {attr}")
                    return "\n".join(results)

            # Version not found
            versions_list = [r.get("version", "") for r in releases[:limit]]
            return f"Version {version} not found for {package}\nAvailable: {', '.join(versions_list)}"

        # Return version history
        results = [f"Package: {package}", f"Total versions: {len(releases)}\n"]
        shown = releases[:limit]
        results.append(f"Recent versions ({len(shown)} of {len(releases)}):\n")
        for release in shown:
            results.extend(_format_release(release, package))
            results.append("")
        return "\n".join(results).strip()

    except requests.Timeout:
        return error("Request timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Network error: {e}", "NETWORK_ERROR")
    except Exception as e:
        return error(str(e))


def main() -> None:
    """Run the MCP server."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
