"""Unit tests for the shared HTML option catalogue cache, scoring, and sources."""

from unittest.mock import patch

import pytest
from mcp_nixos.caches import HtmlOptionsCache, darwin_cache, home_manager_cache
from mcp_nixos.config import APIError
from mcp_nixos.sources.base import (
    _browse_options,
    _info_html_options,
    _search_html_options,
    _stats_html_options,
)
from mcp_nixos.utils import score_option_match

# The GH #190 scenario: alphabetically-earlier substring matches used to crowd
# out the programs.git.* namespace for the query "git".
GIT_OPTIONS = [
    {"name": "programs.bun.enableGitIntegration", "description": "Enable Git integration.", "type": "boolean"},
    {"name": "programs.delta.enableGitIntegration", "description": "Enable Git integration.", "type": "boolean"},
    {"name": "programs.diff-so-fancy.enableGitIntegration", "description": "Git integration.", "type": "boolean"},
    {"name": "programs.difftastic.enableGitIntegration", "description": "Git integration.", "type": "boolean"},
    {"name": "programs.git.enable", "description": "Whether to enable Git.", "type": "boolean"},
    {"name": "programs.git.userName", "description": "Default user name to use.", "type": "null or string"},
    {"name": "services.syncthing.enable", "description": "Whether to enable Syncthing.", "type": "boolean"},
]


def make_cache(options: list[dict[str, str]] | None = None) -> HtmlOptionsCache:
    cache = HtmlOptionsCache("https://example.invalid/options.html", "Home Manager")
    cache.options = options if options is not None else list(GIT_OPTIONS)
    return cache


@pytest.mark.unit
class TestScoreOptionMatch:
    """Test the shared option match scorer."""

    def test_exact_match_scores_highest(self):
        assert score_option_match("programs.git.enable", "", "programs.git.enable") == 100

    def test_leading_path_prefix(self):
        assert score_option_match("programs.git.enable", "", "programs.git") == 80

    def test_full_path_segment_beats_name_substring(self):
        segment = score_option_match("programs.git.enable", "", "git")
        substring = score_option_match("programs.bun.enableGitIntegration", "", "git")
        assert segment == 69
        assert substring == 60
        assert segment > substring

    def test_earlier_segment_beats_deeper_segment(self):
        module = score_option_match("programs.git.enable", "", "git")
        nested = score_option_match("programs.difftastic.git.enable", "", "git")
        assert module == 69
        assert nested == 68
        assert module > nested

    def test_multi_segment_mid_path_match(self):
        assert score_option_match("vim.languages.nix.enable", "", "languages.nix") == 69

    def test_description_match_scores_lowest(self):
        assert score_option_match("services.syncthing.enable", "Whether to enable Git hooks.", "git hooks") == 20

    def test_no_match_scores_zero(self):
        assert score_option_match("programs.firefox.enable", "Browser.", "git") == 0

    def test_empty_query_scores_zero(self):
        assert score_option_match("programs.git.enable", "anything", "") == 0

    def test_case_insensitive(self):
        assert score_option_match("programs.Git.enable", "", "GIT") == 69


@pytest.mark.unit
class TestHtmlOptionsCache:
    """Test the process-local HTML option catalogue cache."""

    def test_fetches_once_and_caches(self):
        cache = HtmlOptionsCache("https://example.invalid/options.html", "Home Manager")
        with patch("mcp_nixos.caches.parse_html_options", return_value=list(GIT_OPTIONS)) as mock_parse:
            first = cache.get_options()
            second = cache.get_options()
        assert first is second
        mock_parse.assert_called_once_with("https://example.invalid/options.html", limit=None)

    def test_empty_catalogue_raises_and_is_not_cached(self):
        cache = HtmlOptionsCache("https://example.invalid/options.html", "nix-darwin")
        with patch("mcp_nixos.caches.parse_html_options", return_value=[]):
            with pytest.raises(APIError, match="no options found"):
                cache.get_options()
        assert cache.options is None

    def test_module_singletons_exist(self):
        assert home_manager_cache.display_name == "Home Manager"
        assert darwin_cache.display_name == "nix-darwin"


@pytest.mark.unit
class TestSearchRanking:
    """Test ranked search over a cached catalogue (GH #190 regression)."""

    def test_direct_namespace_outranks_substring_matches(self):
        result = _search_html_options(make_cache(), "git", 5)
        lines = [line for line in result.splitlines() if line.startswith("* ")]
        assert lines[0] == "* programs.git.enable"
        assert lines[1] == "* programs.git.userName"
        assert "enableGitIntegration" in result

    def test_limit_truncates_after_ranking(self):
        result = _search_html_options(make_cache(), "git", 2)
        assert "Found 2 Home Manager options matching 'git':" in result
        assert "programs.git.enable" in result
        assert "enableGitIntegration" not in result

    def test_exact_path_query_ranks_first(self):
        result = _search_html_options(make_cache(), "programs.git.enable", 5)
        lines = [line for line in result.splitlines() if line.startswith("* ")]
        assert lines[0] == "* programs.git.enable"

    def test_no_matches(self):
        result = _search_html_options(make_cache(), "zzznotfound", 5)
        assert result == "No Home Manager options found matching 'zzznotfound'"

    def test_api_error_returns_error_text(self):
        cache = HtmlOptionsCache("https://example.invalid/options.html", "Home Manager")
        with patch.object(cache, "get_options", side_effect=APIError("boom")):
            result = _search_html_options(cache, "git", 5)
        assert result.startswith("Error")
        assert "boom" in result


@pytest.mark.unit
class TestInfoHtmlOptions:
    """Test option detail lookup over a cached catalogue."""

    def test_exact_option(self):
        result = _info_html_options(make_cache(), "programs.git.enable")
        assert "Option: programs.git.enable" in result
        assert "Type: boolean" in result
        assert "Description: Whether to enable Git." in result

    def test_not_found_with_suggestions(self):
        result = _info_html_options(make_cache(), "programs.git")
        assert "NOT_FOUND" in result
        assert "programs.git.enable" in result

    def test_not_found_without_suggestions(self):
        result = _info_html_options(make_cache(), "zzznotfound")
        assert "NOT_FOUND" in result
        assert "Similar" not in result


@pytest.mark.unit
class TestStatsHtmlOptions:
    """Test stats over a cached catalogue."""

    def test_counts_and_categories(self):
        result = _stats_html_options(make_cache())
        assert "Home Manager Statistics:" in result
        assert "* Total options: 7" in result
        assert "- programs: 6" in result


@pytest.mark.unit
class TestBrowseOptionsCached:
    """Test prefix browsing backed by the catalogue caches."""

    def test_browse_prefix(self):
        with patch.object(home_manager_cache, "get_options", return_value=list(GIT_OPTIONS)):
            result = _browse_options("home-manager", "programs.git")
        assert "Home Manager options with prefix 'programs.git' (2 found):" in result
        assert "* programs.git.enable" in result
        assert "* programs.git.userName" in result

    def test_browse_categories(self):
        with patch.object(darwin_cache, "get_options", return_value=list(GIT_OPTIONS)):
            result = _browse_options("darwin", "")
        assert "nix-darwin categories" in result
        assert "* programs (6 options)" in result

    def test_browse_prefix_truncates_long_listings(self):
        many = [{"name": f"programs.git.alias{i:03}", "description": "", "type": "string"} for i in range(150)]
        with patch.object(home_manager_cache, "get_options", return_value=many):
            result = _browse_options("home-manager", "programs.git")
        assert "(150 found)" in result
        assert "... and 50 more options" in result

    def test_browse_prefix_no_matches(self):
        with patch.object(home_manager_cache, "get_options", return_value=list(GIT_OPTIONS)):
            result = _browse_options("home-manager", "zzz")
        assert result == "No Home Manager options found with prefix 'zzz'"
