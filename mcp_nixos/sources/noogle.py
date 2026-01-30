"""Noogle source (noogle.dev - Nix function API search)."""

from typing import Any

from ..caches import noogle_cache
from ..config import APIError
from ..utils import error, strip_html


def _get_noogle_function_path(doc: dict[str, Any]) -> str:
    """Extract the function path from a Noogle document."""
    meta = doc.get("meta", {})
    # Use path if available, otherwise construct from title
    path = meta.get("path", [])
    if path:
        return ".".join(str(p) for p in path)
    title = meta.get("title", "")
    return str(title) if title else ""


def _get_noogle_type_signature(doc: dict[str, Any]) -> str:
    """Extract the type signature from a Noogle document."""
    content = doc.get("content")
    if not content or not isinstance(content, dict):
        return ""

    # Check for signature in content
    signature = content.get("signature", "")
    if signature:
        return str(signature)

    # Check for type annotation
    type_info = content.get("type", "")
    if type_info:
        return str(type_info)

    return ""


def _get_noogle_aliases(doc: dict[str, Any]) -> list[str]:
    """Extract aliases from a Noogle document."""
    meta = doc.get("meta")
    if not meta or not isinstance(meta, dict):
        return []
    aliases = meta.get("aliases")
    if aliases and isinstance(aliases, list):
        return [".".join(str(p) for p in a) if isinstance(a, list) else str(a) for a in aliases]
    return []


def _get_noogle_description(doc: dict[str, Any]) -> str:
    """Extract description from a Noogle document."""
    content = doc.get("content")
    if not content or not isinstance(content, dict):
        return ""

    # Try different content fields
    desc = content.get("content", "")
    if desc:
        return strip_html(str(desc))

    # Try lambda content
    lambda_content = content.get("lambda")
    if lambda_content and isinstance(lambda_content, dict):
        lambda_desc = lambda_content.get("content", "")
        if lambda_desc:
            return strip_html(str(lambda_desc))

    return ""


def _search_noogle(query: str, limit: int) -> str:
    """Search Noogle functions by name, path, or documentation content."""
    try:
        data, _ = noogle_cache.get_data()
        query_lower = query.lower()

        matches = []
        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            desc = _get_noogle_description(doc)
            desc_lower = desc.lower()
            aliases = _get_noogle_aliases(doc)

            # Score matches
            score = 0
            # Exact path match
            if path_lower == query_lower:
                score = 100
            # Path contains query
            elif query_lower in path_lower:
                # Boost if query matches end of path (function name)
                if path_lower.endswith(query_lower) or path_lower.endswith("." + query_lower):
                    score = 50
                else:
                    score = 30
            # Alias match
            elif any(query_lower in alias.lower() for alias in aliases):
                score = 40
            # Description match
            elif query_lower in desc_lower:
                score = 10

            if score > 0:
                matches.append((score, path, doc))

        if not matches:
            return f"No Noogle functions found matching '{query}'"

        # Sort by score (descending), then by path
        matches.sort(key=lambda x: (-x[0], x[1]))
        matches = matches[:limit]

        results = [f"Found {len(matches)} Noogle functions matching '{query}':\n"]
        for _, path, doc in matches:
            results.append(f"* {path}")
            sig = _get_noogle_type_signature(doc)
            if sig:
                # Truncate long signatures
                sig = sig[:100] + "..." if len(sig) > 100 else sig
                results.append(f"  Type: {sig}")
            desc = _get_noogle_description(doc)
            if desc:
                desc = desc[:200] + "..." if len(desc) > 200 else desc
                results.append(f"  {desc}")
            aliases = _get_noogle_aliases(doc)
            if aliases:
                results.append(f"  Aliases: {', '.join(aliases[:3])}")
            results.append("")

        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_noogle(name: str) -> str:
    """Get detailed info for a specific Noogle function."""
    try:
        data, _ = noogle_cache.get_data()
        name_lower = name.lower()

        # Find exact match first, then partial match
        exact_match = None
        partial_matches = []

        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            aliases = _get_noogle_aliases(doc)
            aliases_lower = [a.lower() for a in aliases]

            if path_lower == name_lower or name_lower in aliases_lower:
                exact_match = doc
                break
            elif name_lower in path_lower:
                partial_matches.append((path, doc))

        if not exact_match and not partial_matches:
            return error(f"Noogle function '{name}' not found", "NOT_FOUND")

        if not exact_match:
            # Suggest partial matches
            suggestions = [p for p, _ in partial_matches[:5]]
            return error(f"Function '{name}' not found. Similar: {', '.join(suggestions)}", "NOT_FOUND")

        doc = exact_match
        path = _get_noogle_function_path(doc)
        meta = doc.get("meta", {})
        content = doc.get("content", {})

        results = [f"Noogle Function: {path}"]

        # Type signature
        sig = _get_noogle_type_signature(doc)
        if sig:
            results.append(f"Type: {sig}")

        # Path
        results.append(f"Path: {path}")

        # Aliases
        aliases = _get_noogle_aliases(doc)
        if aliases:
            results.append(f"Aliases: {', '.join(aliases)}")

        # Primop info (for builtins)
        primop_meta = meta.get("primop_meta", {})
        if primop_meta:
            arity = primop_meta.get("arity")
            args = primop_meta.get("args", [])
            if arity is not None:
                if args:
                    results.append(f"Primop: Yes (arity: {arity}, args: {', '.join(args)})")
                else:
                    results.append(f"Primop: Yes (arity: {arity})")

        results.append("")

        # Description
        desc = _get_noogle_description(doc)
        if desc:
            results.append("Description:")
            results.append(desc)
            results.append("")

        # Example
        example = content.get("example", "")
        if example:
            example = strip_html(example)
            results.append("Example:")
            # Truncate long examples
            if len(example) > 500:
                example = example[:500] + "..."
            results.append(example)
            results.append("")

        # Source position
        position = meta.get("position", {})
        if position:
            file_path = position.get("file", "")
            line = position.get("line")
            if file_path:
                if line:
                    results.append(f"Source: {file_path}:{line}")
                else:
                    results.append(f"Source: {file_path}")

        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _stats_noogle() -> str:
    """Get Noogle statistics."""
    try:
        data, _ = noogle_cache.get_data()

        # Count functions by category
        categories: dict[str, int] = {}
        with_signatures = 0
        with_docs = 0

        for doc in data:
            path = _get_noogle_function_path(doc)
            if "." in path:
                cat = ".".join(path.split(".")[:2])  # e.g., "lib.strings"
            else:
                cat = path

            categories[cat] = categories.get(cat, 0) + 1

            if _get_noogle_type_signature(doc):
                with_signatures += 1
            if _get_noogle_description(doc):
                with_docs += 1

        top_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]

        results = [
            "Noogle Statistics:",
            f"* Total functions: {len(data):,}",
            f"* With type signatures: {with_signatures:,}",
            f"* With documentation: {with_docs:,}",
            f"* Categories: {len(categories)}",
            "* Top categories:",
        ]

        for cat, count in top_cats:
            results.append(f"  - {cat}: {count}")

        results.append("")
        results.append("Data source: noogle.dev (updated daily)")

        return "\n".join(results)
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))


def _browse_noogle_options(prefix: str) -> str:
    """Browse Noogle functions by prefix, or list categories if no prefix."""
    try:
        data, _ = noogle_cache.get_data()

        if not prefix:
            # List top-level categories with counts
            categories: dict[str, int] = {}
            for doc in data:
                path = _get_noogle_function_path(doc)
                if "." in path:
                    cat = ".".join(path.split(".")[:2])  # e.g., "lib.strings"
                else:
                    cat = path
                categories[cat] = categories.get(cat, 0) + 1

            sorted_cats = sorted(categories.items(), key=lambda x: (-x[1], x[0]))
            results = [f"Noogle function categories ({len(categories)} total):\n"]
            for cat, count in sorted_cats:
                results.append(f"* {cat} ({count} functions)")
            return "\n".join(results)

        # List functions under prefix
        prefix_lower = prefix.lower()
        prefix_dot = prefix_lower if prefix_lower.endswith(".") else prefix_lower + "."
        matches = []

        for doc in data:
            path = _get_noogle_function_path(doc)
            path_lower = path.lower()
            if path_lower.startswith(prefix_dot) or path_lower == prefix_lower:
                matches.append(
                    {
                        "path": path,
                        "type": _get_noogle_type_signature(doc),
                        "description": _get_noogle_description(doc),
                    }
                )

        if not matches:
            return f"No Noogle functions found with prefix '{prefix}'"

        results = [f"Noogle functions with prefix '{prefix}' ({len(matches)} found):\n"]
        for func in sorted(matches, key=lambda x: x["path"])[:100]:
            results.append(f"* {func['path']}")
            if func["type"]:
                sig = func["type"][:80] + "..." if len(func["type"]) > 80 else func["type"]
                results.append(f"  Type: {sig}")
            if func["description"]:
                desc = func["description"][:150] + "..." if len(func["description"]) > 150 else func["description"]
                results.append(f"  {desc}")
            results.append("")

        if len(matches) > 100:
            results.append(f"... and {len(matches) - 100} more functions")
        return "\n".join(results).strip()
    except APIError as e:
        return error(str(e), "API_ERROR")
    except Exception as e:
        return error(str(e))
