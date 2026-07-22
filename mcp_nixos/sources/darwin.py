"""nix-darwin options source."""

from ..caches import darwin_cache
from .base import _info_html_options, _search_html_options, _stats_html_options


def _search_darwin(query: str, limit: int) -> str:
    """Search nix-darwin options, ranked by match quality."""
    return _search_html_options(darwin_cache, query, limit)


def _info_darwin(name: str) -> str:
    """Get detailed info for a nix-darwin option."""
    return _info_html_options(darwin_cache, name)


def _stats_darwin() -> str:
    """Get nix-darwin option counts and top categories."""
    return _stats_html_options(darwin_cache)
