"""Den framework documentation source (https://den.denful.dev).

Search, info, stats, and browse the Starlight-rendered Astro site that
publishes the Den framework docs. Discovery and per-page parsing live in
`DenCache`; this module is a thin formatter on top of it.
"""

from typing import Any

from ..caches import den_cache
from ..config import DEN_BASE_URL, APIError
from ..utils import error

# Cap the body we return from `_info_den` at ~200KB so a large page
# doesn't blow the LLM context. The full Den docs corpus is small
# (≈50 pages × a few KB each); 200KB is plenty for legitimate docs.
_DEN_MAX_BODY_CHARS = 200_000

# Browse output cap — matches `home-manager` / `darwin` browse behaviour.
_DEN_BROWSE_LIMIT = 100


def _score_page(page: dict[str, Any], query_lower: str) -> int:
    """Score a Den page against a lowercased query.

    Scoring is intentionally simple and matches the nix-dev / noogle style:
    title hits are weighted higher than body hits, prefix matches on
    titles are weighted higher still. Multi-term queries are split on
    whitespace and each term contributes independently.
    """
    title = page.get("title", "").lower()
    body = page.get("body", "").lower()

    if not title and not body:
        return 0

    terms = [t for t in query_lower.split() if t]
    if not terms:
        return 0

    score = 0
    for term in terms:
        score += title.count(term) * 5
        score += body.count(term)
        if title.startswith(term):
            score += 3
    return score


def _search_den(query: str, limit: int) -> str:
    """Search Den docs by case-insensitive substring on title + body."""
    try:
        pages = den_cache.get_pages()
    except APIError as exc:
        return error(str(exc), "API_ERROR")
    except Exception as e:
        return error(str(e))

    query_lower = query.lower().strip()
    if not query_lower:
        return error("Query required for den search")

    scored: list[tuple[int, dict[str, Any]]] = []
    for page in pages:
        s = _score_page(page, query_lower)
        if s > 0:
            scored.append((s, page))

    if not scored:
        return f"No Den docs found matching '{query}'"

    scored.sort(key=lambda x: (-x[0], x[1].get("path", "")))
    top = scored[:limit]

    results = [f"Found {len(top)} Den docs matching '{query}':\n"]
    for _score, page in top:
        path = page.get("path", "")
        title = page.get("title", "")
        results.append(f"* {title}")
        results.append(f"  {DEN_BASE_URL}{path}")
        results.append("")
    return "\n".join(results).strip()


def _info_den(query: str) -> str:
    """Return a single Den page as plain text (title + body + url)."""
    if not query or not query.strip():
        return error("Query required for den info (path, slug, or URL)")

    try:
        page = den_cache.get_by_path(query)
    except APIError as exc:
        return error(str(exc), "API_ERROR")
    except Exception as e:
        return error(str(e))

    if page is None:
        # No exact path match — try a basename fallback so the caller can
        # pass a slug like "aspects" instead of "/explanation/aspects/".
        slug = query.strip().strip("/").rsplit("/", 1)[-1]
        try:
            pages = den_cache.get_pages()
        except APIError as exc:
            return error(str(exc), "API_ERROR")
        except Exception as e:
            return error(str(e))
        matches = [p for p in pages if p.get("path", "").strip("/").rsplit("/", 1)[-1] == slug]
        if matches:
            page = matches[0]

    if page is None:
        return error(f"Den page not found: {query}", "NOT_FOUND")

    title = page.get("title", "")
    path = page.get("path", "")
    url = page.get("url", f"{DEN_BASE_URL}{path}")
    body = page.get("body", "").strip()

    truncated = len(body) > _DEN_MAX_BODY_CHARS
    if truncated:
        body = body[:_DEN_MAX_BODY_CHARS]

    lines = [
        f"Title: {title}",
        f"Source: {url}",
        f"Path: {path}",
        "",
        body,
    ]
    if truncated:
        lines.append("")
        lines.append("[truncated]")
    return "\n".join(lines)


def _stats_den() -> str:
    """Total Den pages + per-section page count."""
    try:
        pages = den_cache.get_pages()
    except APIError as exc:
        return error(str(exc), "API_ERROR")
    except Exception as e:
        return error(str(e))

    if not pages:
        return error("Failed to fetch Den documentation statistics")

    section_counts: dict[str, int] = {}
    for page in pages:
        path = page.get("path", "")
        # First non-empty path segment after the leading slash is the
        # section name (e.g., "/explanation/aspects/" -> "explanation").
        parts = [p for p in path.strip("/").split("/") if p]
        section = parts[0] if parts else "(root)"
        section_counts[section] = section_counts.get(section, 0) + 1

    sorted_sections = sorted(section_counts.items(), key=lambda x: (-x[1], x[0]))
    lines = [
        "Den Documentation Statistics:",
        f"* Total pages: {len(pages):,}",
        f"* Sections: {len(section_counts)}",
        "* Pages per section:",
    ]
    for section, count in sorted_sections:
        lines.append(f"  - {section}: {count}")
    return "\n".join(lines)


def _browse_den(prefix: str) -> str:
    """Browse Den pages by path prefix; with no prefix, list top-level sections."""
    try:
        pages = den_cache.get_pages()
    except APIError as exc:
        return error(str(exc), "API_ERROR")
    except Exception as e:
        return error(str(e))

    if not prefix:
        # Top-level section summary (mirrors `_browse_options` for hm/darwin).
        section_counts: dict[str, int] = {}
        for page in pages:
            path = page.get("path", "")
            parts = [p for p in path.strip("/").split("/") if p]
            section = parts[0] if parts else "(root)"
            section_counts[section] = section_counts.get(section, 0) + 1
        if not section_counts:
            return "No Den pages indexed"

        sorted_sections = sorted(section_counts.items(), key=lambda x: (-x[1], x[0]))
        results = [f"Den doc sections ({len(section_counts)} total):\n"]
        for section, count in sorted_sections:
            results.append(f"* {section} ({count} pages)")
        return "\n".join(results)

    # Normalize the prefix to a `/section/.../` shape.
    norm = prefix.strip().strip("/")
    if norm:
        norm = "/" + norm
    if not norm.endswith("/"):
        norm = norm + "/"

    matches = [p for p in pages if p.get("path", "").startswith(norm)]
    if not matches:
        return f"No Den pages found with prefix '{prefix}'"

    matches.sort(key=lambda p: p.get("path", ""))
    matches = matches[:_DEN_BROWSE_LIMIT]

    results = [f"Den pages with prefix '{prefix}' ({len(matches)} found):\n"]
    for page in matches:
        path = page.get("path", "")
        title = page.get("title", "")
        results.append(f"* {path} — {title}")
    if len(matches) == _DEN_BROWSE_LIMIT:
        # We truncated; check if there are more.
        total = sum(1 for p in pages if p.get("path", "").startswith(norm))
        if total > _DEN_BROWSE_LIMIT:
            results.append("")
            results.append(f"... and {total - _DEN_BROWSE_LIMIT} more pages")
    return "\n".join(results)
