"""Utility functions for MCP-NixOS server."""

import os
import re
from datetime import UTC, datetime
from typing import Any, TypedDict

import requests
from bs4 import BeautifulSoup

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
