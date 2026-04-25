"""Base functionality shared across data sources."""

import re
import time
from typing import Any

import requests

from .. import __version__
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

# Short per-process cache for GitHub branch HEAD lookups, keyed by nixpkgs
# branch name. Entries expire after ~10 minutes so a long-running MCP
# process does not keep reporting a stale HEAD after upstream advances
# (see CodeRabbit review on PR #147). Channel aliases pointing to the
# same branch share a single lookup.
_BRANCH_REV_TTL = 600.0
_BRANCH_REVS: dict[str, tuple[str, float]] = {}

_GITHUB_USER_AGENT = f"mcp-nixos/{__version__}"

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


def _channel_revision(name: str, index: str, resolved: dict[str, str]) -> tuple[str, str]:
    """Resolve a commit for a channel along with its provenance.

    Returns ``(sha, source)`` where ``source`` is:

    - ``"indexed"`` — the commit is embedded in the ES index name, so the
      package/option data returned for this channel was built from exactly
      this commit. Safe to compare against with ``nix_versions``.
    - ``"branch_head"`` — best-effort GitHub API fetch of the channel
      branch's current HEAD. This may be a few commits ahead of the
      published search index, so it is a *pointer* to the channel, not a
      claim about the indexed data.
    - ``""`` (empty) when nothing could be resolved.
    """
    embedded = _COMMIT_IN_INDEX.search(index)
    if embedded:
        return embedded.group(1), "indexed"

    branch = _channel_to_branch(name, index, resolved)
    if not branch:
        return "", ""
    cached = _BRANCH_REVS.get(branch)
    now = time.monotonic()
    if cached and (now - cached[1]) < _BRANCH_REV_TTL:
        return cached[0], "branch_head"

    try:
        resp = requests.get(
            f"https://api.github.com/repos/NixOS/nixpkgs/commits/{branch}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": _GITHUB_USER_AGENT,
            },
            timeout=4,
        )
        if resp.status_code == 200:
            data = resp.json()
            rev = data.get("sha", "") if isinstance(data, dict) else ""
            if rev:
                _BRANCH_REVS[branch] = (rev, now)
                return rev, "branch_head"
    except (requests.RequestException, ValueError):
        # ValueError covers json decoding failures on a 200 with a non-JSON
        # body (rare, but e.g. GitHub interstitials). Treat as a miss so the
        # channels listing can still fall back to a stale cache or empty rev.
        pass
    # Fall back to a stale cached value if the refresh attempt failed —
    # better to surface last-known HEAD than nothing.
    if cached:
        return cached[0], "branch_head"
    return "", ""


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
            rev, source = _channel_revision(name, index, configured)
            branch = _channel_to_branch(name, index, configured)
            if branch:
                results.append(f"  Branch: {branch}")
            if rev and source == "indexed":
                # Exact commit the search index was built from — safe to
                # compare package versions against.
                results.append(f"  Revision (indexed): {rev}")
            elif rev and source == "branch_head":
                # Upstream branch HEAD; the search index for this channel
                # may lag by a handful of commits.
                results.append(f"  Branch HEAD: {rev} (upstream; may be ahead of indexed data)")
            results.append("")

        results.append(
            "Note: 'stable' always points to current stable release. "
            "'Revision (indexed)' is the exact commit the search index was built from "
            "(safe to compare against `nix_versions`). 'Branch HEAD' is the upstream "
            "branch tip, fetched best-effort from GitHub and cached for up to "
            "10 minutes per process — it may be a few commits ahead of the "
            "indexed data or a few minutes stale from the upstream ref."
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
