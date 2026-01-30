"""Home Manager options source."""

from ..config import HOME_MANAGER_URL
from ..utils import error, parse_html_options


def _search_home_manager(query: str, limit: int) -> str:
    """Search Home Manager options by parsing HTML documentation."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, query, "", limit)
        if not options:
            return f"No Home Manager options found matching '{query}'"
        results = [f"Found {len(options)} Home Manager options matching '{query}':\n"]
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


def _info_home_manager(name: str) -> str:
    """Get detailed info for a Home Manager option."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, name, "", 100)
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


def _stats_home_manager() -> str:
    """Get Home Manager option counts and top categories."""
    try:
        options = parse_html_options(HOME_MANAGER_URL, limit=5000)
        if not options:
            return error("Failed to fetch Home Manager statistics")

        categories: dict[str, int] = {}
        for opt in options:
            cat = opt["name"].split(".")[0]
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = ["Home Manager Statistics:", f"* Total options: {len(options):,}", f"* Categories: {len(categories)}"]
        result.append("* Top categories:")
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except Exception as e:
        return error(str(e))
