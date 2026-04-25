"""Base functionality shared across data sources."""

import re
from typing import Any

import requests

from ..caches import channel_cache
from ..config import (
    DARWIN_URL,
    HOME_MANAGER_URL,
    NIXOS_API,
    NIXOS_AUTH,
    APIError,
)
from ..utils import error, parse_html_options

# Match the 40-char hex commit appended to unstable ES indices,
# e.g. `nixos-46-unstable-b12141ef619e0a9c1c84dc8c684040326f27cdcc`.
_COMMIT_IN_INDEX = re.compile(r"-([0-9a-f]{40})$")

# Per-process cache for GitHub channel HEAD lookups. Persists for the
# lifetime of the MCP server; populated lazily. Keys are nixpkgs branch names
# (e.g. "nixos-unstable", "nixos-25.11"), so multiple channel aliases pointing
# to the same branch share a single lookup.
_BRANCH_REVS: dict[str, str] = {}

# =============================================================================
# Channel helpers
# =============================================================================


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


# =============================================================================
# Browsing utilities
# =============================================================================


def _channel_to_branch(name: str, index: str, resolved: dict[str, str]) -> str:
    """Map a channel name to its nixpkgs branch for commit lookups."""
    if "unstable" in name or "unstable" in index:
        return "nixos-unstable"
    if name in {"stable", "beta"}:
        # Resolve to the release version indirectly via the ES index name.
        parts = index.split("-")
        if len(parts) >= 4 and re.match(r"^\d+\.\d+$", parts[3]):
            return f"nixos-{parts[3]}"
        return ""
    if re.match(r"^\d+\.\d+$", name):
        return f"nixos-{name}"
    return ""


def _channel_revision(name: str, index: str, resolved: dict[str, str]) -> str:
    """Resolve the current HEAD commit for a channel.

    When the commit is embedded in the ES index name (older unstable indices),
    use it directly. Otherwise do a best-effort GitHub API fetch keyed by
    branch, with a short timeout and graceful degradation on failure or rate
    limits.
    """
    embedded = _COMMIT_IN_INDEX.search(index)
    if embedded:
        return embedded.group(1)

    branch = _channel_to_branch(name, index, resolved)
    if not branch:
        return ""
    if branch in _BRANCH_REVS:
        return _BRANCH_REVS[branch]

    try:
        resp = requests.get(
            f"https://api.github.com/repos/NixOS/nixpkgs/commits/{branch}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=4,
        )
        if resp.status_code == 200:
            rev = resp.json().get("sha", "") or ""
            _BRANCH_REVS[branch] = rev
            return rev
    except requests.RequestException:
        pass
    return ""


def _list_channels() -> str:
    """List available NixOS channels with status, document counts, and HEAD commit."""
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
            rev = _channel_revision(name, index, configured)
            if rev:
                branch = _channel_to_branch(name, index, configured)
                branch_note = f" ({branch})" if branch else ""
                results.append(f"  Revision: {rev}{branch_note}")
            results.append("")

        results.append(
            "Note: 'stable' always points to current stable release. Revisions show the "
            "nixpkgs HEAD commit for the channel's branch — use this to compare commit "
            "hashes against a channel or pass to `nix_versions` for version history."
        )
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
