"""NixOS Wiki source (wiki.nixos.org)."""

from urllib.parse import quote

import requests

from ..config import WIKI_API
from ..utils import error, strip_html


def _search_wiki(query: str, limit: int) -> str:
    """Search NixOS Wiki via MediaWiki API."""
    try:
        # Normalize query: replace hyphens with spaces for better MediaWiki search matching
        # e.g., "home-manager" -> "home manager" finds "Home Manager" page
        normalized_query = query.replace("-", " ")
        params: dict[str, str | int] = {
            "action": "query",
            "list": "search",
            "srsearch": normalized_query,
            "format": "json",
            "utf8": "1",
            "srlimit": limit,
        }
        resp = requests.get(WIKI_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results_list = data.get("query", {}).get("search", [])
        if not results_list:
            return f"No wiki articles found matching '{query}'"

        results = [f"Found {len(results_list)} wiki articles matching '{query}':\n"]
        for item in results_list:
            title = item.get("title", "")
            snippet = strip_html(item.get("snippet", ""))
            wordcount = item.get("wordcount", 0)

            results.append(f"* {title}")
            results.append(f"  https://wiki.nixos.org/wiki/{quote(title.replace(' ', '_'), safe='')}")
            if snippet:
                # Truncate long snippets
                snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                results.append(f"  {snippet}")
            if wordcount:
                results.append(f"  ({wordcount:,} words)")
            results.append("")

        return "\n".join(results).strip()
    except requests.Timeout:
        return error("Wiki API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Wiki API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_wiki(title: str) -> str:
    """Get wiki page content/extract via MediaWiki API."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "exintro": "1",  # Just the intro
            "explaintext": "1",  # Plain text, no HTML
            "format": "json",
        }
        resp = requests.get(WIKI_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return error(f"Wiki page '{title}' not found", "NOT_FOUND")

        # Get first page (there's only one)
        page = next(iter(pages.values()))
        # Check if "missing" key exists - MediaWiki uses empty string for missing pages
        if "missing" in page:
            return error(f"Wiki page '{title}' not found", "NOT_FOUND")

        page_title = page.get("title", title)
        extract = page.get("extract", "")

        results = [
            f"Wiki: {page_title}",
            f"URL: https://wiki.nixos.org/wiki/{quote(page_title.replace(' ', '_'), safe='')}",
            "",
        ]

        if extract:
            # Limit extract length
            if len(extract) > 1500:
                extract = extract[:1500] + "..."
            results.append(extract)

        return "\n".join(results)
    except requests.Timeout:
        return error("Wiki API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Wiki API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))
