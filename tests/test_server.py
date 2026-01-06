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
