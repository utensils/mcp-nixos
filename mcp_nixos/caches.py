"""Cache classes for MCP-NixOS server."""

from __future__ import annotations

import json
import re
import threading
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from .config import (
    DARWIN_URL,
    FALLBACK_CHANNELS,
    HOME_MANAGER_URL,
    NIXDEV_SEARCH_INDEX,
    NIXOS_API,
    NIXOS_AUTH,
    NIXVIM_OPTIONS_CHUNKS_BASE,
    NOOGLE_API,
    NVF_OPTIONS_URL,
    APIError,
)
from .utils import parse_html_options

if TYPE_CHECKING:
    from .sources.nvf import NvfOption


class ChannelCache:
    """Cache for discovered channels and resolved mappings."""

    # Matches `latest-<gen>-nixos-<channel>` aliases, where <channel> is either
    # the string "unstable" or a release like "25.11". The generation captured
    # in group 1 is what disambiguates rollovers — when Hydra publishes a new
    # index for a channel it increments the generation and atomically retargets
    # the alias, so the highest generation is always the freshest data.
    _ALIAS_RE = re.compile(r"^latest-(\d+)-nixos-(unstable|\d+\.\d+)$")

    # After a failed alias probe, serve the fallback for this long before
    # spending another round of requests. Without it, an outage makes every
    # concurrent caller queue behind the lock for its own 10s timeout, since
    # fallback results are deliberately not memoized.
    _DISCOVERY_RETRY_COOLDOWN = 30.0

    # An alias observed empty means Hydra is mid-publish. Counts — and the
    # resolution derived from them — are a snapshot of that window, so they
    # expire: otherwise the process stays pinned to the older generation (or,
    # if every alias was empty, to the fallback) until it restarts.
    _ROLLOVER_RECHECK = 300.0

    def __init__(self) -> None:
        # Alias *names* and their document counts are cached separately: names
        # are what channel resolution needs, counts are display-only. A partial
        # `_count` failure must not shrink the set of channels we can resolve.
        self.alias_names: list[str] | None = None
        # Aliases whose `_count` came back 200 with zero documents. Hydra
        # publishes the alias before the index finishes filling, so during a
        # rollover the newest generation can be live but empty — resolving to it
        # would fail every search for that channel. Distinct from an alias whose
        # probe merely failed, which stays a candidate.
        self.empty_aliases: set[str] = set()
        self.available_channels: dict[str, str] | None = None
        self.resolved_channels: dict[str, str] | None = None
        self.using_fallback: bool = False
        self._failed_at: float | None = None
        self._rollover_at: float | None = None
        # Every tool call reaches this cache through `asyncio.to_thread`, so
        # concurrent first requests can race. The lock keeps each population
        # decision atomic; the fallback verdict is threaded through return
        # values rather than shared state so one resolution cannot act on
        # another's outcome.
        self._lock = threading.Lock()

    def get_available(self) -> dict[str, str]:
        with self._lock:
            self._expire_rollover_locked()
            return self._available_locked()

    def _expire_rollover_locked(self) -> None:
        """Drop discovery state captured while a rollover was in progress."""
        if self._rollover_at is None or (time.monotonic() - self._rollover_at) < self._ROLLOVER_RECHECK:
            return
        self._rollover_at = None
        self.alias_names = None
        self.available_channels = None
        self.resolved_channels = None
        self.empty_aliases = set()

    def _aliases_locked(self) -> list[str]:
        """Live alias names, cached once a probe succeeds.

        A failed probe is not cached — the hardcoded fallback goes stale, so the
        next call must retry — but it does start a cooldown so an outage does
        not make every caller pay for its own round of requests.
        """
        if self.alias_names is not None:
            return self.alias_names
        if self._failed_at is not None and (time.monotonic() - self._failed_at) < self._DISCOVERY_RETRY_COOLDOWN:
            return []
        aliases = self._list_aliases()
        if aliases:
            self.alias_names = aliases
            self._failed_at = None
        else:
            self._failed_at = time.monotonic()
        return aliases

    def _available_locked(self) -> dict[str, str]:
        if self.available_channels is not None:
            return self.available_channels
        counted, empty, complete = self._discover_available_channels()
        self.empty_aliases = empty
        # Start (or clear) the rollover clock so this snapshot cannot outlive
        # the publish window it was taken in.
        self._rollover_at = time.monotonic() if empty else None
        # Cache only a complete listing. A partial one means some `_count`
        # probes failed transiently, and memoizing it would report those
        # channels as Unavailable for the life of the process.
        if complete:
            self.available_channels = counted
        return counted

    def get_resolved(self) -> dict[str, str]:
        with self._lock:
            self._expire_rollover_locked()
            if self.resolved_channels is not None:
                return self.resolved_channels
            resolved, used_fallback, cacheable = self._resolve_channels()
            self.using_fallback = used_fallback
            if used_fallback or not cacheable:
                # Never memoize a fallback: the hardcoded generations go stale
                # and a retired alias 404s on every query, so caching one
                # transient discovery failure would poison the whole process.
                # `cacheable` is False when a `_count` probe failed, which means
                # a selected alias might turn out to be an empty rollover index.
                return resolved
            self.resolved_channels = resolved
            return resolved

    def _list_aliases(self) -> list[str]:
        """Return live `latest-<gen>-nixos-<channel>` alias names, newest first.

        Replaces a hardcoded `[43..46]` probe loop with a single
        `_cat/aliases` call, so newly published channel generations
        (e.g. `latest-48-nixos-unstable` after Hydra rolls forward) are
        picked up automatically instead of bit-rotting in the source.
        """
        try:
            resp = requests.get(
                f"{NIXOS_API}/_cat/aliases?format=json",
                auth=NIXOS_AUTH,
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            entries = resp.json()
            if not isinstance(entries, list):
                return []
        except Exception:
            return []

        return [
            entry["alias"]
            for entry in entries
            if isinstance(entry, dict) and self._ALIAS_RE.match(str(entry.get("alias", "")))
        ]

    def _discover_available_channels(self) -> tuple[dict[str, str], set[str], bool]:
        """Map each live alias to its document count.

        Returns `(counts, empty, complete)`:
        - `counts` — aliases that hold documents, with a formatted count.
        - `empty` — aliases confirmed to hold zero documents. Resolution must
          skip these; an alias whose probe *failed* is absent from both sets and
          stays a candidate.
        - `complete` — False when any probe failed, so the caller knows `counts`
          is not cacheable.
        """
        available: dict[str, str] = {}
        empty: set[str] = set()
        aliases = self._aliases_locked()
        complete = bool(aliases)
        for alias in aliases:
            try:
                count_resp = requests.post(
                    f"{NIXOS_API}/{alias}/_count",
                    json={"query": {"match_all": {}}},
                    auth=NIXOS_AUTH,
                    timeout=10,
                )
                if count_resp.status_code == 200:
                    count = count_resp.json().get("count", 0)
                    if count > 0:
                        available[alias] = f"{count:,} documents"
                    else:
                        empty.add(alias)
                else:
                    complete = False
            except Exception:
                complete = False
                continue
        return available, empty, complete

    def _resolve_channels(self) -> tuple[dict[str, str], bool, bool]:
        """Resolve channel names to aliases.

        Returns `(mapping, used_fallback, cacheable)`. The verdicts are returned
        rather than stored so a concurrent resolution cannot flip them out from
        under this one.
        """
        # Resolution reads alias *names*, not the counted listing: a cluster that
        # serves `_cat/aliases` while refusing `_count` still tells us exactly
        # which channels are live, and a partial count failure must not silently
        # drop a channel like `stable` from the mapping.
        aliases = self._aliases_locked()
        if not aliases:
            return FALLBACK_CHANNELS.copy(), True, False

        # Probe counts so confirmed-empty aliases can be skipped. Hydra publishes
        # an alias before its index has filled, so mid-rollover the highest
        # generation may exist with zero documents — resolving to it would fail
        # every search for that channel until the process restarts.
        self._available_locked()
        # `available_channels` is only populated from a complete probe, so this
        # doubles as "every alias has a known document count". When some probe
        # failed, the winning alias might be an empty rollover index we could not
        # rule out, so the result must not be memoized.
        cacheable = self.available_channels is not None
        available = [alias for alias in aliases if alias not in self.empty_aliases]
        if not available:
            return FALLBACK_CHANNELS.copy(), True, False

        # Bucket aliases by channel name ("unstable", "25.11", ...) and
        # remember each candidate's generation so we can pick the maximum
        # per channel. The previous implementation picked the *first*
        # unstable match in dict-insertion order, which yielded the lowest
        # generation when multiple unstable indices were live.
        by_channel: dict[str, list[tuple[int, str]]] = {}
        for pattern in available:
            match = self._ALIAS_RE.match(pattern)
            if not match:
                continue
            gen = int(match.group(1))
            channel = match.group(2)
            by_channel.setdefault(channel, []).append((gen, pattern))

        for candidates in by_channel.values():
            candidates.sort(reverse=True)  # highest generation first

        resolved: dict[str, str] = {}
        if "unstable" in by_channel:
            resolved["unstable"] = by_channel["unstable"][0][1]

        release_versions = sorted(
            (v for v in by_channel if v != "unstable"),
            key=lambda v: tuple(int(p) for p in v.split(".")),
            reverse=True,
        )

        for version in release_versions:
            resolved[version] = by_channel[version][0][1]

        if release_versions:
            resolved["stable"] = resolved[release_versions[0]]
            resolved["beta"] = resolved["stable"]

        if not resolved:
            return FALLBACK_CHANNELS.copy(), True, False
        return resolved, False, cacheable


channel_cache = ChannelCache()


class NixvimCache:
    """Cache for Nixvim options fetched from NuschtOS chunked JSON.

    As of mid-2026 the NuschtOS search frontend for nix-community/nixvim was
    reorganized: the old `…/search/meta/N.json` layout was removed and replaced
    with a WASM-backed frontend at `…/search/data/options/`. The options data
    itself is exposed as `chunks/N.json` (≈300 options per chunk, JSON array).

    This loader walks chunks sequentially until it sees a 404, flattens them
    into a single in-memory list, and serves subsequent calls from cache. The
    full set currently runs to ~60 chunks / ~17k options / a few MB and fits
    comfortably in memory; we re-scan in Python for keyword matching, avoiding
    the WASM dependency entirely.
    """

    def __init__(self) -> None:
        self.options: list[dict[str, Any]] | None = None
        self._init_lock = threading.Lock()

    def get_options(self) -> list[dict[str, Any]]:
        """Fetch and cache all Nixvim options from NuschtOS chunk JSON."""
        if self.options is not None:
            return self.options

        with self._init_lock:
            if self.options is not None:
                return self.options

            all_options: list[dict[str, Any]] = []
            chunk_id = 0
            try:
                while True:
                    url = f"{NIXVIM_OPTIONS_CHUNKS_BASE}/{chunk_id}.json"
                    resp = requests.get(url, timeout=30)

                    if resp.status_code == 404:
                        # Treat as end-of-pagination — but a 404 on the *first*
                        # chunk almost always means a config error (wrong base URL
                        # or layout change), so surface that distinctly.
                        if chunk_id == 0:
                            raise APIError(
                                f"First Nixvim options chunk returned 404 at {url}; "
                                "the NuschtOS data layout may have changed again."
                            )
                        break

                    resp.raise_for_status()
                    chunk_data = resp.json()

                    if isinstance(chunk_data, list):
                        all_options.extend(chunk_data)
                    else:
                        # Unexpected payload: a layout/format change in the
                        # middle of the chunk sequence. Fail loud so we don't
                        # silently cache a partial option set.
                        raise APIError(
                            f"Unexpected Nixvim options payload at {url}: "
                            f"expected JSON list, got {type(chunk_data).__name__}."
                        )

                    chunk_id += 1

                self.options = all_options
                return self.options
            except requests.Timeout as exc:
                raise APIError("Timeout fetching Nixvim options") from exc
            except requests.RequestException as exc:
                raise APIError(f"Failed to fetch Nixvim options: {exc}") from exc
            except APIError:
                raise
            except Exception as exc:
                raise APIError(f"Failed to parse Nixvim options: {exc}") from exc


nixvim_cache = NixvimCache()


class NvfCache:
    """Cache NVF's canonical ``vim.*`` options from its published docs."""

    def __init__(self) -> None:
        self.options: list[NvfOption] | None = None

    @staticmethod
    def _extract_text(option: Tag, selector: str, label: str = "") -> str:
        """Extract a field as readable plain text, preserving code blocks."""
        field = option.select_one(selector)
        if field is None:
            return ""

        preserve_lines = field.find("pre") is not None
        separator = "\n" if preserve_lines else " "
        value = field.get_text(separator=separator, strip=True)
        if label and value.startswith(label):
            value = value[len(label) :].lstrip()

        if preserve_lines:
            return "\n".join(line.rstrip() for line in value.splitlines()).strip()
        return " ".join(value.split())

    @classmethod
    def _parse_options(cls, html: bytes | str) -> list[NvfOption]:
        """Parse normalized NVF option records from ``options.html``."""
        soup = BeautifulSoup(html, "html.parser")
        options: list[NvfOption] = []

        for option in soup.select(".options-container .option"):
            anchor = option.select_one(".option-name .option-anchor")
            if anchor is None:
                continue

            name = anchor.get_text(" ", strip=True)
            if name != "vim" and not name.startswith("vim."):
                continue

            declarations: list[str] = []
            for declaration in option.select(".option-declared a[href]"):
                href = declaration.get("href")
                if isinstance(href, str):
                    declarations.append(urljoin(NVF_OPTIONS_URL, href))

            anchor_href = anchor.get("href")
            if isinstance(anchor_href, str):
                option_url = urljoin(NVF_OPTIONS_URL, anchor_href)
            else:
                option_id = option.get("id")
                fragment = f"#{option_id}" if isinstance(option_id, str) and option_id else ""
                option_url = f"{NVF_OPTIONS_URL}{fragment}"

            options.append(
                {
                    "name": name,
                    "type": cls._extract_text(option, ".option-type", "Type:"),
                    "description": cls._extract_text(option, ".option-description"),
                    "default": cls._extract_text(option, ".option-default", "Default:"),
                    "example": cls._extract_text(option, ".option-example", "Example:"),
                    "declarations": declarations,
                    "url": option_url,
                }
            )

        return options

    def get_options(self) -> list[NvfOption]:
        """Fetch, validate, and cache the latest published NVF options."""
        if self.options is not None:
            return self.options

        try:
            response = requests.get(NVF_OPTIONS_URL, timeout=30)
            response.raise_for_status()
            options = self._parse_options(response.content)
            if not options:
                raise APIError("Failed to parse NVF options: no canonical vim.* options found")

            self.options = options
            return self.options
        except requests.Timeout as exc:
            raise APIError("Timeout fetching NVF options") from exc
        except requests.RequestException as exc:
            raise APIError(f"Failed to fetch NVF options: {exc}") from exc
        except APIError:
            raise
        except Exception as exc:
            raise APIError(f"Failed to parse NVF options: {exc}") from exc


nvf_cache = NvfCache()


class HtmlOptionsCache:
    """Process-local cache for an HTML-parsed option catalogue.

    Home Manager and nix-darwin publish their full option catalogues as
    single HTML documents (~4 MB for Home Manager). Parsing once per process
    lets search, info, browse, and stats filter in memory instead of
    re-downloading and re-parsing the document on every request.
    """

    def __init__(self, url: str, display_name: str) -> None:
        self.url = url
        self.display_name = display_name
        self.options: list[dict[str, str]] | None = None

    def get_options(self) -> list[dict[str, str]]:
        """Fetch, parse, and cache the full option catalogue."""
        if self.options is not None:
            return self.options

        options = parse_html_options(self.url, limit=None)
        if not options:
            raise APIError(f"Failed to parse {self.display_name} options: no options found")

        self.options = options
        return self.options


home_manager_cache = HtmlOptionsCache(HOME_MANAGER_URL, "Home Manager")
darwin_cache = HtmlOptionsCache(DARWIN_URL, "nix-darwin")


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
