"""Nixvim options source."""

from typing import Any

from ..caches import nixvim_cache
from ..config import APIError
from ..utils import error, strip_html


def _search_nixvim(query: str, limit: int) -> str:
    """Search Nixvim options from NuschtOS meta JSON."""
    try:
        options = nixvim_cache.get_options()
        query_lower = query.lower()

        matches = []
        for opt in options:
            name = opt.get("name", "")
            desc = strip_html(opt.get("description", ""))
            if query_lower in name.lower() or query_lower in desc.lower():
                matches.append(
                    {
                        "name": name,
                        "type": opt.get("type", ""),
                        "description": desc,
                    }
                )
                if len(matches) >= limit:
                    break

        if not matches:
            return f"No Nixvim options found matching '{query}'"

        results = [f"Found {len(matches)} Nixvim options matching '{query}':\n"]
        for opt in matches:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                desc = opt["description"][:200] + "..." if len(opt["description"]) > 200 else opt["description"]
                results.append(f"  {desc}")
            results.append("")
        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _info_nixvim(name: str) -> str:
    """Get detailed info for a Nixvim option."""
    try:
        options = nixvim_cache.get_options()

        # Exact match first
        for opt in options:
            if opt.get("name") == name:
                return _format_nixvim_option(opt)

        # Try case-insensitive match
        name_lower = name.lower()
        for opt in options:
            if opt.get("name", "").lower() == name_lower:
                return _format_nixvim_option(opt)

        # Suggest similar options
        similar = [o["name"] for o in options if name_lower in o.get("name", "").lower()][:5]
        if similar:
            return error(f"Option '{name}' not found. Similar: {', '.join(similar)}", "NOT_FOUND")
        return error(f"Nixvim option '{name}' not found", "NOT_FOUND")
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _format_nixvim_option(opt: dict[str, Any]) -> str:
    """Format a Nixvim option for detailed display."""
    lines = [f"Nixvim Option: {opt.get('name', '')}"]

    if opt.get("type"):
        lines.append(f"Type: {opt['type']}")

    desc = strip_html(opt.get("description", ""))
    if desc:
        lines.append(f"Description: {desc}")

    default = strip_html(opt.get("default", ""))
    if default:
        lines.append(f"Default: {default}")

    example = strip_html(opt.get("example", ""))
    if example:
        # Truncate long examples
        if len(example) > 500:
            example = example[:500] + "..."
        lines.append(f"Example: {example}")

    declarations = opt.get("declarations", [])
    if declarations:
        lines.append(f"Declared in: {declarations[0]}")

    return "\n".join(lines)


def _stats_nixvim() -> str:
    """Get Nixvim option statistics."""
    try:
        options = nixvim_cache.get_options()

        # Count top-level categories
        categories: dict[str, int] = {}
        for opt in options:
            name = opt.get("name", "")
            if "." in name:
                cat = name.split(".")[0]
            else:
                cat = name
            categories[cat] = categories.get(cat, 0) + 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
        result = [
            "Nixvim Statistics:",
            f"* Total options: {len(options):,}",
            f"* Categories: {len(categories)}",
            "* Top categories:",
        ]
        for cat, count in top_cats:
            result.append(f"  - {cat}: {count:,}")
        return "\n".join(result)
    except APIError:
        raise
    except Exception as e:
        return error(str(e))


def _browse_nixvim_options(prefix: str) -> str:
    """Browse Nixvim options by prefix, or list categories if no prefix."""
    try:
        options = nixvim_cache.get_options()

        if not prefix:
            # List top-level categories with counts
            categories: dict[str, int] = {}
            for opt in options:
                name = opt.get("name", "")
                if "." in name:
                    cat = name.split(".")[0]
                else:
                    cat = name
                categories[cat] = categories.get(cat, 0) + 1

            sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            results = [f"Nixvim option categories ({len(categories)} total):\n"]
            for cat, count in sorted_cats:
                results.append(f"* {cat} ({count} options)")
            return "\n".join(results)

        # List options under prefix
        prefix_dot = prefix if prefix.endswith(".") else prefix + "."
        matches = []
        for opt in options:
            name = opt.get("name", "")
            if name.startswith(prefix_dot) or name == prefix:
                matches.append(
                    {
                        "name": name,
                        "type": opt.get("type", ""),
                        "description": strip_html(opt.get("description", "")),
                    }
                )

        if not matches:
            return f"No Nixvim options found with prefix '{prefix}'"

        results = [f"Nixvim options with prefix '{prefix}' ({len(matches)} found):\n"]
        for opt in sorted(matches, key=lambda x: x["name"])[:100]:
            results.append(f"* {opt['name']}")
            if opt["type"]:
                results.append(f"  Type: {opt['type']}")
            if opt["description"]:
                desc = opt["description"][:150] + "..." if len(opt["description"]) > 150 else opt["description"]
                results.append(f"  {desc}")
            results.append("")

        if len(matches) > 100:
            results.append(f"... and {len(matches) - 100} more options")
        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as e:
        return error(str(e))
