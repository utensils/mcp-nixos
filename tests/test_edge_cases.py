#!/usr/bin/env python3
"""Comprehensive edge case tests for MCP-NixOS server."""

import pytest
from unittest.mock import Mock, patch
import requests
from mcp_nixos.server import (
    error,
    es_query,
    parse_html_options,
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_info,
    home_manager_list_options,
    darwin_search,
    darwin_info,
    darwin_list_options,
    darwin_options_by_prefix,
)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_error_with_none_message(self):
        """Test error function with None message."""
        result = error(None)  # type: ignore
        assert result == "Error (ERROR): "

    def test_error_with_empty_string(self):
        """Test error function with empty string."""
        result = error("")
        assert result == "Error (ERROR): "

    def test_error_with_unicode(self):
        """Test error function with unicode characters."""
        result = error("Failed to parse: 你好世界 🌍")
        assert result == "Error (ERROR): Failed to parse: 你好世界 🌍"

    @patch("requests.post")
    def test_es_query_malformed_response(self, mock_post):
        """Test es_query with malformed JSON response."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json = Mock(return_value={"unexpected": "structure"})
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"query": {}})
        assert result == []

    @patch("requests.post")
    def test_es_query_network_timeout(self, mock_post):
        """Test es_query with network timeout."""
        mock_post.side_effect = requests.Timeout("Connection timed out")

        with pytest.raises(Exception, match="API error: Connection timed out"):
            es_query("test-index", {"query": {}})

    @patch("requests.post")
    def test_es_query_http_error(self, mock_post):
        """Test es_query with HTTP error status."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        mock_post.return_value = mock_resp

        with pytest.raises(Exception, match="API error: 503 Service Unavailable"):
            es_query("test-index", {"query": {}})

    @patch("requests.get")
    def test_parse_html_options_large_document(self, mock_get):
        """Test parsing very large HTML documents."""
        # Create a large HTML document with many options
        large_html = (
            """
        <html><body>
        """
            + "\n".join(
                [
                    f"""
        <dt><a id="opt-test.option{i}">test.option{i}</a></dt>
        <dd>
            <p>Description for option {i}</p>
            <span class="term">Type: string</span>
        </dd>
        """
                    for i in range(1000)
                ]
            )
            + """
        </body></html>
        """
        )

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.text = large_html
        mock_get.return_value = mock_resp

        # Should respect limit
        options = parse_html_options("http://test.com", limit=50)
        assert len(options) == 50
        assert options[0]["name"] == "test.option0"
        assert options[49]["name"] == "test.option49"

    @patch("requests.get")
    def test_parse_html_options_malformed_html(self, mock_get):
        """Test parsing malformed HTML with missing tags."""
        malformed_html = """
        <html><body>
        <dt><a id="opt-test.option1">test.option1</a>
        <!-- Missing closing dt tag -->
        <dd>Description without proper structure
        <!-- Missing closing dd tag -->
        <dt><a id="opt-test.option2">test.option2</a></dt>
        <!-- Missing dd for this dt -->
        <dt><a id="opt-test.option3">test.option3</a></dt>
        <dd><p>Proper description</p></dd>
        </body></html>
        """

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.text = malformed_html
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com")
        # Should handle malformed HTML gracefully
        assert len(options) >= 1
        assert any(opt["name"] == "test.option3" for opt in options)

    @patch("requests.get")
    def test_parse_html_options_special_characters(self, mock_get):
        """Test parsing options with special characters and HTML entities."""
        html_with_entities = """
        <html><body>
        <dt><a id="opt-test.option&lt;name&gt;">test.option&lt;name&gt;</a></dt>
        <dd>
            <p>Description with &amp; entities &quot;quoted&quot; and &apos;apostrophes&apos;</p>
            <span class="term">Type: list of (attribute set)</span>
        </dd>
        <dt><a id="opt-programs.firefox.profiles._name_.search">programs.firefox.profiles.<name>.search</a></dt>
        <dd><p>Firefox search configuration</p></dd>
        </body></html>
        """

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.text = html_with_entities
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com")
        assert len(options) == 2
        # BeautifulSoup should decode HTML entities
        assert options[0]["description"] == "Description with & entities \"quoted\" and 'apostrophes'"
        # The underscore replacement might change the name
        assert "programs.firefox.profiles" in options[1]["name"]
        assert "search" in options[1]["name"]

    def test_nixos_search_invalid_parameters(self):
        """Test nixos_search with various invalid parameters."""
        # Invalid type
        result = nixos_search("test", search_type="invalid")
        assert "Error (ERROR): Invalid type 'invalid'" in result

        # Invalid channel
        result = nixos_search("test", channel="nonexistent")
        assert "Error (ERROR): Invalid channel 'nonexistent'" in result

        # Invalid limit (too low)
        result = nixos_search("test", limit=0)
        assert "Error (ERROR): Limit must be 1-100" in result

        # Invalid limit (too high)
        result = nixos_search("test", limit=101)
        assert "Error (ERROR): Limit must be 1-100" in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_with_empty_query(self, mock_es_query):
        """Test searching with empty query string."""
        mock_es_query.return_value = []

        result = nixos_search("")
        assert "No packages found matching ''" in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_programs_edge_case(self, mock_es_query):
        """Test programs search when program name doesn't match query."""
        mock_es_query.return_value = [
            {"_source": {"package_pname": "coreutils", "package_programs": ["ls", "cp", "mv", "rm"]}}
        ]

        # Search for 'ls' should find it in programs
        result = nixos_search("ls", search_type="programs")
        assert "ls (provided by coreutils)" in result

        # Search for 'grep' should not show coreutils
        result = nixos_search("grep", search_type="programs")
        assert "coreutils" not in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_with_missing_fields(self, mock_es_query):
        """Test nixos_info when response has missing fields."""
        # Package with minimal fields
        mock_es_query.return_value = [
            {
                "_source": {
                    "package_pname": "minimal-pkg"
                    # Missing version, description, homepage, license
                }
            }
        ]

        result = nixos_info("minimal-pkg", type="package")
        assert "Package: minimal-pkg" in result
        assert "Version: " in result  # Empty version
        # Should not crash on missing fields

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_html_stripping(self, mock_es_query):
        """Test HTML stripping in option descriptions."""
        mock_es_query.return_value = [
            {
                "_source": {
                    "option_name": "test.option",
                    "option_type": "boolean",
                    "option_description": (
                        "<rendered-html><p>This is a <strong>test</strong> "
                        "option with <a href='#'>links</a></p></rendered-html>"
                    ),
                    "option_default": "false",
                }
            }
        ]

        result = nixos_info("test.option", type="option")
        assert "Description: This is a test option with links" in result
        assert "<" not in result  # No HTML tags
        assert ">" not in result

    @patch("requests.post")
    def test_nixos_stats_partial_failure(self, mock_post):
        """Test nixos_stats when one count request fails."""
        # First call succeeds
        mock_resp1 = Mock()
        mock_resp1.json = Mock(return_value={"count": 100000})

        # Second call fails
        mock_resp2 = Mock()
        mock_resp2.json = Mock(side_effect=ValueError("Invalid JSON"))

        mock_post.side_effect = [mock_resp1, mock_resp2]

        result = nixos_stats()
        # With improved error handling, it should show 0 for failed count
        assert "Options: 0" in result or "Error (ERROR):" in result

    def test_home_manager_search_edge_cases(self):
        """Test home_manager_search with edge cases."""
        # Invalid limit
        result = home_manager_search("test", limit=0)
        assert "Error (ERROR): Limit must be 1-100" in result

        result = home_manager_search("test", limit=101)
        assert "Error (ERROR): Limit must be 1-100" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_info_exact_match(self, mock_parse):
        """Test home_manager_info requires exact name match."""
        mock_parse.return_value = [
            {"name": "programs.git", "description": "Git program", "type": ""},
            {"name": "programs.git.enable", "description": "Enable git", "type": "boolean"},
        ]

        # Should find exact match
        result = home_manager_info("programs.git.enable")
        assert "Option: programs.git.enable" in result
        assert "Enable git" in result

        # Should not find partial match
        result = home_manager_info("programs.git.en")
        assert "Error (NOT_FOUND):" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_list_options_category_extraction(self, mock_parse):
        """Test category extraction from option names."""
        mock_parse.return_value = [
            {"name": "programs.git.enable", "description": "", "type": ""},
            {"name": "programs.firefox.enable", "description": "", "type": ""},
            {"name": "services.gpg-agent.enable", "description": "", "type": ""},
            {"name": "xdg.configHome", "description": "", "type": ""},
            {"name": "single", "description": "No category", "type": ""},  # Edge case: no dot
        ]

        result = home_manager_list_options()
        assert "programs (2 options)" in result
        assert "services (1 options)" in result
        assert "xdg (1 options)" in result
        assert "single (1 options)" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_options_by_prefix_sorting(self, mock_parse):
        """Test darwin_options_by_prefix sorts results."""
        mock_parse.return_value = [
            {"name": "system.defaults.c", "description": "Option C", "type": ""},
            {"name": "system.defaults.a", "description": "Option A", "type": ""},
            {"name": "system.defaults.b", "description": "Option B", "type": ""},
        ]

        result = darwin_options_by_prefix("system.defaults")
        lines = result.split("\n")

        # Find option lines (those starting with •)
        option_lines = [line for line in lines if line.startswith("•")]
        assert option_lines[0] == "• system.defaults.a"
        assert option_lines[1] == "• system.defaults.b"
        assert option_lines[2] == "• system.defaults.c"

    def test_all_tools_handle_exceptions_gracefully(self):
        """Test that all tools handle exceptions and return error messages."""
        with patch("requests.post", side_effect=Exception("Network error")):
            result = nixos_search("test")
            assert "Error (ERROR):" in result

            result = nixos_info("test")
            assert "Error (ERROR):" in result

            result = nixos_stats()
            assert "Error (ERROR):" in result

        with patch("requests.get", side_effect=Exception("Network error")):
            result = home_manager_search("test")
            assert "Error (ERROR):" in result

            result = home_manager_info("test")
            assert "Error (ERROR):" in result

            result = home_manager_list_options()
            assert "Error (ERROR):" in result

            result = darwin_search("test")
            assert "Error (ERROR):" in result

            result = darwin_info("test")
            assert "Error (ERROR):" in result

            result = darwin_list_options()
            assert "Error (ERROR):" in result
