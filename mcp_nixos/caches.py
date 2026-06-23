"""Cache classes for MCP-NixOS server."""

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from bs4 import BeautifulSoup

from .config import (
    FALLBACK_CHANNELS,
    HOME_MANAGER_OPTIONS_DIR,
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


class HomeManagerCache:
    """Cache for Home Manager options fetched from the mdBook-rendered site.

    As of mid-2026 the home-manager docs are published as an mdBook site. The
    legacy single-page `options.xhtml` is now a 1.4 KB JS redirect stub; the
    real options live on ~600 per-page HTML files under `options/home-manager/`,
    organised roughly as:

      options/home-manager/                 →  ~30 top-level pages (accounts.html,
                                               dconf.html, fonts.html, gtk.html, …)
      options/home-manager/programs/         →  ~400 program pages (git.html,
                                               helix.html, …)
      options/home-manager/services/         →  ~170 service pages

    Each page is a self-contained mdBook chapter that lists the options it
    defines as `<h2 id="opt-...">` headers followed by `<p>` tags for the
    description, type, default, and example. We discover page URLs from three
    directory listings, then fetch each page in parallel (bounded thread pool)
    and parse out the options into a single in-memory list.
    """

    # Subdirectories under HOME_MANAGER_OPTIONS_DIR that contain option pages.
    _PAGE_LISTINGS = ("", "programs/", "services/")

    # Cap concurrent fetches so we don't hammer GitHub Pages.
    _MAX_WORKERS = 10

    def __init__(self) -> None:
        self.options: list[dict[str, Any]] | None = None
        self._by_name: dict[str, dict[str, Any]] | None = None
        self._init_lock = threading.Lock()

    def get_options(self) -> list[dict[str, Any]]:
        """Fetch and cache all Home Manager options.

        Concurrency-safe via double-checked locking: N concurrent first
        callers all see the cold cache, but only one performs the walk;
        the rest wait and consume the cached list.
        """
        if self.options is not None:
            return self.options

        with self._init_lock:
            if self.options is not None:
                return self.options

            page_urls = self._discover_page_urls()
            if not page_urls:
                raise APIError("No Home Manager option pages discovered")

            all_options: list[dict[str, Any]] = []
            try:
                with ThreadPoolExecutor(max_workers=self._MAX_WORKERS) as pool:
                    futures = {pool.submit(self._fetch_page_options, url): url for url in page_urls}
                    for future in as_completed(futures):
                        url = futures[future]
                        try:
                            page_options = future.result()
                        except requests.RequestException as exc:
                            raise APIError(f"Failed to fetch {url}: {exc}") from exc
                        except Exception as exc:
                            raise APIError(f"Failed to parse {url}: {exc}") from exc
                        all_options.extend(page_options)
            except requests.Timeout as exc:
                raise APIError("Timeout fetching Home Manager options") from exc
            except requests.RequestException as exc:
                raise APIError(f"Failed to fetch Home Manager options: {exc}") from exc

            # Sort by name for deterministic downstream output (search, info,
            # browse) — `as_completed()` yields in completion order.
            all_options.sort(key=lambda opt: opt.get("name", ""))
            self.options = all_options
            self._by_name = {opt["name"]: opt for opt in all_options if opt.get("name")}
            return self.options

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Look up a single option by its exact name. Lazy-loads the cache."""
        if self._by_name is None:
            self.get_options()
        return self._by_name.get(name) if self._by_name else None

    def _discover_page_urls(self) -> list[str]:
        """Enumerate option-page URLs by reading three directory listings.

        Returns unique URLs in the order the listings declared them. If any
        individual listing fetch fails (network error or non-2xx), the
        failure is collected and raised as a single `APIError` so a partial
        index isn't silently cached — a missing listings means the user is
        about to see "0 options" for whatever section didn't load.
        """
        from urllib.parse import urljoin, urlparse

        allowed = urlparse(HOME_MANAGER_OPTIONS_DIR)
        urls: list[str] = []
        failed: list[str] = []
        for sub in self._PAGE_LISTINGS:
            listing_url = f"{HOME_MANAGER_OPTIONS_DIR}/{sub}" if sub else f"{HOME_MANAGER_OPTIONS_DIR}/"
            try:
                resp = requests.get(listing_url, timeout=15)
                if resp.status_code != 200:
                    failed.append(f"{listing_url} (HTTP {resp.status_code})")
                    continue
            except requests.RequestException as exc:
                failed.append(f"{listing_url} ({exc})")
                continue

            soup = BeautifulSoup(resp.content, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                # Skip the print.html / parent-directory links emitted by
                # GitHub Pages' directory listing.
                if not href.endswith(".html") or href.startswith("..") or href.startswith("?"):
                    continue
                if sub == "":
                    # Top-level: only accept "<name>.html" with no slashes
                    # (e.g. "accounts.html", "fonts.html"). Subdirectory
                    # entries ("programs/", "services/") and any nested
                    # links are ignored.
                    if "/" in href:
                        continue
                # SSRF guard: only follow links that resolve to the same
                # scheme+host+path-prefix as HOME_MANAGER_OPTIONS_DIR. A
                # compromised listing page can't pivot us into fetching
                # arbitrary hosts.
                candidate = urljoin(listing_url, href)
                parsed = urlparse(candidate)
                if parsed.scheme != "https" or parsed.netloc != allowed.netloc:
                    continue
                if not parsed.path.startswith(allowed.path):
                    continue
                urls.append(candidate)

        if failed:
            raise APIError("Failed to fetch Home Manager option listings: " + "; ".join(failed))

        # De-dup while preserving order.
        seen: set[str] = set()
        unique: list[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    @staticmethod
    def _fetch_page_options(url: str) -> list[dict[str, Any]]:
        """Fetch a single page and extract the options declared on it.

        Each option in the mdBook-rendered page looks like:

            <h2 id="opt-NAME">NAME</h2>
            <p>description (possibly multi-paragraph)</p>
            <p><em>Type:</em> value</p>
            <p><em>Default:</em></p>
            <pre><code>value</code></pre>
            <p><em>Example:</em></p>
            <pre><code>value</code></pre>
            <p><em>Declared by:</em></p>
            <ul>…</ul>

        We walk via `find_next_sibling()` so we only see the option's own
        block elements (not nested `<em>`/`<a>`/`<code>` descendants).
        """
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        options: list[dict[str, Any]] = []
        for h2 in soup.find_all("h2", id=True):
            anchor_id = h2.get("id", "")
            if not anchor_id.startswith("opt-"):
                continue
            name = anchor_id[4:]  # strip "opt-" prefix
            if not name or "." not in name:
                continue

            option: dict[str, Any] = {
                "name": name,
                "type": "",
                "description": "",
                "default": "",
                "example": "",
            }

            # Walk the siblings of the <h2> until the next <h2> (next option)
            # or the end of the document. Sibling traversal keeps us at the
            # block-element level; nested <em>/<a>/<code>/<pre> are handled
            # by `get_text()`.
            last_label: str | None = None
            description_paragraphs: list[str] = []
            for sibling in h2.find_next_siblings():
                if sibling.name == "h2":
                    break
                if not hasattr(sibling, "name") or sibling.name is None:
                    continue  # text node

                # Extract the leading label from the first <em> child if any.
                em = sibling.find("em")
                if em is not None:
                    label = em.get_text(strip=True).rstrip(":").lower()
                else:
                    label = None

                if label in ("type", "default", "example"):
                    last_label = label
                    if label == "type":
                        # The full <p> text is "Type: value" (or "Type
                        # value" if the site drops the colon). Strip the label
                        # text from the start and any leading colon so both
                        # renderings produce the same value.
                        em_text = em.get_text(strip=True)  # original case
                        full = sibling.get_text(" ", strip=True)
                        after = full
                        for prefix in (f"{em_text}:", em_text, f"{em_text}:"):
                            if after.startswith(prefix):
                                after = after[len(prefix) :]
                                break
                        option["type"] = after.strip()
                    # default / example values are emitted in a *following*
                    # <pre><code>, so we don't set them here; we set them
                    # in the loop below when we see a <pre> right after a
                    # "Default:" or "Example:" label.
                elif sibling.name == "pre" and last_label in ("default", "example"):
                    value = sibling.get_text(" ", strip=True)
                    if last_label == "default":
                        option["default"] = value
                    else:
                        option["example"] = value
                    last_label = None  # consumed
                elif sibling.name == "p":
                    # Could be a continuation of the description, a "Declared
                    # by:" block, or one of the multi-paragraph descriptions.
                    text = sibling.get_text(" ", strip=True)
                    if not text:
                        continue
                    lower = text.lower()
                    if lower.startswith("declared by"):
                        last_label = None
                        continue
                    if lower.startswith(("type:", "default:", "example:")):
                        # Shouldn't reach here in well-formed pages but be
                        # defensive.
                        last_label = None
                        continue
                    if not option["description"]:
                        description_paragraphs.append(text)
                    else:
                        description_paragraphs.append(text)

            option["description"] = " ".join(description_paragraphs)
            options.append(option)
        return options


home_manager_cache = HomeManagerCache()
