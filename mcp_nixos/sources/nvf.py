"""Contract and shared helpers for the NVF options source.

NVF's standalone/flake interface publishes its option catalogue under
``vim.*``. The NixOS and Home Manager modules wrap the same catalogue under
``programs.nvf.settings.vim.*``. MCP callers may also use the shorter
``programs.nvf.vim.*`` spelling; all supported wrapper paths normalize to the
canonical ``vim.*`` form before lookup or prefix browsing.

The source tracks NVF's latest published unstable documentation and supports
the existing ``search``, ``info``, ``browse``, and ``stats`` actions.
"""

from typing import Final, TypedDict

from ..caches import nvf_cache
from ..config import APIError
from ..utils import error

NVF_SOURCE: Final = "nvf"
NVF_DISPLAY_NAME: Final = "NVF"
NVF_DOCS_TRACK: Final = "unstable"
NVF_CANONICAL_ROOT: Final = "vim"
NVF_SUPPORTED_ACTIONS: Final[frozenset[str]] = frozenset({"search", "info", "browse", "stats"})

_NVF_SEARCH_DESCRIPTION_LIMIT: Final = 200
_NVF_SEARCH_DEFAULT_LIMIT: Final = 120
_NVF_INFO_EXAMPLE_LIMIT: Final = 500
_NVF_BROWSE_LIMIT: Final = 100

# Longest aliases come first to make the intended precedence explicit. Each
# alias names the root itself (without a trailing dot), allowing both a full
# option path and a browse prefix such as ``programs.nvf.vim`` to normalize.
NVF_OPTION_ROOT_ALIASES: Final[tuple[str, ...]] = (
    "config.programs.nvf.settings.vim",
    "programs.nvf.settings.vim",
    "programs.nvf.vim",
)


class NvfOption(TypedDict):
    """Normalized option record shared by NVF cache and source operations."""

    name: str
    type: str
    description: str
    default: str
    example: str
    declarations: list[str]
    url: str


def normalize_nvf_option_path(value: str) -> str:
    """Normalize a canonical or wrapped NVF option path.

    Only recognized option roots are rewritten. Ordinary keyword searches,
    unknown paths, and wrapper-only options such as ``programs.nvf.enable``
    are returned unchanged so later search logic can handle them honestly.
    Prefix comparison is case-insensitive while the unmatched suffix keeps
    its original spelling.
    """
    path = value.strip()
    path_lower = path.lower()

    for alias in NVF_OPTION_ROOT_ALIASES:
        alias_lower = alias.lower()
        if path_lower == alias_lower:
            return NVF_CANONICAL_ROOT
        if path_lower.startswith(alias_lower + "."):
            return NVF_CANONICAL_ROOT + path[len(alias) :]

    return path


def nvf_option_category(name: str) -> str:
    """Return a useful browse/stats category for an NVF option path.

    Since nearly every public NVF option begins with ``vim``, the first two
    path components form the category (for example ``vim.languages``).
    Non-canonical names fall back to their first component.
    """
    normalized = normalize_nvf_option_path(name)
    parts = normalized.split(".") if normalized else []
    if not parts:
        return ""
    if parts[0].lower() == NVF_CANONICAL_ROOT and len(parts) > 1:
        return ".".join(parts[:2])
    return parts[0]


def _compact_text(value: str, limit: int) -> str:
    """Collapse whitespace and truncate text for compact result listings."""
    compact = " ".join(value.split())
    if len(compact) > limit:
        return compact[:limit] + "..."
    return compact


def _nvf_match_score(option: NvfOption, query: str) -> int:
    """Score a search match, prioritizing option paths over descriptions."""
    name = option["name"].casefold()
    description = option["description"].casefold()

    if name == query:
        return 100
    if name.startswith(query + "."):
        return 80
    if query in name:
        return 60
    if query in description:
        return 20
    return 0


def _search_nvf(query: str, limit: int) -> str:
    """Search NVF options by canonical path or description text."""
    try:
        options = nvf_cache.get_options()
        display_query = query.strip()
        canonical_query = normalize_nvf_option_path(query).casefold()

        matches: list[tuple[int, NvfOption]] = []
        if canonical_query:
            for option in options:
                score = _nvf_match_score(option, canonical_query)
                if score:
                    matches.append((score, option))

        matches.sort(key=lambda match: (-match[0], match[1]["name"].casefold()))
        matches = matches[:limit]

        if not matches:
            return f"No NVF options found matching '{display_query}'"

        results = [f"Found {len(matches)} NVF options matching '{display_query}':\n"]
        for _score, option in matches:
            results.append(f"* {option['name']}")
            if option["type"]:
                results.append(f"  Type: {option['type']}")
            if option["default"]:
                default = _compact_text(option["default"], _NVF_SEARCH_DEFAULT_LIMIT)
                results.append(f"  Default: {default}")
            if option["description"]:
                description = _compact_text(option["description"], _NVF_SEARCH_DESCRIPTION_LIMIT)
                results.append(f"  {description}")
            results.append("")

        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as exc:
        return error(str(exc))


def _format_nvf_option(option: NvfOption) -> str:
    """Format one normalized NVF option for detailed display."""
    lines = [f"NVF Option: {option['name']}"]

    if option["type"]:
        lines.append(f"Type: {option['type']}")
    if option["description"]:
        lines.append(f"Description: {option['description']}")
    if option["default"]:
        lines.append(f"Default: {option['default']}")
    if option["example"]:
        example = option["example"]
        if len(example) > _NVF_INFO_EXAMPLE_LIMIT:
            example = example[:_NVF_INFO_EXAMPLE_LIMIT] + "..."
        lines.append(f"Example: {example}")

    declarations = option["declarations"]
    if len(declarations) == 1:
        lines.append(f"Declared in: {declarations[0]}")
    elif declarations:
        lines.append("Declared in:")
        lines.extend(f"* {declaration}" for declaration in declarations)

    if option["url"]:
        lines.append(f"Documentation: {option['url']}")

    return "\n".join(lines)


def _info_nvf(name: str) -> str:
    """Get detailed information for an exact NVF option path."""
    try:
        options = nvf_cache.get_options()
        display_name = name.strip()
        canonical_name = normalize_nvf_option_path(name)

        for option in options:
            if option["name"] == canonical_name:
                return _format_nvf_option(option)

        canonical_lower = canonical_name.casefold()
        for option in options:
            if option["name"].casefold() == canonical_lower:
                return _format_nvf_option(option)

        similar = sorted(
            (option["name"] for option in options if canonical_lower in option["name"].casefold()),
            key=str.casefold,
        )[:5]
        if similar:
            return error(f"Option '{display_name}' not found. Similar: {', '.join(similar)}", "NOT_FOUND")
        return error(f"NVF option '{display_name}' not found", "NOT_FOUND")
    except APIError:
        raise
    except Exception as exc:
        return error(str(exc))


def _stats_nvf() -> str:
    """Summarize the current published NVF option catalogue."""
    try:
        options = nvf_cache.get_options()
        categories: dict[str, int] = {}
        for option in options:
            category = nvf_option_category(option["name"])
            if category:
                categories[category] = categories.get(category, 0) + 1

        top_categories = sorted(categories.items(), key=lambda item: (-item[1], item[0].casefold()))[:10]
        results = [
            "NVF Statistics:",
            f"* Documentation track: {NVF_DOCS_TRACK}",
            f"* Total options: {len(options):,}",
            f"* Categories: {len(categories)}",
            "* Top categories:",
        ]
        for category, count in top_categories:
            results.append(f"  - {category}: {count:,}")
        return "\n".join(results)
    except APIError:
        raise
    except Exception as exc:
        return error(str(exc))


def _browse_nvf_options(prefix: str) -> str:
    """List NVF categories or options below a canonical/wrapped prefix."""
    try:
        options = nvf_cache.get_options()
        canonical_prefix = normalize_nvf_option_path(prefix).rstrip(".")

        if not canonical_prefix:
            categories: dict[str, int] = {}
            for option in options:
                category = nvf_option_category(option["name"])
                if category:
                    categories[category] = categories.get(category, 0) + 1

            sorted_categories = sorted(categories.items(), key=lambda item: (-item[1], item[0].casefold()))
            results = [f"NVF option categories ({len(categories)} total):\n"]
            for category, count in sorted_categories:
                noun = "option" if count == 1 else "options"
                results.append(f"* {category} ({count:,} {noun})")
            return "\n".join(results)

        prefix_lower = canonical_prefix.casefold()
        prefix_dot = prefix_lower + "."
        matches = [
            option
            for option in options
            if option["name"].casefold() == prefix_lower or option["name"].casefold().startswith(prefix_dot)
        ]

        if not matches:
            return f"No NVF options found with prefix '{canonical_prefix}'"

        matches.sort(key=lambda option: option["name"].casefold())
        results = [f"NVF options with prefix '{canonical_prefix}' ({len(matches):,} found):\n"]
        for option in matches[:_NVF_BROWSE_LIMIT]:
            results.append(f"* {option['name']}")
            if option["type"]:
                results.append(f"  Type: {option['type']}")
            if option["description"]:
                description = _compact_text(option["description"], _NVF_SEARCH_DESCRIPTION_LIMIT)
                results.append(f"  {description}")
            results.append("")

        if len(matches) > _NVF_BROWSE_LIMIT:
            results.append(f"... and {len(matches) - _NVF_BROWSE_LIMIT:,} more options")
        return "\n".join(results).strip()
    except APIError:
        raise
    except Exception as exc:
        return error(str(exc))
