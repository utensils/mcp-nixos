"""Home Manager options source.

The Home Manager docs migrated to an mdBook site in mid-2026. Options now
live on ~600 per-page HTML files (one page per program / service / top-level
category) instead of a single giant `options.xhtml`. The HomeManagerCache
discovers those pages and parses out the options; this module is a thin
formatter on top of it.
"""

from ..caches import home_manager_cache
from ..config import APIError
from ..utils import error


def _search_home_manager(query: str, limit: int) -> str:
    """Search Home Manager options by name or description substring."""
    try:
        options = home_manager_cache.get_options()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))

    query_lower = query.lower()
    matches = []
    for opt in options:
        name = opt.get("name", "")
        desc = opt.get("description", "")
        if query_lower in name.lower() or query_lower in desc.lower():
            matches.append(opt)
            if len(matches) >= limit:
                break

    if not matches:
        return f"No Home Manager options found matching '{query}'"

    results = [f"Found {len(matches)} Home Manager options matching '{query}':\n"]
    for opt in matches:
        results.append(f"* {opt['name']}")
        if opt.get("type"):
            results.append(f"  Type: {opt['type']}")
        if opt.get("description"):
            results.append(f"  {opt['description']}")
        results.append("")
    return "\n".join(results).strip()


def _info_home_manager(name: str) -> str:
    """Get detailed info for a Home Manager option."""
    try:
        opt = home_manager_cache.get_by_name(name)
    except APIError:
        raise
    except Exception as e:
        return error(str(e))

    if opt is not None:
        info = [f"Option: {name}"]
        if opt.get("type"):
            info.append(f"Type: {opt['type']}")
        if opt.get("description"):
            info.append(f"Description: {opt['description']}")
        if opt.get("default"):
            info.append(f"Default: {opt['default']}")
        if opt.get("example"):
            info.append(f"Example: {opt['example']}")
        return "\n".join(info)

    # Not found — offer up to 5 substring suggestions so the caller can retry.
    try:
        options = home_manager_cache.get_options()
    except APIError:
        options = []
    suggestions = [o["name"] for o in options if name in o.get("name", "")][:5]
    if suggestions:
        return error(f"Option '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")
    return error(f"Option '{name}' not found", "NOT_FOUND")


def _stats_home_manager() -> str:
    """Get Home Manager option counts and top categories."""
    try:
        options = home_manager_cache.get_options()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))

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
