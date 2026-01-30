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
import shutil
import stat
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from fastmcp import FastMCP

from . import __version__


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


class NixDevCache:
    """Cache for nix.dev Sphinx search index."""

    def __init__(self) -> None:
        self.index: dict[str, Any] | None = None

    def get_index(self) -> dict[str, Any]:
        """Fetch and cache nix.dev search index."""
        if self.index is not None:
            return self.index

        try:
            resp = requests.get(NIXDEV_SEARCH_INDEX, timeout=30)
            resp.raise_for_status()

            # Parse JavaScript: Search.setIndex({...})
            content = resp.text.strip()
            if content.startswith("Search.setIndex("):
                match = re.search(r"Search\.setIndex\((.*)\)\s*$", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    self.index = json.loads(json_str)
                else:
                    raise ValueError("Unexpected search index format")
            else:
                raise ValueError("Unexpected search index format")

            return self.index
        except requests.Timeout as exc:
            raise APIError("Timeout fetching nix.dev search index") from exc
        except requests.RequestException as exc:
            raise APIError(f"Failed to fetch nix.dev index: {exc}") from exc
        except Exception as exc:
            raise APIError(f"Failed to parse nix.dev index: {exc}") from exc


nixdev_cache = NixDevCache()


class NoogleCache:
    """Cache for Noogle function data fetched from noogle.dev API."""

    def __init__(self) -> None:
        self._data: list[dict[str, Any]] | None = None
        self._builtin_types: dict[str, dict[str, str]] | None = None

    def get_data(self) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
        """Fetch and cache all Noogle function data."""
        if self._data is not None:
            return self._data, self._builtin_types or {}

        try:
            resp = requests.get(NOOGLE_API, timeout=60)
            resp.raise_for_status()
            payload = resp.json()

            data: list[dict[str, Any]] = payload.get("data", [])
            builtin_types: dict[str, dict[str, str]] = payload.get("builtinTypes", {})

            self._data = data
            self._builtin_types = builtin_types

            return data, builtin_types
        except requests.Timeout as exc:
            raise APIError("Timeout fetching Noogle data") from exc
        except requests.RequestException as exc:
            raise APIError(f"Failed to fetch Noogle data: {exc}") from exc
        except Exception as exc:
            raise APIError(f"Failed to parse Noogle data: {exc}") from exc


noogle_cache = NoogleCache()


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


# =============================================================================
# FlakeHub functions (Determinate Systems registry)
# =============================================================================


def _search_flakehub(query: str, limit: int) -> str:
    """Search FlakeHub flakes by name or description."""
    try:
        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}
        resp = requests.get(f"{FLAKEHUB_API}/search", params={"q": query}, headers=headers, timeout=15)
        resp.raise_for_status()
        flakes = resp.json()

        if not flakes:
            return f"No flakes found on FlakeHub matching '{query}'"

        # Limit results
        flakes = flakes[:limit]

        results = [f"Found {len(flakes)} flakes on FlakeHub matching '{query}':\n"]
        for flake in flakes:
            org = flake.get("org", "")
            project = flake.get("project", "")
            desc = flake.get("description", "")
            labels = flake.get("labels", [])

            results.append(f"* {org}/{project}")
            if desc:
                desc = " ".join(desc.split())  # Normalize whitespace
                desc = desc[:200] + "..." if len(desc) > 200 else desc
                results.append(f"  {desc}")
            if labels:
                results.append(f"  Labels: {', '.join(labels[:5])}")
            results.append(f"  https://flakehub.com/flake/{org}/{project}")
            results.append("")

        return "\n".join(results).strip()
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_flakehub(name: str) -> str:
    """Get detailed info for a FlakeHub flake (org/project format)."""
    try:
        # Parse org/project format
        if "/" not in name:
            return error("FlakeHub flake name must be in 'org/project' format (e.g., 'NixOS/nixpkgs')")

        parts = name.split("/", 1)
        org, project = parts[0], parts[1]

        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}

        # Get latest version info
        resp = requests.get(f"{FLAKEHUB_API}/version/{org}/{project}/*", headers=headers, timeout=15)
        if resp.status_code == 404:
            return error(f"Flake '{name}' not found on FlakeHub", "NOT_FOUND")
        resp.raise_for_status()
        version_info = resp.json()

        results = [f"FlakeHub Flake: {org}/{project}"]

        desc = version_info.get("description", "")
        if desc:
            results.append(f"Description: {desc}")

        version = version_info.get("simplified_version") or version_info.get("version", "")
        if version:
            results.append(f"Latest Version: {version}")

        revision = version_info.get("revision", "")
        if revision:
            results.append(f"Revision: {revision}")

        commit_count = version_info.get("commit_count")
        if commit_count:
            results.append(f"Commits: {commit_count:,}")

        visibility = version_info.get("visibility", "")
        if visibility:
            results.append(f"Visibility: {visibility}")

        published = version_info.get("published_at", "")
        if published:
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                results.append(f"Published: {dt.strftime('%Y-%m-%d %H:%M UTC')}")
            except Exception:
                pass

        mirrored = version_info.get("mirrored")
        if mirrored:
            results.append("Source: Mirrored from GitHub")

        download_url = version_info.get("pretty_download_url") or version_info.get("download_url", "")
        if download_url:
            results.append(f"Download: {download_url}")

        results.append(f"FlakeHub URL: https://flakehub.com/flake/{org}/{project}")

        return "\n".join(results)
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
            return error(f"Flake '{name}' not found on FlakeHub", "NOT_FOUND")
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _stats_flakehub() -> str:
    """Get FlakeHub statistics."""
    try:
        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}

        # Get all flakes to count them
        resp = requests.get(f"{FLAKEHUB_API}/flakes", headers=headers, timeout=15)
        resp.raise_for_status()
        flakes = resp.json()

        total_flakes = len(flakes)

        # Count flakes by organization
        orgs: dict[str, int] = {}
        labels: dict[str, int] = {}
        for flake in flakes:
            org = flake.get("org", "unknown")
            orgs[org] = orgs.get(org, 0) + 1
            for label in flake.get("labels", []):
                labels[label] = labels.get(label, 0) + 1

        top_orgs = sorted(orgs.items(), key=lambda x: x[1], reverse=True)[:5]
        top_labels = sorted(labels.items(), key=lambda x: x[1], reverse=True)[:5]

        results = [
            "FlakeHub Statistics:",
            f"* Total flakes: {total_flakes:,}",
            f"* Organizations: {len(orgs):,}",
            "* Top organizations:",
        ]
        for org, count in top_orgs:
            results.append(f"  - {org}: {count:,} flakes")

        if top_labels:
            results.append("* Top labels:")
            for label, count in top_labels:
                results.append(f"  - {label}: {count:,} flakes")

        results.append("\nFlakeHub URL: https://flakehub.com/")
        return "\n".join(results)
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


# =============================================================================
# NixOS Wiki functions (wiki.nixos.org)
# =============================================================================


def _search_wiki(query: str, limit: int) -> str:
    """Search NixOS Wiki via MediaWiki API."""
    try:
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": "1",
            "srlimit": limit,
        }
        resp = requests.get(WIKI_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results_list = data.get("query", {}).get("search", [])
        if not results_list:
            return f"No wiki articles found matching '{query}'"

        results = [f"Found {len(results_list)} wiki articles matching '{query}':\n"]
        for item in results_list:
            title = item.get("title", "")
            snippet = strip_html(item.get("snippet", ""))
            wordcount = item.get("wordcount", 0)

            results.append(f"* {title}")
            results.append(f"  https://wiki.nixos.org/wiki/{quote(title.replace(' ', '_'), safe='')}")
            if snippet:
                # Truncate long snippets
                snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                results.append(f"  {snippet}")
            if wordcount:
                results.append(f"  ({wordcount:,} words)")
            results.append("")

        return "\n".join(results).strip()
    except requests.Timeout:
        return error("Wiki API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Wiki API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_wiki(title: str) -> str:
    """Get wiki page content/extract via MediaWiki API."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "exintro": "1",  # Just the intro
            "explaintext": "1",  # Plain text, no HTML
            "format": "json",
        }
        resp = requests.get(WIKI_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return error(f"Wiki page '{title}' not found", "NOT_FOUND")

        # Get first page (there's only one)
        page = next(iter(pages.values()))
        if page.get("missing"):
            return error(f"Wiki page '{title}' not found", "NOT_FOUND")

        page_title = page.get("title", title)
        extract = page.get("extract", "")

        results = [
            f"Wiki: {page_title}",
            f"URL: https://wiki.nixos.org/wiki/{quote(page_title.replace(' ', '_'), safe='')}",
            "",
        ]

        if extract:
            # Limit extract length
            if len(extract) > 1500:
                extract = extract[:1500] + "..."
            results.append(extract)

        return "\n".join(results)
    except requests.Timeout:
        return error("Wiki API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Wiki API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


# =============================================================================
# nix.dev functions (documentation site)
# =============================================================================


def _search_nixdev(query: str, limit: int) -> str:
    """Search nix.dev documentation via cached Sphinx index."""
    try:
        index = nixdev_cache.get_index()

        docnames = index.get("docnames", [])
        titles = index.get("titles", [])
        terms = index.get("terms", {})

        query_lower = query.lower()
        query_terms = query_lower.split()

        # Score documents by term matches
        scores: dict[int, int] = {}
        for term in query_terms:
            # Exact term match
            if term in terms:
                doc_ids = terms[term]
                if isinstance(doc_ids, list):
                    for doc_id in doc_ids:
                        scores[doc_id] = scores.get(doc_id, 0) + 2

            # Partial term matches
            for index_term, doc_ids in terms.items():
                if term in index_term and term != index_term:
                    if isinstance(doc_ids, list):
                        for doc_id in doc_ids:
                            scores[doc_id] = scores.get(doc_id, 0) + 1

        # Also search titles
        for i, doc_title in enumerate(titles):
            if query_lower in doc_title.lower():
                scores[i] = scores.get(i, 0) + 5  # Title match bonus

        if not scores:
            return f"No nix.dev documentation found matching '{query}'"

        # Sort by score, limit results
        sorted_docs = sorted(scores.items(), key=lambda x: -x[1])[:limit]

        results = [f"Found {len(sorted_docs)} nix.dev docs matching '{query}':\n"]
        for doc_id, _score in sorted_docs:
            if doc_id < len(titles) and doc_id < len(docnames):
                doc_title = titles[doc_id]
                docname = docnames[doc_id]
                url = f"{NIXDEV_BASE_URL}/{docname}"

                results.append(f"* {doc_title}")
                results.append(f"  {url}")
                results.append("")

        return "\n".join(results).strip()
    except APIError as exc:
        return error(str(exc), "API_ERROR")
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


# =============================================================================
# Noogle functions (noogle.dev - Nix function API search)
# =============================================================================


def _get_noogle_function_path(doc: dict[str, Any]) -> str:
    """Extract the function path from a Noogle document."""
    meta = doc.get("meta", {})
    # Use path if available, otherwise construct from title
    path = meta.get("path", [])
    if path:
        return ".".join(str(p) for p in path)
    title = meta.get("title", "")
    return str(title) if title else ""


def _get_noogle_type_signature(doc: dict[str, Any]) -> str:
    """Extract the type signature from a Noogle document."""
    content = doc.get("content")
    if not content or not isinstance(content, dict):
        return ""

    # Check for signature in content
    signature = content.get("signature", "")
    if signature:
        return str(signature)

    # Check for type annotation
    type_info = content.get("type", "")
    if type_info:
        return str(type_info)

    return ""


def _get_noogle_aliases(doc: dict[str, Any]) -> list[str]:
    """Extract aliases from a Noogle document."""
    meta = doc.get("meta")
    if not meta or not isinstance(meta, dict):
        return []
    aliases = meta.get("aliases")
    if aliases and isinstance(aliases, list):
        return [".".join(str(p) for p in a) if isinstance(a, list) else str(a) for a in aliases]
    return []


def _get_noogle_description(doc: dict[str, Any]) -> str:
    """Extract description from a Noogle document."""
    content = doc.get("content")
    if not content or not isinstance(content, dict):
        return ""

    # Try different content fields
    desc = content.get("content", "")
    if desc:
        return strip_html(str(desc))

    # Try lambda content
    lambda_content = content.get("lambda")
    if lambda_content and isinstance(lambda_content, dict):
        lambda_desc = lambda_content.get("content", "")
        if lambda_desc:
            return strip_html(str(lambda_desc))

    return ""


def _search_noogle(query: str, limit: int) -> str:
    """Search Noogle functions by name, path, or documentation content."""
    try:
        data, _ = noogle_cache.get_data()
        query_lower = query.lower()

        matches = []
        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            desc = _get_noogle_description(doc)
            desc_lower = desc.lower()
            aliases = _get_noogle_aliases(doc)

            # Score matches
            score = 0
            # Exact path match
            if path_lower == query_lower:
                score = 100
            # Path contains query
            elif query_lower in path_lower:
                # Boost if query matches end of path (function name)
                if path_lower.endswith(query_lower) or path_lower.endswith("." + query_lower):
                    score = 50
                else:
                    score = 30
            # Alias match
            elif any(query_lower in alias.lower() for alias in aliases):
                score = 40
            # Description match
            elif query_lower in desc_lower:
                score = 10

            if score > 0:
                matches.append((score, path, doc))

        if not matches:
            return f"No Noogle functions found matching '{query}'"

        # Sort by score (descending), then by path
        matches.sort(key=lambda x: (-x[0], x[1]))
        matches = matches[:limit]

        results = [f"Found {len(matches)} Noogle functions matching '{query}':\n"]
        for _, path, doc in matches:
            results.append(f"* {path}")
            sig = _get_noogle_type_signature(doc)
            if sig:
                # Truncate long signatures
                sig = sig[:100] + "..." if len(sig) > 100 else sig
                results.append(f"  Type: {sig}")
            desc = _get_noogle_description(doc)
            if desc:
                desc = desc[:200] + "..." if len(desc) > 200 else desc
                results.append(f"  {desc}")
            aliases = _get_noogle_aliases(doc)
            if aliases:
                results.append(f"  Aliases: {', '.join(aliases[:3])}")
            results.append("")

        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_noogle(name: str) -> str:
    """Get detailed info for a specific Noogle function."""
    try:
        data, _ = noogle_cache.get_data()
        name_lower = name.lower()

        # Find exact match first, then partial match
        exact_match = None
        partial_matches = []

        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            aliases = _get_noogle_aliases(doc)
            aliases_lower = [a.lower() for a in aliases]

            if path_lower == name_lower or name_lower in aliases_lower:
                exact_match = doc
                break
            elif name_lower in path_lower:
                partial_matches.append((path, doc))

        if not exact_match and not partial_matches:
            return error(f"Noogle function '{name}' not found", "NOT_FOUND")

        if not exact_match:
            # Suggest partial matches
            suggestions = [p for p, _ in partial_matches[:5]]
            return error(f"Function '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")

        doc = exact_match
        path = _get_noogle_function_path(doc)
        meta = doc.get("meta", {})
        content = doc.get("content", {})

        results = [f"Noogle Function: {path}"]

        # Type signature
        sig = _get_noogle_type_signature(doc)
        if sig:
            results.append(f"Type: {sig}")

        # Path
        results.append(f"Path: {path}")

        # Aliases
        aliases = _get_noogle_aliases(doc)
        if aliases:
            results.append(f"Aliases: {', '.join(aliases)}")

        # Primop info (for builtins)
        primop_meta = meta.get("primop_meta", {})
        if primop_meta:
            arity = primop_meta.get("arity")
            args = primop_meta.get("args", [])
            if arity is not None:
                if args:
                    results.append(f"Primop: Yes (arity: {arity}, args: {', '.join(args)})")
                else:
                    results.append(f"Primop: Yes (arity: {arity})")

        results.append("")

        # Description
        desc = _get_noogle_description(doc)
        if desc:
            results.append("Description:")
            results.append(desc)
            results.append("")

        # Example
        example = content.get("example", "")
        if example:
            example = strip_html(example)
            results.append("Example:")
            # Truncate long examples
            if len(example) > 500:
                example = example[:500] + "..."
            results.append(example)
            results.append("")

        # Source position
        position = meta.get("position", {})
        if position:
            file_path = position.get("file", "")
            line = position.get("line")
            if file_path:
                if line:
                    results.append(f"Source: {file_path}:{line}")
                else:
                    results.append(f"Source: {file_path}")

        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _stats_noogle() -> str:
    """Get Noogle statistics."""
    try:
        data, _ = noogle_cache.get_data()

        # Count functions by category
        categories: dict[str, int] = {}
        with_signatures = 0
        with_docs = 0

        for doc in data:
            path = _get_noogle_function_path(doc)
            if "." in path:
                cat = ".".join(path.split(".")[:2])  # e.g., "lib.strings"
            else:
                cat = path

            categories[cat] = categories.get(cat, 0) + 1

            if _get_noogle_type_signature(doc):
                with_signatures += 1
            if _get_noogle_description(doc):
                with_docs += 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]

        results = [
            "Noogle Statistics:",
            f"* Total functions: {len(data):,}",
            f"* With type signatures: {with_signatures:,}",
            f"* With documentation: {with_docs:,}",
            f"* Categories: {len(categories)}",
            "* Top categories:",
        ]

        for cat, count in top_cats:
            results.append(f"  - {cat}: {count}")

        results.append("")
        results.append("Data source: noogle.dev (updated daily)")

        return "\n".join(results)
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _browse_noogle_options(prefix: str) -> str:
    """Browse Noogle functions by prefix, or list categories if no prefix."""
    try:
        data, _ = noogle_cache.get_data()

        if not prefix:
            # List top-level categories with counts
            categories: dict[str, int] = {}
            for doc in data:
                path = _get_noogle_function_path(doc)
                if "." in path:
                    cat = ".".join(path.split(".")[:2])  # e.g., "lib.strings"
                else:
                    cat = path
                categories[cat] = categories.get(cat, 0) + 1

            sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            results = [f"Noogle function categories ({len(categories)} total):\n"]
            for cat, count in sorted_cats:
                results.append(f"* {cat} ({count} functions)")
            return "\n".join(results)

        # List functions under prefix
        prefix_lower = prefix.lower()
        prefix_dot = prefix_lower if prefix_lower.endswith(".") else prefix_lower + "."
        matches = []

        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            if path_lower.startswith(prefix_dot) or path_lower == prefix_lower:
                matches.append(
                    {
                        "path": path,
                        "type": _get_noogle_type_signature(doc),
                        "description": _get_noogle_description(doc),
                    }
                )

        if not matches:
            return f"No Noogle functions found with prefix '{prefix}'"

        results = [f"Noogle functions with prefix '{prefix}' ({len(matches)} found):\n"]
        for func in sorted(matches, key=lambda x: x["path"])[:100]:
            results.append(f"* {func['path']}")
            if func["type"]:
                sig = func["type"][:80] + "..." if len(func["type"]) > 80 else func["type"]
                results.append(f"  Type: {sig}")
            if func["description"]:
                desc = func["description"][:150] + "..." if len(func["description"]) > 150 else func["description"]
                results.append(f"  {desc}")
            results.append("")

        if len(matches) > 100:
            results.append(f"... and {len(matches) - 100} more functions")
        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
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
# Flake inputs helpers (local nix store access)
# =============================================================================

# Maximum file size for reading (1MB)
MAX_FILE_SIZE = 1024 * 1024
# Default and maximum line limits
DEFAULT_LINE_LIMIT = 500
MAX_LINE_LIMIT = 2000
# Known sources (to distinguish from flake paths)
KNOWN_SOURCES = {"nixos", "home-manager", "darwin", "flakes", "flakehub", "nixvim", "wiki", "nix-dev", "noogle"}


def _check_nix_available() -> bool:
    """Check if nix command is available on the system."""
    return shutil.which("nix") is not None


async def _run_nix_command(args: list[str], cwd: str | None = None, timeout: int = 60) -> tuple[bool, str, str]:
    """Run a nix command asynchronously with timeout.

    Returns (success, stdout, stderr).
    """
    process: asyncio.subprocess.Process | None = None
    try:
        # nix flake commands require experimental features
        full_args = ["nix", "--extra-experimental-features", "nix-command flakes"] + args
        process = await asyncio.create_subprocess_exec(
            *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        return process.returncode == 0, stdout_str, stderr_str
    except TimeoutError:
        # Kill the process and wait for it to terminate
        if process is not None:
            process.kill()
            await process.wait()
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", "nix command not found"
    except Exception as e:
        return False, "", str(e)


async def _get_flake_inputs(flake_dir: str) -> tuple[bool, dict[str, Any] | None, str]:
    """Get flake inputs by running nix flake archive --json.

    Returns (success, inputs_dict, error_message).
    """
    # Verify flake.nix exists
    flake_path = os.path.join(flake_dir, "flake.nix")
    if not os.path.isfile(flake_path):
        return False, None, f"Not a flake directory: {flake_dir} (no flake.nix found)"

    success, stdout, stderr = await _run_nix_command(["flake", "archive", "--json"], cwd=flake_dir)
    if not success:
        # Check for common error patterns
        if "experimental feature" in stderr.lower():
            msg = "Flakes not enabled. Enable with: nix-command flakes experimental features"
            return False, None, msg
        if "does not provide attribute" in stderr:
            return False, None, f"Invalid flake: {stderr.strip()}"
        return False, None, f"Failed to get flake inputs: {stderr.strip()}"

    try:
        data = json.loads(stdout)
        return True, data, ""
    except json.JSONDecodeError as e:
        return False, None, f"Failed to parse flake archive output: {e}"


def _flatten_inputs(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten nested inputs from nix flake archive output.

    Returns dict mapping input names (e.g., 'nixpkgs', 'flake-parts.nixpkgs-lib')
    to their nix store paths.
    """
    result = {}
    inputs = data.get("inputs", {})

    for name, info in inputs.items():
        full_name = f"{prefix}.{name}" if prefix else name
        store_path = info.get("path", "")
        if store_path:
            result[full_name] = store_path
        # Recursively flatten nested inputs
        if "inputs" in info and info["inputs"]:
            nested = _flatten_inputs(info, full_name)
            result.update(nested)

    return result


def _format_size(size: int) -> str:
    """Format file size in human-readable form."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _validate_store_path(path: str) -> bool:
    """Validate that a path is within /nix/store/ and doesn't escape."""
    try:
        # Resolve the path to handle symlinks and relative components
        real_path = os.path.realpath(path)
        # Must be under /nix/store/
        return real_path.startswith("/nix/store/")
    except (OSError, ValueError):
        return False


def _is_binary_file(file_path: str, sample_size: int = 8192) -> bool:
    """Check if a file appears to be binary by looking for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            return b"\x00" in chunk
    except OSError:
        return True  # Assume binary if we can't read it


# =============================================================================
# Flake inputs main implementation functions
# =============================================================================


async def _flake_inputs_list(flake_dir: str) -> str:
    """List all flake inputs with their store paths."""
    if not _check_nix_available():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    success, data, err_msg = await _get_flake_inputs(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)
    if not inputs:
        return "No inputs found for this flake."

    # Get the flake's own path
    flake_path = data.get("path", flake_dir)

    lines = [f"Flake inputs ({len(inputs)} found):", f"Flake path: {flake_path}", ""]

    for name, store_path in sorted(inputs.items()):
        lines.append(f"* {name}")
        lines.append(f"  {store_path}")
        lines.append("")

    return "\n".join(lines).strip()


async def _flake_inputs_ls(flake_dir: str, query: str) -> str:
    """List directory contents within a flake input.

    Query format: 'input_name' or 'input_name:subpath'
    """
    if not _check_nix_available():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    # Parse query: input_name or input_name:path
    if ":" in query:
        input_name, subpath = query.split(":", 1)
        subpath = subpath.lstrip("/")
    else:
        input_name = query
        subpath = ""

    success, data, err_msg = await _get_flake_inputs(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)

    if input_name not in inputs:
        available = ", ".join(sorted(inputs.keys())[:10])
        more = f" ... and {len(inputs) - 10} more" if len(inputs) > 10 else ""
        return error(f"Input '{input_name}' not found. Available: {available}{more}", "NOT_FOUND")

    store_path = inputs[input_name]
    target_path = os.path.join(store_path, subpath) if subpath else store_path

    # Security: validate path stays within /nix/store/
    if not _validate_store_path(target_path):
        return error("Invalid path: must stay within /nix/store/", "SECURITY_ERROR")

    if not os.path.exists(target_path):
        return error(f"Path not found: {subpath or '/'} in {input_name}", "NOT_FOUND")

    if not os.path.isdir(target_path):
        return error(f"Not a directory: {subpath or '/'} in {input_name}", "NOT_DIRECTORY")

    try:
        entries = os.listdir(target_path)
    except PermissionError:
        return error(f"Permission denied: {subpath or '/'}", "PERMISSION_ERROR")
    except OSError as e:
        return error(f"Cannot list directory: {e}", "OS_ERROR")

    if not entries:
        return f"Directory '{subpath or '/'}' in {input_name} is empty."

    # Sort and categorize entries
    dirs: list[str] = []
    files: list[tuple[str, int | None]] = []

    for entry in sorted(entries):
        entry_path = os.path.join(target_path, entry)
        try:
            st = os.stat(entry_path)
            if stat.S_ISDIR(st.st_mode):
                dirs.append(entry)
            else:
                files.append((entry, st.st_size))
        except OSError:
            files.append((entry, None))

    display_path = f"{input_name}:{subpath}" if subpath else input_name
    lines = [f"Contents of {display_path} ({len(dirs)} dirs, {len(files)} files):", ""]

    for name in dirs:
        lines.append(f"  {name}/")

    for name, size in files:
        size_str = f" ({_format_size(size)})" if size is not None else ""
        lines.append(f"  {name}{size_str}")

    return "\n".join(lines)


async def _flake_inputs_read(flake_dir: str, query: str, limit: int) -> str:
    """Read a file from a flake input.

    Query format: 'input_name:path/to/file'
    """
    if not _check_nix_available():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    # Parse query: input_name:path
    if ":" not in query:
        return error("Read requires 'input:path' format (e.g., 'nixpkgs:flake.nix')", "INVALID_FORMAT")

    input_name, file_path = query.split(":", 1)
    file_path = file_path.lstrip("/")

    if not file_path:
        return error("File path required (e.g., 'nixpkgs:flake.nix')", "INVALID_FORMAT")

    success, data, err_msg = await _get_flake_inputs(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)

    if input_name not in inputs:
        available = ", ".join(sorted(inputs.keys())[:10])
        more = f" ... and {len(inputs) - 10} more" if len(inputs) > 10 else ""
        return error(f"Input '{input_name}' not found. Available: {available}{more}", "NOT_FOUND")

    store_path = inputs[input_name]
    target_path = os.path.join(store_path, file_path)

    # Security: validate path stays within /nix/store/
    if not _validate_store_path(target_path):
        return error("Invalid path: must stay within /nix/store/", "SECURITY_ERROR")

    if not os.path.exists(target_path):
        return error(f"File not found: {file_path} in {input_name}", "NOT_FOUND")

    if os.path.isdir(target_path):
        return error(f"'{file_path}' is a directory. Use type='ls' to list contents.", "IS_DIRECTORY")

    # Check file size
    try:
        file_size = os.path.getsize(target_path)
    except OSError as e:
        return error(f"Cannot access file: {e}", "OS_ERROR")

    if file_size > MAX_FILE_SIZE:
        return error(f"File too large: {_format_size(file_size)} (max {_format_size(MAX_FILE_SIZE)})", "FILE_TOO_LARGE")

    # Check for binary content
    if _is_binary_file(target_path):
        return error(f"Binary file detected: {file_path} ({_format_size(file_size)})", "BINARY_FILE")

    # Read file with line limit (single pass for efficiency)
    try:
        with open(target_path, encoding="utf-8", errors="replace") as f:
            lines = []
            total_lines = 0
            for i, line in enumerate(f):
                total_lines += 1
                if i < limit:
                    lines.append(line.rstrip("\n\r"))

        header = [f"File: {input_name}:{file_path}", f"Size: {_format_size(file_size)}", ""]

        if total_lines > limit:
            header.append(f"(Showing {limit} of {total_lines} lines)")
            header.append("")

        return "\n".join(header + lines)

    except PermissionError:
        return error(f"Permission denied: {file_path}", "PERMISSION_ERROR")
    except OSError as e:
        return error(f"Cannot read file: {e}", "OS_ERROR")


# =============================================================================
# MCP Tools (only 2 exposed)
# =============================================================================


@mcp.tool()
async def nix(
    action: Annotated[str, "search|info|stats|options|channels|flake-inputs"],
    query: Annotated[str, "Search term, name, or prefix. For flake-inputs: input_name or input:path"] = "",
    source: Annotated[str, "nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle"] = "nixos",
    type: Annotated[str, "packages|options|programs|list|ls|read"] = "packages",
    channel: Annotated[str, "unstable|stable|25.05"] = "unstable",
    limit: Annotated[int, "1-100 (or 1-2000 for flake-inputs read)"] = 20,
) -> str:
    """Query NixOS, Home Manager, Darwin, flakes, FlakeHub, Nixvim, Wiki, nix.dev, Noogle, or flake inputs."""
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
            return _search_nixos(query, type, limit, channel)
        elif source == "home-manager":
            return _search_home_manager(query, limit)
        elif source == "darwin":
            return _search_darwin(query, limit)
        elif source == "flakes":
            return _search_flakes(query, limit)
        elif source == "flakehub":
            return _search_flakehub(query, limit)
        elif source == "nixvim":
            return _search_nixvim(query, limit)
        elif source == "wiki":
            return _search_wiki(query, limit)
        elif source == "nix-dev":
            return _search_nixdev(query, limit)
        elif source == "noogle":
            return _search_noogle(query, limit)
        else:
            return error("Source must be nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle")

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
        elif source == "flakehub":
            return _info_flakehub(query)
        elif source == "nixvim":
            return _info_nixvim(query)
        elif source == "wiki":
            return _info_wiki(query)
        elif source == "nix-dev":
            return error("Info not available for nix-dev. Use search to find docs, then visit the URL.")
        elif source == "noogle":
            return _info_noogle(query)
        else:
            return error("Source must be nixos|home-manager|darwin|flakehub|nixvim|wiki|nix-dev|noogle")

    elif action == "stats":
        if source == "nixos":
            return _stats_nixos(channel)
        elif source == "home-manager":
            return _stats_home_manager()
        elif source == "darwin":
            return _stats_darwin()
        elif source == "flakes":
            return _stats_flakes()
        elif source == "flakehub":
            return _stats_flakehub()
        elif source == "nixvim":
            return _stats_nixvim()
        elif source == "noogle":
            return _stats_noogle()
        elif source in ["wiki", "nix-dev"]:
            return error(f"Stats not available for {source}")
        else:
            return error("Source must be nixos|home-manager|darwin|flakes|flakehub|nixvim|wiki|nix-dev|noogle")

    elif action == "options":
        if source not in ["home-manager", "darwin", "nixvim", "noogle"]:
            return error("Options browsing only for home-manager|darwin|nixvim|noogle")
        if source == "nixvim":
            return _browse_nixvim_options(query)
        if source == "noogle":
            return _browse_noogle_options(query)
        return _browse_options(source, query)

    elif action == "channels":
        return _list_channels()

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

    else:
        return error("Action must be search|info|stats|options|channels|flake-inputs")


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
