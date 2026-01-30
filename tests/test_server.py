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


class TestElasticsearchQuery:
    """Test Elasticsearch query helper."""

    @patch("mcp_nixos.server.requests.post")
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

    @patch("mcp_nixos.server.requests.post")
    def test_custom_size(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_resp

        es_query("test-index", {"match_all": {}}, size=50)
        call_args = mock_post.call_args[1]
        assert call_args["json"]["size"] == 50

    @patch("mcp_nixos.server.requests.post")
    def test_timeout(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.Timeout()
        with pytest.raises(APIError, match="Connection timed out"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.server.requests.post")
    def test_request_error(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.HTTPError("HTTP error")
        with pytest.raises(APIError, match="API error"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.server.requests.post")
    def test_malformed_response(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"invalid": "structure"}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert result == []


class TestParseHtmlOptions:
    """Test HTML option parsing."""

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
    def test_timeout(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.Timeout()
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)

    @patch("mcp_nixos.server.requests.get")
    def test_request_error(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.RequestException("Network error")
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)


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

    @patch("mcp_nixos.server.requests.post")
    def test_discover_channels(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"count": 100000}
        mock_post.return_value = mock_resp

        cache = ChannelCache()
        cache.available_channels = None
        result = cache.get_available()
        assert isinstance(result, dict)


class TestChannelValidation:
    """Test channel validation helpers."""

    @patch("mcp_nixos.server.get_channels")
    def test_valid_channel(self, mock_get):
        mock_get.return_value = {"stable": "latest-44-nixos-25.11"}
        result = validate_channel("stable")
        assert result is True

    @patch("mcp_nixos.server.get_channels")
    def test_invalid_channel(self, mock_get):
        mock_get.return_value = {"stable": "latest-44-nixos-25.11"}
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
    def test_search_wiki_no_results(self, mock_get):
        """Test wiki search with no results."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"search": []}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("xyznonexistent", 10)
        assert "No wiki articles found" in result

    @patch("mcp_nixos.server.requests.get")
    def test_search_wiki_timeout(self, mock_get):
        """Test wiki search timeout handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.Timeout()
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.server.requests.get")
    def test_search_wiki_api_error(self, mock_get):
        """Test wiki search API error handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.RequestException("Connection failed")
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "API_ERROR" in result

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
    def test_info_wiki_not_found(self, mock_get):
        """Test wiki page not found."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"pages": {"-1": {"missing": True, "title": "NonexistentPage"}}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("NonexistentPage")
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.server.requests.get")
    def test_info_wiki_timeout(self, mock_get):
        """Test wiki info timeout handling."""
        from mcp_nixos.server import _info_wiki

        mock_get.side_effect = requests.Timeout()
        result = _info_wiki("test")
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
    def test_nixdev_cache_timeout(self, mock_get):
        """Test nix.dev cache handles timeout."""
        from mcp_nixos.server import APIError, nixdev_cache

        mock_get.side_effect = requests.Timeout()
        nixdev_cache.index = None

        with pytest.raises(APIError) as exc_info:
            nixdev_cache.get_index()
        assert "Timeout" in str(exc_info.value)

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
    def test_search_noogle_timeout(self, mock_get):
        """Test Noogle search timeout handling."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_get.side_effect = requests.Timeout()
        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("test", 10)
        assert "Error" in result

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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

    @patch("mcp_nixos.server.requests.get")
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
