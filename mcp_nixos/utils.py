"""Utility functions for MCP-NixOS server."""

import os
import re
from datetime import UTC, datetime
from typing import Any, TypedDict

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .config import DocumentParseError


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


def _option_matches(name: str, query: str, prefix: str) -> bool:
    """Return whether an option name matches the requested filters."""
    if query and query.lower() not in name.lower():
        return False
    return not prefix or name.startswith(prefix + ".") or name == prefix


def score_option_match(name: str, description: str, query: str) -> int:
    """Score how well an option matches a query, prioritizing path matches.

    Tiers: exact path (100), leading path prefix (80), complete dot-separated
    path segment(s) (70 minus the segment position, floored at 62), name
    substring (60), description substring (20). The segment tier ranks
    ``programs.git.enable`` above ``programs.bun.enableGitIntegration`` for
    the query ``git``, and the position penalty ranks it above deeper segment
    matches such as ``programs.difftastic.git.enable``.
    """
    query_cf = query.casefold()
    if not query_cf:
        return 0
    name_cf = name.casefold()

    if name_cf == query_cf:
        return 100
    if name_cf.startswith(query_cf + "."):
        return 80

    name_parts = name_cf.split(".")
    query_parts = query_cf.split(".")
    for start in range(len(name_parts) - len(query_parts) + 1):
        if name_parts[start : start + len(query_parts)] == query_parts:
            return 70 - min(start, 8)

    if query_cf in name_cf:
        return 60
    if query_cf in description.casefold():
        return 20
    return 0


def _parse_home_manager_mdbook(soup: BeautifulSoup, query: str, prefix: str, limit: int | None) -> list[dict[str, str]]:
    """Parse options from an mdBook-style document (Home Manager docs)."""
    options: list[dict[str, str]] = []

    for heading in soup.select('h2[id^="opt-"]'):
        anchor = heading.find("a", class_="header")
        name = anchor.get_text(" ", strip=True) if isinstance(anchor, Tag) else heading.get_text(" ", strip=True)
        if not name or not _option_matches(name, query, prefix):
            continue

        description_parts: list[str] = []
        type_info = ""
        metadata_started = False

        for sibling in heading.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            if sibling.name in {"h1", "h2"}:
                break
            if sibling.name != "p":
                continue

            label = sibling.find("em")
            label_text = label.get_text(" ", strip=True) if isinstance(label, Tag) else ""
            if label_text == "Type:":
                metadata_started = True
                type_info = sibling.get_text(" ", strip=True).removeprefix("Type:").strip()
            elif label_text in {"Default:", "Example:", "Declared by:"}:
                metadata_started = True
            elif not metadata_started:
                description_parts.append(sibling.get_text(" ", strip=True))

        description = " ".join(description_parts)
        options.append(
            {
                "name": name,
                "description": description[:200] if len(description) > 200 else description,
                "type": type_info,
            }
        )
        if limit is not None and len(options) >= limit:
            break

    return options


def parse_html_options(url: str, query: str = "", prefix: str = "", limit: int | None = 100) -> list[dict[str, str]]:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Dispatch on document structure, not URL: mdBook option docs (Home
        # Manager) mark each option with an h2 "opt-" heading, while DocBook
        # manuals (nix-darwin) use dt/dd definition lists.
        if soup.select_one('h2[id^="opt-"]') is not None:
            return _parse_home_manager_mdbook(soup, query, prefix, limit)

        options: list[dict[str, str]] = []
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
            if not _option_matches(name, query, prefix):
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
                if limit is not None and len(options) >= limit:
                    break
        return options
    except Exception as exc:
        raise DocumentParseError(f"Failed to fetch docs: {str(exc)}") from exc


# =============================================================================
# Version helpers
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
    """Format a single release entry with version, date, platforms, and commit info.

    Handles v1/pkg format where:
    - platforms is an array of system names ["x86_64-linux", ...]
    - commit_hash is at the release level
    - systems is a dict with system info including attr_paths
    - last_updated is an epoch timestamp (int)
    """
    results: list[str] = []
    version = release.get("version", "unknown")

    results.append(f"* {version}")

    # Handle last_updated as either ISO string or epoch timestamp
    last_updated = release.get("last_updated")
    if last_updated:
        try:
            if isinstance(last_updated, int | float):
                # Epoch timestamp - use UTC to match NixHub's timezone
                dt = datetime.fromtimestamp(last_updated, tz=UTC)
            else:
                # ISO string
                dt = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
            results.append(f"  Updated: {dt.strftime('%Y-%m-%d')}")
        except Exception:
            pass  # Skip malformed timestamps; omit Updated line rather than failing

    # Platforms can be either:
    # 1. Array of system names: ["x86_64-linux", "aarch64-darwin", ...]
    # 2. Array of dicts with "system" key (old format)
    platforms = release.get("platforms", [])
    if platforms:
        platform_systems: set[str] = set()
        for p in platforms:
            if isinstance(p, str):
                # Direct system name
                platform_systems.add(p)
            elif isinstance(p, dict):
                # Dict with "system" key
                sys = p.get("system", "")
                if sys:
                    platform_systems.add(sys)

        if platform_systems:
            # Simplify platform display
            has_linux = any("linux" in s for s in platform_systems)
            has_darwin = any("darwin" in s for s in platform_systems)
            if has_linux and has_darwin:
                results.append("  Platforms: Linux and macOS")
            elif has_linux:
                results.append("  Platforms: Linux")
            elif has_darwin:
                results.append("  Platforms: macOS")
            else:
                results.append(f"  Platforms: {', '.join(sorted(platform_systems))}")

    # Show commit info - in v1/pkg format, commit_hash is at release level
    commit = release.get("commit_hash", "")
    if commit and re.match(r"^[a-fA-F0-9]{40}$", commit):
        results.append(f"  Nixpkgs commit: {commit}")

        # Get attribute path from systems dict
        systems_dict = release.get("systems", {})
        if isinstance(systems_dict, dict):
            for sys_info in systems_dict.values():
                if isinstance(sys_info, dict):
                    attr_paths = sys_info.get("attr_paths", [])
                    if attr_paths:
                        results.append(f"  Attribute: {attr_paths[0]}")
                        break
    return results


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


# =============================================================================
# NarInfo parsing
# =============================================================================


class NarInfo(TypedDict, total=False):
    """Typed dictionary for parsed narinfo data."""

    file_size: int
    nar_size: int
    compression: str
    store_path: str
    url: str


def _parse_narinfo(text: str) -> NarInfo:
    """Parse a narinfo file and return key fields."""
    result: NarInfo = {}
    for line in text.split("\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "filesize":
            try:
                result["file_size"] = int(value)
            except ValueError:
                pass  # Skip malformed values; omit field rather than failing parse
        elif key == "narsize":
            try:
                result["nar_size"] = int(value)
            except ValueError:
                pass  # Skip malformed values; omit field rather than failing parse
        elif key == "compression":
            result["compression"] = value
        elif key == "storepath":
            result["store_path"] = value
        elif key == "url":
            result["url"] = value

    return result


# =============================================================================
# Path validation and file utilities
# =============================================================================


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


def _read_file_with_limit(file_path: str, limit: int) -> tuple[list[str], int]:
    """Read a file with line limit (runs in thread pool).

    Returns (lines, total_lines) tuple.
    """
    with open(file_path, encoding="utf-8", errors="replace") as f:
        lines = []
        total_lines = 0
        for i, line in enumerate(f):
            total_lines += 1
            if i < limit:
                lines.append(line.rstrip("\n\r"))
    return lines, total_lines
