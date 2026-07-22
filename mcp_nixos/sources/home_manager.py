"""Home Manager options source."""

from ..caches import home_manager_cache
from .base import _info_html_options, _search_html_options, _stats_html_options


def _search_home_manager(query: str, limit: int) -> str:
    """Search Home Manager options, ranked by match quality."""
    return _search_html_options(home_manager_cache, query, limit)


def _info_home_manager(name: str) -> str:
    """Get detailed info for a Home Manager option."""
    return _info_html_options(home_manager_cache, name)


def _stats_home_manager() -> str:
    """Get Home Manager option counts and top categories."""
    return _stats_html_options(home_manager_cache)
