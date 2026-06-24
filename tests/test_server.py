"""Tests for server helper functions and internal logic."""

from unittest.mock import Mock, patch

import pytest
import requests
from mcp_nixos.server import (
    HOME_MANAGER_URL,
    NIXOS_API,
    NIXOS_AUTH,
    ChannelCache,
    error,
    es_query,
    get_channel_suggestions,
    get_channels,
    parse_html_options,
    validate_channel,
)


@pytest.mark.unit
class TestErrorFunction:
    """Test error formatting helper."""

    def test_basic_error(self):
        result = error("Test message")
        assert result == "Error (ERROR): Test message"

    def test_custom_code(self):
        result = error("Not found", "NOT_FOUND")
        assert result == "Error (NOT_FOUND): Not found"

    def test_special_characters(self):
        result = error('Error <tag> & "quotes"', "CODE")
        assert result == 'Error (CODE): Error <tag> & "quotes"'

    def test_empty_message(self):
        result = error("")
        assert result == "Error (ERROR): "


@pytest.mark.unit
class TestElasticsearchQuery:
    """Test Elasticsearch query helper."""

    @patch("mcp_nixos.sources.base.requests.post")
    def test_success(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": [{"_source": {"test": "data"}}]}}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert len(result) == 1
        assert result[0]["_source"]["test"] == "data"
        mock_post.assert_called_once_with(
            f"{NIXOS_API}/test-index/_search",
            json={"query": {"match_all": {}}, "size": 20},
            auth=NIXOS_AUTH,
            timeout=10,
        )

    @patch("mcp_nixos.sources.base.requests.post")
    def test_custom_size(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_resp

        es_query("test-index", {"match_all": {}}, size=50)
        call_args = mock_post.call_args[1]
        assert call_args["json"]["size"] == 50

    @patch("mcp_nixos.sources.base.requests.post")
    def test_timeout(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.Timeout()
        with pytest.raises(APIError, match="Connection timed out"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.sources.base.requests.post")
    def test_request_error(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.HTTPError("HTTP error")
        with pytest.raises(APIError, match="API error"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.sources.base.requests.post")
    def test_malformed_response(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"invalid": "structure"}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert result == []


@pytest.mark.unit
class TestParseHtmlOptions:
    """Test HTML option parsing."""

    @patch("mcp_nixos.utils.requests.get")
    def test_success(self, mock_get):
        html = b"""
        <html><body>
        <dt><a id="opt-programs.git.enable">programs.git.enable</a></dt>
        <dd><p>Description</p><span class="term">Type: boolean</span></dd>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL)
        assert isinstance(result, list)

    @patch("mcp_nixos.utils.requests.get")
    def test_with_query(self, mock_get):
        html = b"""
        <html><body>
        <dt><a id="opt-programs.git.enable">programs.git.enable</a></dt>
        <dd><p>Enable git</p><span class="term">Type: boolean</span></dd>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL, query="git")
        assert isinstance(result, list)
        # Should find the git option
        assert len(result) >= 1

    @patch("mcp_nixos.utils.requests.get")
    def test_timeout(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.Timeout()
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)

    @patch("mcp_nixos.utils.requests.get")
    def test_request_error(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.RequestException("Network error")
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)


@pytest.mark.unit
class TestChannelCache:
    """Test channel cache functionality."""

    def test_singleton_behavior(self):
        cache = ChannelCache()
        cache.available_channels = {"test": "value"}
        result = cache.get_available()
        assert result == {"test": "value"}

    def test_resolved_channels_fallback(self):
        cache = ChannelCache()
        cache.available_channels = {}  # Empty available channels
        cache.resolved_channels = None
        result = cache.get_resolved()
        assert cache.using_fallback is True
        assert "unstable" in result

    @patch("mcp_nixos.sources.base.requests.post")
    def test_discover_channels(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"count": 100000}
        mock_post.return_value = mock_resp

        cache = ChannelCache()
        cache.available_channels = None
        result = cache.get_available()
        assert isinstance(result, dict)


@pytest.mark.unit
class TestChannelValidation:
    """Test channel validation helpers."""

    @patch("mcp_nixos.sources.base.requests.post")
    @patch("mcp_nixos.sources.base.get_channels")
    def test_valid_channel(self, mock_get_channels, mock_post):
        mock_get_channels.return_value = {"stable": "latest-44-nixos-25.11"}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"count": 100}
        result = validate_channel("stable")
        assert result is True

    @patch("mcp_nixos.sources.base.get_channels")
    def test_invalid_channel(self, mock_get_channels):
        mock_get_channels.return_value = {"stable": "latest-44-nixos-25.11"}
        result = validate_channel("nonexistent")
        assert result is False

    def test_special_characters(self):
        result = validate_channel("invalid<>channel")
        assert result is False

    def test_suggestions(self):
        result = get_channel_suggestions("unstabel")
        assert "unstable" in result or "Did you mean" in result or "Available" in result


class TestGetChannels:
    """Test get_channels function."""

    def test_returns_dict(self):
        result = get_channels()
        assert isinstance(result, dict)

    def test_contains_unstable(self):
        result = get_channels()
        assert "unstable" in result


@pytest.mark.unit
class TestWikiFunctions:
    """Test wiki.nixos.org internal functions."""

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_success(self, mock_get):
        """Test successful wiki search."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {
                "search": [
                    {"title": "Flakes", "snippet": "Flakes are...", "wordcount": 1500},
                    {"title": "Nvidia", "snippet": "GPU drivers...", "wordcount": 800},
                ]
            }
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("flakes", 10)
        assert "Found 2 wiki articles" in result
        assert "Flakes" in result
        assert "wiki.nixos.org" in result
        assert "Error" not in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_no_results(self, mock_get):
        """Test wiki search with no results."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"search": []}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("xyznonexistent", 10)
        assert "No wiki articles found" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_timeout(self, mock_get):
        """Test wiki search timeout handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.Timeout()
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_api_error(self, mock_get):
        """Test wiki search API error handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.RequestException("Connection failed")
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "API_ERROR" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_strips_html(self, mock_get):
        """Test wiki search strips HTML from snippets."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {
                "search": [
                    {
                        "title": "Test",
                        "snippet": '<span class="searchmatch">highlighted</span> text',
                        "wordcount": 100,
                    }
                ]
            }
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("test", 10)
        assert "<span" not in result
        assert "highlighted" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_success(self, mock_get):
        """Test successful wiki page info."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {
                "pages": {"123": {"title": "Flakes", "extract": "Flakes are a new way to manage Nix projects..."}}
            }
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Flakes")
        assert "Wiki: Flakes" in result
        assert "wiki.nixos.org" in result
        assert "Flakes are a new way" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_not_found(self, mock_get):
        """Test wiki page not found."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"pages": {"-1": {"missing": True, "title": "NonexistentPage"}}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("NonexistentPage")
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_timeout(self, mock_get):
        """Test wiki info timeout handling."""
        from mcp_nixos.server import _info_wiki

        mock_get.side_effect = requests.Timeout()
        result = _info_wiki("test")
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_truncates_long_extract(self, mock_get):
        """Test wiki info truncates very long extracts."""
        from mcp_nixos.server import _info_wiki

        long_extract = "A" * 2000
        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"pages": {"123": {"title": "Test", "extract": long_extract}}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Test")
        assert len(result) < len(long_extract) + 200  # Account for header
        assert "..." in result


@pytest.mark.unit
class TestNixDevFunctions:
    """Test nix.dev internal functions."""

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_success(self, mock_get):
        """Test successful nix.dev search."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/first-steps", "concepts/flakes"],
            "titles": ["First Steps", "Flakes"],
            "terms": {"flake": [1], "nix": [0, 1], "tutorial": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Reset cache to trigger fetch
        nixdev_cache.index = None

        result = _search_nixdev("flakes", 10)
        assert "Flakes" in result
        assert "nix.dev" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_no_results(self, mock_get):
        """Test nix.dev search with no matches."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {"docnames": ["tutorials/first-steps"], "titles": ["First Steps"], "terms": {"tutorial": [0]}}
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        result = _search_nixdev("xyznonexistent", 10)
        assert "No nix.dev documentation found" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_nixdev_cache_reuse(self, mock_get):
        """Test that nix.dev cache is reused."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/first-steps"],
            "titles": ["First Steps"],
            "terms": {"nix": [0], "tutorial": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        _search_nixdev("nix", 10)
        _search_nixdev("tutorial", 10)

        # Should only fetch once due to caching
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_nixdev_cache_timeout(self, mock_get):
        """Test nix.dev cache handles timeout."""
        from mcp_nixos.server import APIError, nixdev_cache

        mock_get.side_effect = requests.Timeout()
        nixdev_cache.index = None

        with pytest.raises(APIError) as exc_info:
            nixdev_cache.get_index()
        assert "Timeout" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_title_match_bonus(self, mock_get):
        """Test nix.dev search gives bonus to title matches."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/packaging", "concepts/flakes", "tutorials/flakes"],
            "titles": ["Packaging Python Apps", "Flakes Intro", "Flakes Tutorial"],
            "terms": {"flakes": [1, 2], "packaging": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        result = _search_nixdev("flakes", 10)
        # Title matches should appear
        assert "Flakes" in result


@pytest.mark.unit
class TestPlainTextOutputDocs:
    """Verify wiki/nix-dev outputs are plain text."""

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_wiki_search_no_xml(self, mock_get):
        """Test wiki search returns plain text."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {"search": [{"title": "Test", "snippet": "<code>example</code>", "wordcount": 100}]}
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("test", 10)
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_wiki_info_no_xml(self, mock_get):
        """Test wiki info returns plain text."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"pages": {"123": {"title": "Test", "extract": "Some content"}}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Test")
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")


@pytest.mark.unit
class TestPlainTextOutput:
    """Verify all outputs are plain text without XML/JSON."""

    def test_error_no_xml(self):
        result = error("Test <message>")
        assert "<error>" not in result
        assert "</error>" not in result

    def test_error_no_json(self):
        result = error("Test message")
        assert not result.startswith("{")
        assert not result.startswith("[")


@pytest.mark.unit
class TestNoogleFunctions:
    """Test Noogle (noogle.dev) internal functions."""

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_success(self, mock_get):
        """Test successful Noogle search."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"title": "mapAttrs", "path": ["lib", "attrsets", "mapAttrs"], "aliases": []},
                    "content": {
                        "signature": "(String -> Any -> Any) -> AttrSet -> AttrSet",
                        "content": "Apply a function to each element in an attribute set.",
                    },
                },
                {
                    "meta": {"title": "mapAttrs'", "path": ["lib", "attrsets", "mapAttrs'"], "aliases": []},
                    "content": {
                        "signature": "(String -> Any -> { name :: String; value :: Any; }) -> AttrSet -> AttrSet",
                        "content": "Like mapAttrs but allows changing names.",
                    },
                },
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Reset cache to trigger fetch
        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("mapAttrs", 10)
        assert "Found" in result
        assert "mapAttrs" in result
        assert "lib.attrsets.mapAttrs" in result
        assert "Error" not in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_no_results(self, mock_get):
        """Test Noogle search with no matches."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"title": "test", "path": ["lib", "test"], "aliases": []}, "content": {"content": "test"}}
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("xyznonexistent", 10)
        assert "No Noogle functions found" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_timeout(self, mock_get):
        """Test Noogle search timeout handling."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_get.side_effect = requests.Timeout()
        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("test", 10)
        assert "Error" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_info_noogle_success(self, mock_get):
        """Test successful Noogle function info."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {
                        "title": "mapAttrs",
                        "path": ["lib", "attrsets", "mapAttrs"],
                        "aliases": [["builtins", "mapAttrs"], ["lib", "mapAttrs"]],
                        "position": {"file": "lib/attrsets.nix", "line": 1016},
                    },
                    "content": {
                        "signature": "(String -> Any -> Any) -> AttrSet -> AttrSet",
                        "content": "Apply a function to each element in an attribute set.",
                        "example": 'mapAttrs (name: value: name + "-" + value) { x = "foo"; }',
                    },
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("lib.attrsets.mapAttrs")
        assert "Noogle Function: lib.attrsets.mapAttrs" in result
        assert "Type:" in result
        assert "Path:" in result
        assert "Aliases:" in result
        assert "Description:" in result
        assert "Example:" in result
        assert "Source:" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_info_noogle_not_found(self, mock_get):
        """Test Noogle function not found."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"title": "test", "path": ["lib", "test"], "aliases": []}, "content": {"content": "test"}}
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("nonexistent.function")
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_stats_noogle_success(self, mock_get):
        """Test Noogle statistics."""
        from mcp_nixos.server import _stats_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "strings", "concatStrings"]},
                    "content": {"signature": "[String] -> String", "content": "Concatenate strings"},
                },
                {
                    "meta": {"path": ["lib", "strings", "hasPrefix"]},
                    "content": {"signature": "String -> String -> Bool", "content": "Check prefix"},
                },
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {"content": "Map over attrs"}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _stats_noogle()
        assert "Noogle Statistics:" in result
        assert "Total functions:" in result
        assert "With type signatures:" in result
        assert "Categories:" in result
        assert "noogle.dev" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_browse_noogle_no_prefix(self, mock_get):
        """Test browsing Noogle categories with no prefix."""
        from mcp_nixos.server import _browse_noogle_options, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"path": ["lib", "strings", "concatStrings"]}, "content": {}},
                {"meta": {"path": ["lib", "strings", "hasPrefix"]}, "content": {}},
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _browse_noogle_options("")
        assert "Noogle function categories" in result
        assert "lib.strings" in result
        assert "lib.attrsets" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_browse_noogle_with_prefix(self, mock_get):
        """Test browsing Noogle functions with a prefix."""
        from mcp_nixos.server import _browse_noogle_options, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "strings", "concatStrings"]},
                    "content": {"signature": "[String] -> String", "content": "Concatenate strings"},
                },
                {
                    "meta": {"path": ["lib", "strings", "hasPrefix"]},
                    "content": {"signature": "String -> String -> Bool", "content": "Check prefix"},
                },
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _browse_noogle_options("lib.strings")
        assert "lib.strings" in result
        assert "concatStrings" in result
        assert "hasPrefix" in result
        assert "mapAttrs" not in result

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_cache_reuse(self, mock_get):
        """Test that Noogle cache is reused."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [{"meta": {"path": ["lib", "test"]}, "content": {"content": "test"}}],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        _search_noogle("test", 10)
        _search_noogle("other", 10)

        # Should only fetch once due to caching
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_alias_matching(self, mock_get):
        """Test Noogle search matches aliases."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {
                        "title": "mapAttrs",
                        "path": ["lib", "attrsets", "mapAttrs"],
                        "aliases": [["builtins", "mapAttrs"]],
                    },
                    "content": {"content": "Map over attrs"},
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("builtins.mapAttrs", 10)
        assert "lib.attrsets.mapAttrs" in result
        assert "builtins.mapAttrs" in result


@pytest.mark.unit
class TestNooglePlainTextOutput:
    """Verify Noogle outputs are plain text."""

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_search_no_xml(self, mock_get):
        """Test Noogle search returns plain text."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [{"meta": {"path": ["lib", "test"]}, "content": {"content": "test"}}],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("test", 10)
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_info_no_xml(self, mock_get):
        """Test Noogle info returns plain text."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "test"], "aliases": []},
                    "content": {"content": "test", "signature": "a -> b"},
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("lib.test")
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")


@pytest.mark.unit
class TestDenCache:
    """Test DenCache (issue #156)."""

    def _fresh_cache(self):
        """Reset the module-level den_cache singleton."""
        from mcp_nixos import caches

        caches.den_cache = caches.DenCache()
        return caches.den_cache

    def _overview_html(self, links: list[str]) -> str:
        """Build a /overview/ page containing the given internal doc links."""
        anchors = "".join(f'<a href="{href}">{href}</a>' for href in links)
        return f"<html><body><main>{anchors}</main></body></html>"

    def _page_html(self, title: str, body_html: str):
        """Build a Mock response carrying a Starlight-shaped page body."""
        html = (
            f"<html><body><main data-pagefind-body>"
            f'<h1 id="_top">{title}</h1>'
            f'<div class="sl-markdown-content">{body_html}</div>'
            f"</main></body></html>"
        )
        return self._http(html)

    def _http(self, html: str, status: int = 200):
        """Build a Mock response carrying the given HTML body."""
        resp = Mock(status_code=status, raise_for_status=Mock())
        resp.content = html.encode("utf-8")
        resp.ok = status < 400
        return resp

    @patch("mcp_nixos.caches.requests.get")
    def test_discover_paths_filters_to_doc_prefixes(self, mock_get):
        """Only paths under doc prefixes are kept; nav, community, etc. are dropped."""

        mock_get.return_value = self._http(
            self._overview_html(
                [
                    "/explanation/aspects/",  # kept
                    "/guides/from-zero-to-den",  # kept (normalised to trailing /)
                    "/reference/aspects/",  # kept
                    "/tutorials/microvm",  # kept
                    "/community",  # dropped
                    "/contributing/",  # dropped
                    "/releases#bleeding-edge-den",  # dropped (anchor)
                    "https://github.com/denful/den",  # dropped (external)
                    "/",  # dropped
                ]
            )
        )

        cache = self._fresh_cache()
        paths = cache._discover_paths()
        # Normalise: every path should have a trailing slash and a leading slash.
        assert all(p.startswith("/") and p.endswith("/") for p in paths)
        assert "/explanation/aspects/" in paths
        assert "/guides/from-zero-to-den/" in paths
        assert "/reference/aspects/" in paths
        assert "/tutorials/microvm/" in paths
        for dropped in ("/community", "/contributing", "/releases", "/"):
            assert not any(p == dropped or p == dropped + "/" for p in paths)

    @patch("mcp_nixos.caches.requests.get")
    def test_discover_paths_dedups(self, mock_get):
        """The same link appearing twice in the overview is returned once."""

        mock_get.return_value = self._http(
            self._overview_html(
                [
                    "/guides/from-zero-to-den/",
                    "/guides/from-zero-to-den",  # dup (normalised)
                    "/guides/from-zero-to-den/#section",  # dup (anchor stripped)
                ]
            )
        )

        cache = self._fresh_cache()
        paths = cache._discover_paths()
        assert paths.count("/guides/from-zero-to-den/") == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_discover_paths_overview_failure_raises(self, mock_get):
        """A 5xx response from /overview/ raises APIError."""
        from mcp_nixos.caches import APIError

        mock_get.return_value = self._http("", status=502)

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache._discover_paths()
        assert "HTTP 502" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_discover_paths_request_error_raises(self, mock_get):
        """A network error during overview fetch surfaces as APIError."""
        from mcp_nixos.caches import APIError

        mock_get.side_effect = requests.RequestException("connection reset")

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache._discover_paths()
        assert "Failed to fetch Den overview" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_get_pages_empty_overview_raises(self, mock_get):
        """If the overview has no doc links, get_pages raises APIError."""
        from mcp_nixos.caches import APIError

        mock_get.return_value = self._http(self._overview_html(["/community", "/contributing"]))

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache.get_pages()
        assert "No Den docs paths discovered" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_get_pages_uses_thread_pool(self, mock_get):
        """get_pages fans out per-page fetches via the thread pool."""

        def fake_get(url, **_kwargs):
            if url.endswith("/overview/"):
                return self._http(
                    self._overview_html(
                        [
                            "/guides/from-zero-to-den/",
                            "/explanation/aspects/",
                        ]
                    )
                )
            if url.endswith("/guides/from-zero-to-den/"):
                return self._page_html("From Zero to Den", "<p>Intro body.</p>")
            if url.endswith("/explanation/aspects/"):
                return self._page_html("Aspects & Functors", "<p>Aspects body.</p>")
            raise AssertionError(f"Unexpected URL in test: {url}")

        mock_get.side_effect = fake_get

        cache = self._fresh_cache()
        pages = cache.get_pages()
        assert len(pages) == 2
        names = {p["title"] for p in pages}
        assert names == {"From Zero to Den", "Aspects & Functors"}
        # First call is the overview, the rest are the two page fetches.
        assert mock_get.call_count == 3

    @patch("mcp_nixos.caches.requests.get")
    def test_get_pages_skips_404_page(self, mock_get):
        """A page that 404s is silently skipped, not surfaced as an error."""

        def fake_get(url, **_kwargs):
            if url.endswith("/overview/"):
                return self._http(
                    self._overview_html(
                        [
                            "/guides/from-zero-to-den/",
                            "/explanation/aspects/",
                        ]
                    )
                )
            if url.endswith("/guides/from-zero-to-den/"):
                return self._http("", status=404)
            if url.endswith("/explanation/aspects/"):
                return self._page_html("Aspects", "<p>Body.</p>")
            raise AssertionError(f"Unexpected URL in test: {url}")

        mock_get.side_effect = fake_get

        cache = self._fresh_cache()
        pages = cache.get_pages()
        assert len(pages) == 1
        assert pages[0]["title"] == "Aspects"

    def test_normalize_path(self):
        """Path normalization handles bare slugs, full URLs, and edge cases."""
        from mcp_nixos.caches import DenCache

        assert DenCache._normalize_path("/guides/from-zero-to-den/") == "/guides/from-zero-to-den/"
        assert DenCache._normalize_path("guides/from-zero-to-den") == "/guides/from-zero-to-den/"
        assert DenCache._normalize_path("https://den.denful.dev/explanation/aspects/") == "/explanation/aspects/"
        assert DenCache._normalize_path("/explanation/aspects/#anchor") == "/explanation/aspects/"
        # URL-encoded slashes / etc. are decoded.
        assert DenCache._normalize_path("/explanation/aspects%2Fother/") == "/explanation/aspects/other/"

    @patch("mcp_nixos.caches.requests.get")
    def test_fetch_page_prefers_main_with_data_pagefind_body(self, mock_get):
        """When a page has both a plain <main> and a <main data-pagefind-body>,
        the data-pagefind-body one wins. Defends against the `or True`
        tautology regression flagged by Copilot and CodeRabbit on PR #176."""
        from mcp_nixos.caches import DenCache

        # The first <main> is decoration / navigation chrome; the second is
        # the actual article body. Without the data-pagefind-body filter the
        # wrong one would be picked.
        html = (
            "<html><body>"
            "<main><h1>navigation chrome</h1></main>"
            "<main data-pagefind-body>"
            '<h1 id="_top">Aspects</h1>'
            '<div class="sl-markdown-content"><p>real body</p></div>'
            "</main></body></html>"
        )
        mock_get.return_value = self._http(html)

        page = DenCache._fetch_page("/explanation/aspects/")
        assert page is not None
        assert page["title"] == "Aspects"
        assert "real body" in page["body"]
        assert "navigation chrome" not in page["body"]


@pytest.mark.unit
class TestDenFunctions:
    """Test _search_den / _info_den / _stats_den / _browse_den (issue #156)."""

    def _page(self, path, title, body):
        return {
            "path": path,
            "url": f"https://den.denful.dev{path}",
            "title": title,
            "body": body,
        }

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_basic(self, mock_cache):
        """A title hit ranks above a body hit, and a prefix bonus pushes it higher."""
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.return_value = [
            self._page("/explanation/aspects/", "Aspects & Functors", "Body about aspects."),
            self._page("/reference/lib/", "Library Reference", "Some mention of aspects here."),
        ]

        result = _search_den("aspects", 5)
        # Title hit should come first.
        assert result.index("Aspects & Functors") < result.index("Library Reference")
        assert "Found 2 Den docs" in result
        assert "https://den.denful.dev/explanation/aspects/" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_no_results(self, mock_cache):
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.return_value = [self._page("/explanation/aspects/", "Aspects", "x")]
        result = _search_den("nonexistentterm", 5)
        assert "No Den docs found" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_case_insensitive(self, mock_cache):
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.return_value = [
            self._page("/explanation/aspects/", "Aspects & Functors", "Body about aspects.")
        ]
        # Uppercase query still matches a lowercase title.
        result = _search_den("ASPECTS", 5)
        assert "Aspects & Functors" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_empty_query_reports_error(self, mock_cache):
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.return_value = []
        result = _search_den("", 5)
        assert "Error" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_multi_term_accumulates_score(self, mock_cache):
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.return_value = [
            self._page("/x/a/", "A", "alpha"),
            self._page("/x/b/", "B", "alpha alpha beta"),
        ]
        result = _search_den("alpha beta", 5)
        # The page that has both terms should rank first.
        assert result.index("* B") < result.index("* A")

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_path_match(self, mock_cache):
        from mcp_nixos.server import _info_den

        mock_cache.get_pages.return_value = []
        mock_cache.get_by_path.return_value = self._page("/explanation/aspects/", "Aspects & Functors", "Body content.")

        result = _info_den("/explanation/aspects/")
        assert "Title: Aspects & Functors" in result
        assert "https://den.denful.dev/explanation/aspects/" in result
        assert "Path: /explanation/aspects/" in result
        assert "Body content." in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_url_match(self, mock_cache):
        from mcp_nixos.server import _info_den

        mock_cache.get_pages.return_value = []
        mock_cache.get_by_path.return_value = self._page("/explanation/aspects/", "Aspects & Functors", "Body content.")
        result = _info_den("https://den.denful.dev/explanation/aspects/")
        assert "Title: Aspects & Functors" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_slug_fallback(self, mock_cache):
        from mcp_nixos.server import _info_den

        aspect_page = self._page("/explanation/aspects/", "Aspects & Functors", "Body content.")
        # First call to get_by_path returns None (no match for "aspects" as a path)
        # so the slug-fallback kicks in via get_pages().
        mock_cache.get_by_path.return_value = None
        mock_cache.get_pages.return_value = [aspect_page]

        result = _info_den("aspects")
        assert "Title: Aspects & Functors" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_not_found(self, mock_cache):
        from mcp_nixos.server import _info_den

        mock_cache.get_by_path.return_value = None
        mock_cache.get_pages.return_value = [self._page("/explanation/aspects/", "Aspects", "Body content.")]
        result = _info_den("nonexistent-slug")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_empty_query(self, mock_cache):
        from mcp_nixos.server import _info_den

        result = _info_den("")
        assert "Error" in result
        assert "Query required" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_truncates_long_body(self, mock_cache):
        from mcp_nixos.server import _info_den
        from mcp_nixos.sources.den import _DEN_MAX_BODY_CHARS

        long_body = "x" * (_DEN_MAX_BODY_CHARS + 5000)
        mock_cache.get_pages.return_value = []
        mock_cache.get_by_path.return_value = self._page("/explanation/aspects/", "Aspects", long_body)
        result = _info_den("/explanation/aspects/")
        assert "[truncated]" in result
        # The full body should not appear in the result.
        assert long_body not in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_stats_basic(self, mock_cache):
        from mcp_nixos.server import _stats_den

        mock_cache.get_pages.return_value = [
            self._page("/explanation/aspects/", "A1", "x"),
            self._page("/explanation/policies/", "A2", "x"),
            self._page("/guides/from-zero-to-den/", "G1", "x"),
            self._page("/reference/lib/", "R1", "x"),
        ]
        result = _stats_den()
        assert "Total pages: 4" in result
        assert "explanation: 2" in result
        assert "guides: 1" in result
        assert "reference: 1" in result
        assert "Sections: 3" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_browse_no_prefix_lists_sections(self, mock_cache):
        from mcp_nixos.server import _browse_den

        mock_cache.get_pages.return_value = [
            self._page("/explanation/aspects/", "A1", "x"),
            self._page("/guides/from-zero-to-den/", "G1", "x"),
        ]
        result = _browse_den("")
        assert "Den doc sections" in result
        assert "explanation (1 pages)" in result
        assert "guides (1 pages)" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_browse_with_prefix(self, mock_cache):
        from mcp_nixos.server import _browse_den

        mock_cache.get_pages.return_value = [
            self._page("/guides/from-zero-to-den/", "From Zero to Den", "x"),
            self._page("/guides/from-flake-to-den/", "From Flake to Den", "x"),
            self._page("/explanation/aspects/", "Aspects", "x"),
        ]
        result = _browse_den("guides")
        assert "Den pages with prefix 'guides' (2 found)" in result
        assert "/guides/from-zero-to-den/ — From Zero to Den" in result
        assert "/guides/from-flake-to-den/ — From Flake to Den" in result
        # Explanation page must not appear under /guides/.
        assert "Aspects" not in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_browse_no_matches(self, mock_cache):
        from mcp_nixos.server import _browse_den

        mock_cache.get_pages.return_value = [self._page("/explanation/aspects/", "Aspects", "x")]
        result = _browse_den("nonexistent-section")
        assert "No Den pages found" in result

    @patch("mcp_nixos.sources.den.den_cache")
    def test_search_handles_cache_error(self, mock_cache):
        """APIError from the cache is converted to a plain-text `Error (...)`
        response (mirrors nix-dev / noogle)."""
        from mcp_nixos.caches import APIError
        from mcp_nixos.server import _search_den

        mock_cache.get_pages.side_effect = APIError("boom")
        result = _search_den("anything", 5)
        assert result == "Error (API_ERROR): boom"

    @patch("mcp_nixos.sources.den.den_cache")
    def test_info_handles_cache_error(self, mock_cache):
        from mcp_nixos.caches import APIError
        from mcp_nixos.server import _info_den

        mock_cache.get_by_path.side_effect = APIError("boom")
        result = _info_den("/anything/")
        assert result == "Error (API_ERROR): boom"

    @patch("mcp_nixos.sources.den.den_cache")
    def test_stats_handles_cache_error(self, mock_cache):
        from mcp_nixos.caches import APIError
        from mcp_nixos.server import _stats_den

        mock_cache.get_pages.side_effect = APIError("boom")
        result = _stats_den()
        assert result == "Error (API_ERROR): boom"

    @patch("mcp_nixos.sources.den.den_cache")
    def test_browse_handles_cache_error(self, mock_cache):
        from mcp_nixos.caches import APIError
        from mcp_nixos.server import _browse_den

        mock_cache.get_pages.side_effect = APIError("boom")
        result = _browse_den("anything")
        assert result == "Error (API_ERROR): boom"

    @patch("mcp_nixos.caches.requests.get")
    def test_fetch_page_5xx_propagates(self, mock_get):
        """A 5xx from a Den page lets the exception propagate up to the
        ThreadPoolExecutor future in get_pages(), where it's wrapped as
        APIError('Failed to fetch Den page ...')."""
        from mcp_nixos import caches
        from mcp_nixos.caches import APIError

        listing_html = '<html><body><a href="/explanation/aspects/">a</a></body></html>'

        resp_5xx = Mock(status_code=502)
        resp_5xx.raise_for_status = Mock(side_effect=requests.HTTPError("502 Bad Gateway"))

        overview = Mock(status_code=200, raise_for_status=Mock())
        overview.content = listing_html.encode("utf-8")
        overview.ok = True

        mock_get.side_effect = [overview, resp_5xx]

        original = caches.den_cache
        cache = caches.DenCache()
        caches.den_cache = cache
        try:
            with pytest.raises(APIError) as exc_info:
                cache.get_pages()
            assert "Failed to fetch Den page" in str(exc_info.value)
        finally:
            caches.den_cache = original

    @patch("mcp_nixos.caches.requests.get")
    def test_fetch_page_404_returns_none(self, mock_get):
        """A 404 means the overview linked to a page that no longer exists;
        skip silently so a stale link doesn't take the whole cache down."""
        from mcp_nixos.caches import DenCache

        resp = Mock(status_code=404)
        mock_get.return_value = resp

        assert DenCache._fetch_page("/nonexistent/") is None

    @patch("mcp_nixos.caches.requests.get")
    def test_concurrent_first_call_only_fetches_once(self, mock_get):
        """Double-checked locking: N concurrent first calls run the walk
        exactly once, not N times."""
        from concurrent.futures import ThreadPoolExecutor

        from mcp_nixos import caches

        # The _fresh_cache helper lives on TestDenCache; build a fresh
        # singleton here directly. Restore in finally so we don't leak
        # state into other tests.
        original = caches.den_cache
        cache = caches.DenCache()
        caches.den_cache = cache
        try:
            listing_html = '<html><body><a href="/explanation/aspects/">a</a></body></html>'
            page_html = (
                "<html><body><main data-pagefind-body>"
                '<h1 id="_top">Aspects</h1>'
                '<div class="sl-markdown-content"><p>Body.</p></div>'
                "</main></body></html>"
            )

            def _resp(html: str, status: int = 200):
                r = Mock(status_code=status, raise_for_status=Mock())
                r.content = html.encode("utf-8")
                r.ok = status < 400
                return r

            # Provide enough responses for any number of walks.
            mock_get.side_effect = [
                _resp(listing_html),
                _resp(page_html),
                _resp("", status=404),
            ] * 50

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: cache.get_pages(), range(20)))

            # Exactly one walk: 1 overview + 1 page = 2 calls.
            assert mock_get.call_count == 2
        finally:
            caches.den_cache = original
