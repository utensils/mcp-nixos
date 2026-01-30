"""Cache classes for MCP-NixOS server."""

import json
import re
from typing import Any

import requests

from .config import (
    FALLBACK_CHANNELS,
    NIXDEV_SEARCH_INDEX,
    NIXOS_API,
    NIXOS_AUTH,
    NIXVIM_META_BASE,
    NOOGLE_API,
    APIError,
)


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

            if self.index is None:
                raise APIError("Failed to parse nix.dev index: empty result")
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
