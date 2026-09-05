"""NixOS Wiki source (wiki.nixos.org)."""

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

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


# Rendered-page chrome that carries no article content: the language bar,
# maintenance notices (cleanup/stub boxes), citation markers and the
# references list, and edit-section links.
_WIKI_CHROME_SELECTORS = (
    ".mw-pt-languages",
    ".noprint",
    ".box",
    ".mw-references-wrap",
    "sup.reference",
    ".mw-editsection",
)
_WIKI_NOT_FOUND_CODES = {"missingtitle", "invalidtitle", "nosuchsection"}
_WIKI_EXTRACT_LIMIT = 1500


# The wiki's Translate markup is not rendered, so `<translate>` tags and
# `<!--T:123-->` unit markers survive into the page text as literal strings.
_WIKI_TRANSLATE_MARKUP = re.compile(r"</?translate>|<!--T:\d+-->")
_WIKI_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)\]])")


def _wiki_html_to_text(html: str) -> str:
    """Flatten the rendered intro section to plain text, dropping page chrome."""
    soup = BeautifulSoup(html, "html.parser")
    for selector in _WIKI_CHROME_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
    text = _WIKI_TRANSLATE_MARKUP.sub(" ", soup.get_text(" "))
    text = " ".join(text.split())
    return _WIKI_SPACE_BEFORE_PUNCT.sub(r"\1", text)


def _info_wiki(title: str) -> str:
    """Get the intro section of a wiki page as plain text.

    wiki.nixos.org does not install MediaWiki's TextExtracts extension, so the
    `prop=extracts` query this used to make was silently ignored (it came back
    as an API *warning*, not an error) and every page degraded to title + URL.
    `action=parse` on section 0 is available on every MediaWiki, so render the
    intro and strip it to text instead.
    """
    try:
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "section": "0",
            "redirects": "1",
            "disabletoc": "1",
            "disablelimitreport": "1",
            "disableeditsection": "1",
            "format": "json",
        }
        resp = requests.get(WIKI_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            code = str(data["error"].get("code", ""))
            if code in _WIKI_NOT_FOUND_CODES:
                return error(f"Wiki page '{title}' not found", "NOT_FOUND")
            return error(f"Wiki API error: {data['error'].get('info', code)}", "API_ERROR")

        parsed = data.get("parse", {})
        page_title = parsed.get("title", title)
        extract = _wiki_html_to_text(parsed.get("text", {}).get("*", ""))

        results = [
            f"Wiki: {page_title}",
            f"URL: https://wiki.nixos.org/wiki/{quote(page_title.replace(' ', '_'), safe='')}",
            "",
        ]

        if extract:
            if len(extract) > _WIKI_EXTRACT_LIMIT:
                extract = extract[:_WIKI_EXTRACT_LIMIT] + "..."
            results.append(extract)

        return "\n".join(results)
    except requests.Timeout:
        return error("Wiki API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"Wiki API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))
