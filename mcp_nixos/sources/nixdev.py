"""nix.dev documentation source."""

import requests

from ..caches import nixdev_cache
from ..config import NIXDEV_BASE_URL, APIError
from ..utils import error

# Cap markdown body at 200KB (~50k tokens) to avoid swamping the LLM context.
# nix.dev pages are typically 5-60KB so this is plenty for legitimate docs.
_NIXDEV_MAX_MD_BYTES = 200 * 1024


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


def _normalize_nixdev_docname(query: str) -> str:
    """Normalize a nix.dev query into a docname (e.g. 'tutorials/nix-language').

    Accepts either a bare docname, a nix.dev URL as printed by `_search_nixdev`
    (e.g. 'https://nix.dev/tutorials/nix-language'), or a rendered '.html' URL
    pasted from a browser. Strips the base URL prefix, a trailing '.html', a
    leading slash, any URL fragment/query string, and percent-decodes the
    result so the traversal guard in `_info_nixdev` sees the real path
    segments instead of `%2e%2e` escapes.
    """
    from urllib.parse import unquote

    name = unquote(query.strip())
    if name.startswith(NIXDEV_BASE_URL):
        name = name[len(NIXDEV_BASE_URL) :]
    # Drop fragment and query string if the caller passed a full URL
    for sep in ("#", "?"):
        if sep in name:
            name = name.split(sep, 1)[0]
    name = name.lstrip("/")
    if name.endswith(".html"):
        name = name[: -len(".html")]
    return name


def _extract_nixdev_title(body: str, fallback: str) -> str:
    """Pull the first markdown H1 from a nix.dev page body."""
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def _info_nixdev(query: str) -> str:
    """Fetch a nix.dev page as markdown.

    The `query` may be a bare docname (e.g. 'tutorials/nix-language'), the
    extensionless URL printed by `_search_nixdev` (e.g.
    'https://nix.dev/tutorials/nix-language'), or a rendered '.html' URL
    pasted from a browser. All three are normalized to the docname before
    fetching '{NIXDEV_BASE_URL}/_sources/{docname}.md'.
    """
    if not query or not query.strip():
        return error("Query required for nix-dev info (docname or URL)")

    docname = _normalize_nixdev_docname(query)
    if not docname:
        return error("Empty docname after normalization")

    # Guard against path traversal — the docname is interpolated into a URL path.
    if ".." in docname.split("/"):
        return error("Invalid docname: path traversal not allowed")

    url = f"{NIXDEV_BASE_URL}/_sources/{docname}.md"
    canonical_url = f"{NIXDEV_BASE_URL}/{docname}.html"

    # Stream the download and stop once we've read past the cap so a
    # multi-MB page doesn't materialize in memory before being truncated.
    # Read one extra byte beyond the cap to detect truncation unambiguously.
    try:
        resp = requests.get(url, timeout=15, stream=True)
    except requests.Timeout:
        return error("nix.dev request timed out", "TIMEOUT")
    except requests.RequestException as exc:
        return error(f"nix.dev request failed: {exc}", "API_ERROR")

    try:
        if resp.status_code == 404:
            return error(f"nix.dev page not found: {docname}", "NOT_FOUND")
        try:
            resp.raise_for_status()
        except requests.RequestException as exc:
            return error(f"nix.dev request failed: {exc}", "API_ERROR")

        cap = _NIXDEV_MAX_MD_BYTES
        buf = bytearray()
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > cap:
                    break
        except requests.RequestException as exc:
            return error(f"nix.dev request failed: {exc}", "API_ERROR")
    finally:
        resp.close()

    truncated = len(buf) > cap
    # Decode defensively — nix.dev markdown is ASCII/UTF-8, but truncating
    # on a byte boundary could split a multi-byte codepoint.
    body = bytes(buf[:cap] if truncated else buf).decode("utf-8", errors="ignore")

    title = _extract_nixdev_title(body, fallback=docname)

    lines = [
        f"Title: {title}",
        f"Source: {canonical_url}",
        f"Docname: {docname}",
        "",
        body.rstrip(),
    ]
    if truncated:
        lines.append("")
        lines.append("[truncated]")
    return "\n".join(lines)
