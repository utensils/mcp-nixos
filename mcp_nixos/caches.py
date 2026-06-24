"""Cache classes for MCP-NixOS server."""

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from bs4 import BeautifulSoup

from .config import (
    DEN_BASE_URL,
    DEN_OVERVIEW_URL,
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


class DenCache:
    """Cache for Den framework docs (https://den.denful.dev).

    The Den site is built with Starlight (Astro 5). The site exposes no
    `sitemap.xml` and no Pagefind JSON metadata (the Pagefind index is a
    bincode binary that needs WASM to read), so the loader does its own
    walk:

    1. **Discovery** — fetch the `/overview/` page once. Its sidebar links
       to every doc page; we extract the `/explanation/|/guides/|/reference/
       |/tutorials/|/motivation/|/maintainers/|/overview/` paths.
    2. **Parallel fetch** — fetch each page in a bounded thread pool
       (10 workers), parse the title (`<h1 id="_top">`) and the
       `<main data-pagefind-body>` body, strip HTML to plain text.
    3. **Index** — hold a flat in-memory `pages: list[dict]` plus a
       `by_path: dict[str, dict]` for exact lookups by `/path/`.

    Total payload is small (≈50 pages × a few KB each) so the in-memory
    copy is cheap. The full walk happens once per process; subsequent
    search/info/browse calls are O(n) over the cached list.
    """

    # Path prefixes we consider "doc pages" (vs. meta pages like
    # `/community/`, `/contributing/`, `/releases/`, `/`, etc.).
    _DOC_PATH_PREFIXES = (
        "/explanation/",
        "/guides/",
        "/reference/",
        "/tutorials/",
        "/motivation/",
        "/maintainers/",
        "/overview/",
    )

    _MAX_WORKERS = 10

    def __init__(self) -> None:
        self.pages: list[dict[str, Any]] | None = None
        self._by_path: dict[str, dict[str, Any]] | None = None
        self._init_lock = threading.Lock()

    def get_pages(self) -> list[dict[str, Any]]:
        """Fetch and cache all Den doc pages.

        Concurrency-safe via double-checked locking: N concurrent first
        callers all see the cold cache, but only one performs the walk;
        the rest wait and consume the cached list.
        """
        if self.pages is not None:
            return self.pages

        with self._init_lock:
            if self.pages is not None:
                return self.pages

            paths = self._discover_paths()
            if not paths:
                raise APIError("No Den docs paths discovered from /overview/")

            all_pages: list[dict[str, Any]] = []
            # `future.result()` re-raises whatever `_fetch_page` raised in its
            # worker thread; we wrap those per-page (a Timeout is a
            # RequestException, so it's covered too). Nothing else inside the
            # pool block raises a `requests` error, so no outer handler is needed.
            with ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as pool:
                futures = {pool.submit(self._fetch_page, path): path for path in paths}
                for future in as_completed(futures):
                    path = futures[future]
                    try:
                        page = future.result()
                    except requests.RequestException as exc:
                        raise APIError(f"Failed to fetch Den page {path}: {exc}") from exc
                    except Exception as exc:
                        raise APIError(f"Failed to parse Den page {path}: {exc}") from exc
                    if page is not None:
                        all_pages.append(page)

            # Sort by path for deterministic downstream output (search, info,
            # browse) — `as_completed()` yields in completion order.
            all_pages.sort(key=lambda p: p.get("path", ""))
            self.pages = all_pages
            self._by_path = {p["path"]: p for p in all_pages if p.get("path")}
            return self.pages

    def get_by_path(self, path: str) -> dict[str, Any] | None:
        """Look up a page by its canonical `/path/` (with trailing slash)."""
        if self._by_path is None:
            self.get_pages()
        return self._by_path.get(self._normalize_path(path)) if self._by_path else None

    def _discover_paths(self) -> list[str]:
        """Read `/overview/` and return unique doc paths in document order."""
        try:
            resp = requests.get(DEN_OVERVIEW_URL, timeout=15)
        except requests.RequestException as exc:
            raise APIError(f"Failed to fetch Den overview: {exc}") from exc
        if resp.status_code != 200:
            raise APIError(f"Den overview returned HTTP {resp.status_code} (expected 200)")

        soup = BeautifulSoup(resp.content, "html.parser")
        seen: set[str] = set()
        paths: list[str] = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Skip anchors, external links, and trailing-slash-only links.
            if not href.startswith("/"):
                continue
            # Normalize to a canonical `/foo/bar/` path (drops query/fragment,
            # unquotes, collapses `//`, ensures trailing slash).
            href = self._normalize_path(href)
            if not any(href.startswith(p) for p in self._DOC_PATH_PREFIXES):
                continue
            if href in seen:
                continue
            seen.add(href)
            paths.append(href)
        return paths

    @staticmethod
    def _fetch_page(path: str) -> dict[str, Any] | None:
        """Fetch a single Den page and extract title + body.

        Returns None only for 404 / 410 (the linked page no longer exists).
        Any other non-2xx response (5xx, 429, etc.) raises so a transient
        upstream incident doesn't silently produce a partial index.
        """
        url = f"{DEN_BASE_URL}{path}"
        resp = requests.get(url, timeout=15)
        if resp.status_code in (404, 410):
            return None
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Title: <h1 id="_top"> on every Starlight page.
        h1 = soup.find("h1", id="_top")
        title = h1.get_text(strip=True) if h1 else path.strip("/").replace("-", " ").title()

        # Body: prefer the <main data-pagefind-body> element Starlight emits
        # for Pagefind; fall back to the first <main> if the attribute is
        # missing (older Starlight, or a future redesign). We use CSS
        # selectors throughout so the BeautifulSoup stubs narrow the return
        # types to `Tag | None`, which avoids the `Tag | NavigableString | int`
        # union mypy complains about.
        body = ""
        main = soup.select_one("main[data-pagefind-body]") or soup.select_one("main")
        if main is not None:
            main_div = main.select_one("div.sl-markdown-content")
            body = main_div.get_text("\n", strip=True) if main_div is not None else main.get_text("\n", strip=True)

        return {"path": path, "url": url, "title": title, "body": body}

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Canonicalize a path to `/foo/bar/` form for by-path lookup."""
        from urllib.parse import unquote

        path = unquote(path.strip())
        # Strip a leading base URL if present.
        if path.startswith(DEN_BASE_URL):
            path = path[len(DEN_BASE_URL) :]
        # Drop query/fragment.
        for sep in ("?", "#"):
            if sep in path:
                path = path.split(sep, 1)[0]
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path = path + "/"
        # Strip duplicate slashes (defensive).
        while "//" in path:
            path = path.replace("//", "/")
        return path


den_cache = DenCache()
