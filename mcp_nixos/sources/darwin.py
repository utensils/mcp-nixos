"""nix-darwin options source."""

from ..config import DARWIN_URL
from ..utils import error, parse_html_options


def _search_darwin(query: str, limit: int) -> str:
    """Search nix-darwin options by parsing HTML documentation."""
    try:
        options = parse_html_options(DARWIN_URL, query, "", limit)
        if not options:
            return f"No nix-darwin options found matching '{query}'"
        results = [f"Found {len(options)} nix-darwin options matching '{query}':\n"]
        for opt in options:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                results.append(f"  {opt['description']}")
            results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _info_darwin(name: str) -> str:
    """Get detailed info for a nix-darwin option."""
    try:
        options = parse_html_options(DARWIN_URL, name, "", 100)
        for opt in options:
            if opt["name"] == name:
                info = [f"Option: {name}"]
                if opt["type"]:
                    info.append(f"Type: {opt['type']}")
                if opt["description"]:
                    info.append(f"Description: {opt['description']}")
                return "\n".join(info)

        if options:
            suggestions = [opt["name"] for opt in options[:5] if name in opt["name"]]
            if suggestions:
                return error(f"Option '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")
        return error(f"Option '{name}' not found", "NOT_FOUND")
    except Exception as e:
        return error(str(e))


def _stats_darwin() -> str:
    """Get nix-darwin option counts and top categories."""
    try:
        options = parse_html_options(DARWIN_URL, limit=3000)
        if not options:
            return error("Failed to fetch nix-darwin statistics")

        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = ["nix-darwin Statistics:", f"* Total options: {len(options):,}", f"* Categories: {len(categories)}"]
        result.append("* Top categories:")
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except Exception as e:
        return error(str(e))
