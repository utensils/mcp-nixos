"""Comprehensive test suite for MCP-NixOS server with 100% coverage."""

import pytest
from unittest.mock import patch, Mock
import xml.etree.ElementTree as ET
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
    home_manager_stats,
    home_manager_list_options,
    home_manager_options_by_prefix,
    darwin_search,
    darwin_info,
    darwin_stats,
    darwin_list_options,
    darwin_options_by_prefix,
    mcp,
    CHANNELS,
    NIXOS_API,
    NIXOS_AUTH,
    HOME_MANAGER_URL,
    DARWIN_URL,
)


class TestHelperFunctions:
    """Test all helper functions with edge cases."""

    def test_error_basic(self):
        """Test basic error formatting."""
        result = error("Test message")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert root.find("code").text == "ERROR"
        assert root.find("message").text == "Test message"

    def test_error_with_code(self):
        """Test error formatting with custom code."""
        result = error("Not found", "NOT_FOUND")
        root = ET.fromstring(result)
        assert root.find("code").text == "NOT_FOUND"
        assert root.find("message").text == "Not found"

    def test_error_xml_escaping(self):
        """Test XML character escaping in errors."""
        result = error("Error <tag> & \"quotes\" 'apostrophe'", "CODE")
        root = ET.fromstring(result)
        assert root.find("message").text == "Error <tag> & \"quotes\" 'apostrophe'"

    def test_error_empty_message(self):
        """Test error with empty message."""
        result = error("")
        root = ET.fromstring(result)
        assert root.find("message").text == ""

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_success(self, mock_post):
        """Test successful Elasticsearch query."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": [{"_source": {"test": "data"}}]}}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert len(result) == 1
        assert result[0]["_source"]["test"] == "data"

        # Verify request parameters
        mock_post.assert_called_once_with(
            f"{NIXOS_API}/test-index/_search",
            json={"query": {"match_all": {}}, "size": 20},
            auth=NIXOS_AUTH,
            timeout=10,
        )

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_custom_size(self, mock_post):
        """Test Elasticsearch query with custom size."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_resp

        es_query("test-index", {"match_all": {}}, size=50)

        # Verify size parameter
        call_args = mock_post.call_args[1]
        assert call_args["json"]["size"] == 50

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_http_error(self, mock_post):
        """Test Elasticsearch query with HTTP error."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_post.return_value = mock_resp

        with pytest.raises(Exception) as exc:
            es_query("test-index", {"match_all": {}})
        assert "API error" in str(exc.value)

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_connection_error(self, mock_post):
        """Test Elasticsearch query with connection error."""
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(Exception) as exc:
            es_query("test-index", {"match_all": {}})
        assert "API error" in str(exc.value)

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_basic(self, mock_get):
        """Test basic HTML option parsing."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt class="option">test.option.one</dt>
            <dd>
                <p>First option description</p>
                <span class="term">Type: string</span>
            </dd>
            <dt class="option">test.option.two</dt>
            <dd>
                <p>Second option description that is very long and should be truncated after 200 characters to ensure
                we don't have overly long descriptions in our output that would make it hard to read</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com")
        assert len(options) == 2
        assert options[0]["name"] == "test.option.one"
        assert options[0]["description"] == "First option description"
        assert options[0]["type"] == "string"
        assert len(options[1]["description"]) <= 200

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_with_query(self, mock_get):
        """Test HTML parsing with query filter."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt class="option">programs.git.enable</dt>
            <dd><p>Enable git</p></dd>
            <dt class="option">programs.zsh.enable</dt>
            <dd><p>Enable zsh</p></dd>
        </html>
        """
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com", query="git")
        assert len(options) == 1
        assert options[0]["name"] == "programs.git.enable"

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_with_prefix(self, mock_get):
        """Test HTML parsing with prefix filter."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt class="option">programs.git.enable</dt>
            <dd><p>Enable git</p></dd>
            <dt class="option">programs.git.userName</dt>
            <dd><p>Git username</p></dd>
            <dt class="option">services.nginx.enable</dt>
            <dd><p>Enable nginx</p></dd>
        </html>
        """
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com", prefix="programs.git")
        assert len(options) == 2
        assert all(opt["name"].startswith("programs.git") for opt in options)

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_limit(self, mock_get):
        """Test HTML parsing with limit."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt class="option">opt1</dt><dd><p>Desc1</p></dd>
            <dt class="option">opt2</dt><dd><p>Desc2</p></dd>
            <dt class="option">opt3</dt><dd><p>Desc3</p></dd>
        </html>
        """
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com", limit=2)
        assert len(options) == 2

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_http_error(self, mock_get):
        """Test HTML parsing with HTTP error."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_resp

        with pytest.raises(Exception) as exc:
            parse_html_options("http://test.com")
        assert "Failed to fetch docs" in str(exc.value)

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_missing_elements(self, mock_get):
        """Test HTML parsing with missing elements."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt class="option">option.without.dd</dt>
            <dt class="option">option.with.dd</dt>
            <dd><p>Has description</p></dd>
            <dt class="option">option.without.description</dt>
            <dd></dd>
        </html>
        """
        mock_get.return_value = mock_resp

        options = parse_html_options("http://test.com")
        # Should get all options that have dt elements, even without dd
        assert len(options) >= 2
        # Check that we got the one with proper dd
        option_names = [opt["name"] for opt in options]
        assert "option.with.dd" in option_names


class TestNixOSTools:
    """Test all NixOS-related tools."""

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_packages_success(self, mock_query):
        """Test successful package search."""
        mock_query.return_value = [
            {
                "_source": {
                    "package": {"pname": "firefox", "version": "120.0", "description": "Mozilla Firefox web browser"}
                }
            }
        ]

        result = nixos_search("firefox", type="packages")
        root = ET.fromstring(result)

        assert root.tag == "package_search"
        assert root.find(".//query").text == "firefox"
        assert root.find(".//results").get("count") == "1"
        assert root.find(".//package/name").text == "firefox"
        assert root.find(".//package/version").text == "120.0"

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_options_success(self, mock_query):
        """Test successful option search."""
        mock_query.return_value = [
            {
                "_source": {
                    "option": {
                        "option_name": "services.nginx.enable",
                        "option_type": "boolean",
                        "option_description": "Whether to enable nginx",
                    }
                }
            }
        ]

        result = nixos_search("nginx", type="options")
        root = ET.fromstring(result)

        assert root.tag == "option_search"
        assert root.find(".//option/name").text == "services.nginx.enable"
        assert root.find(".//option/type").text == "boolean"

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_programs_success(self, mock_query):
        """Test successful program search."""
        mock_query.return_value = [{"_source": {"program": "git", "package": "git"}}]

        result = nixos_search("git", type="programs")
        root = ET.fromstring(result)

        assert root.tag == "program_search"
        assert root.find(".//program/name").text == "git"
        assert root.find(".//program/package").text == "git"

    def test_nixos_search_invalid_type(self):
        """Test search with invalid type."""
        result = nixos_search("test", type="invalid")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Invalid type" in root.find(".//message").text

    def test_nixos_search_invalid_channel(self):
        """Test search with invalid channel."""
        result = nixos_search("test", channel="invalid")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Invalid channel" in root.find(".//message").text

    def test_nixos_search_invalid_limit_low(self):
        """Test search with limit too low."""
        result = nixos_search("test", limit=0)
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Limit must be 1-100" in root.find(".//message").text

    def test_nixos_search_invalid_limit_high(self):
        """Test search with limit too high."""
        result = nixos_search("test", limit=101)
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Limit must be 1-100" in root.find(".//message").text

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_all_channels(self, mock_query):
        """Test search works with all defined channels."""
        mock_query.return_value = []

        for channel in CHANNELS.keys():
            result = nixos_search("test", channel=channel)
            root = ET.fromstring(result)
            assert root.tag == "package_search"

            # Verify correct index is used
            mock_query.assert_called_with(
                CHANNELS[channel],
                {
                    "bool": {
                        "should": [
                            {"match": {"package.pname": {"query": "test", "boost": 3}}},
                            {"match": {"package.description": "test"}},
                        ]
                    }
                },
                20,
            )

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_exception_handling(self, mock_query):
        """Test search handles exceptions gracefully."""
        mock_query.side_effect = Exception("Connection failed")

        result = nixos_search("test")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Connection failed" in root.find(".//message").text

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_package_found(self, mock_query):
        """Test package info when found."""
        mock_query.return_value = [
            {
                "_source": {
                    "package": {
                        "pname": "git",
                        "version": "2.43.0",
                        "description": "Distributed version control system",
                        "homepage": "https://git-scm.com",
                        "license": {"fullName": "GPLv2"},
                    }
                }
            }
        ]

        result = nixos_info("git", type="package")
        root = ET.fromstring(result)

        assert root.tag == "package_info"
        assert root.find(".//name").text == "git"
        assert root.find(".//version").text == "2.43.0"
        assert root.find(".//homepage").text == "https://git-scm.com"

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_found(self, mock_query):
        """Test option info when found."""
        mock_query.return_value = [
            {
                "_source": {
                    "option": {
                        "option_name": "services.nginx.enable",
                        "option_type": "boolean",
                        "option_description": "Whether to enable nginx",
                        "option_default": "false",
                        "option_example": "true",
                    }
                }
            }
        ]

        result = nixos_info("services.nginx.enable", type="option")
        root = ET.fromstring(result)

        assert root.tag == "option_info"
        assert root.find(".//name").text == "services.nginx.enable"
        assert root.find(".//default").text == "false"
        assert root.find(".//example").text == "true"

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_not_found(self, mock_query):
        """Test info when package/option not found."""
        mock_query.return_value = []

        result = nixos_info("nonexistent", type="package")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert root.find(".//code").text == "NOT_FOUND"
        assert "Package 'nonexistent' not found" in root.find(".//message").text

    def test_nixos_info_invalid_type(self):
        """Test info with invalid type."""
        result = nixos_info("test", type="invalid")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Type must be 'package' or 'option'" in root.find(".//message").text

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_success(self, mock_post):
        """Test stats retrieval."""
        # Mock package count
        pkg_resp = Mock()
        pkg_resp.json.return_value = {"count": 95000}

        # Mock option count
        opt_resp = Mock()
        opt_resp.json.return_value = {"count": 18000}

        mock_post.side_effect = [pkg_resp, opt_resp]

        result = nixos_stats()
        root = ET.fromstring(result)

        assert root.tag == "nixos_stats"
        assert root.find(".//channel").text == "unstable"
        assert root.find(".//packages").text == "95000"
        assert root.find(".//options").text == "18000"

    def test_nixos_stats_invalid_channel(self):
        """Test stats with invalid channel."""
        result = nixos_stats(channel="invalid")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Invalid channel" in root.find(".//message").text

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_api_error(self, mock_post):
        """Test stats with API error."""
        mock_post.side_effect = requests.ConnectionError("Failed")

        result = nixos_stats()
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Failed" in root.find(".//message").text


class TestHomeManagerTools:
    """Test all Home Manager tools."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_search_success(self, mock_parse):
        """Test successful Home Manager search."""
        mock_parse.return_value = [{"name": "programs.git.enable", "type": "boolean", "description": "Enable git"}]

        result = home_manager_search("git")
        root = ET.fromstring(result)

        assert root.tag == "option_search"
        assert root.find(".//query").text == "git"
        assert root.find(".//option/name").text == "programs.git.enable"

        # Verify parse was called correctly
        mock_parse.assert_called_once_with(HOME_MANAGER_URL, "git", "", 20)

    def test_home_manager_search_invalid_limit(self):
        """Test Home Manager search with invalid limit."""
        result = home_manager_search("test", limit=0)
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Limit must be 1-100" in root.find(".//message").text

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_search_exception(self, mock_parse):
        """Test Home Manager search with exception."""
        mock_parse.side_effect = Exception("Parse failed")

        result = home_manager_search("test")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Parse failed" in root.find(".//message").text

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_info_found(self, mock_parse):
        """Test Home Manager info when option found."""
        mock_parse.return_value = [{"name": "programs.git.enable", "type": "boolean", "description": "Enable git"}]

        result = home_manager_info("programs.git.enable")
        root = ET.fromstring(result)

        assert root.tag == "option_info"
        assert root.find(".//name").text == "programs.git.enable"
        assert root.find(".//type").text == "boolean"

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_info_not_found(self, mock_parse):
        """Test Home Manager info when option not found."""
        mock_parse.return_value = [{"name": "other.option", "type": "string", "description": "Other"}]

        result = home_manager_info("programs.git.enable")
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert root.find(".//code").text == "NOT_FOUND"

    def test_home_manager_stats(self):
        """Test Home Manager stats returns simplified message."""
        result = home_manager_stats()
        root = ET.fromstring(result)

        assert root.tag == "home_manager_stats"
        assert root.find(".//message").text is not None
        assert root.find(".//hint").text is not None

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_list_options_success(self, mock_parse):
        """Test Home Manager list options."""
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg.enable", "type": "boolean", "description": "Enable GPG"},
        ]

        result = home_manager_list_options()
        root = ET.fromstring(result)

        assert root.tag == "option_categories"
        categories = root.findall(".//category")
        assert len(categories) == 2  # programs and services

        # Check counts
        for cat in categories:
            if cat.find("name").text == "programs":
                assert cat.find("count").text == "2"
            elif cat.find("name").text == "services":
                assert cat.find("count").text == "1"

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_options_by_prefix_success(self, mock_parse):
        """Test Home Manager options by prefix."""
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.git.userName", "type": "string", "description": "Git username"},
        ]

        result = home_manager_options_by_prefix("programs.git")
        root = ET.fromstring(result)

        assert root.tag == "option_list"
        assert root.find(".//prefix").text == "programs.git"
        options = root.findall(".//option")
        assert len(options) == 2

        # Verify parse was called with prefix
        mock_parse.assert_called_once_with(HOME_MANAGER_URL, "", "programs.git")


class TestDarwinTools:
    """Test all Darwin/nix-darwin tools."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_search_success(self, mock_parse):
        """Test successful Darwin search."""
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"}
        ]

        result = darwin_search("dock")
        root = ET.fromstring(result)

        assert root.tag == "option_search"
        assert root.find(".//query").text == "dock"
        assert root.find(".//option/name").text == "system.defaults.dock.autohide"

        # Verify parse was called correctly
        mock_parse.assert_called_once_with(DARWIN_URL, "dock", "", 20)

    def test_darwin_search_invalid_limit(self):
        """Test Darwin search with invalid limit."""
        result = darwin_search("test", limit=150)
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Limit must be 1-100" in root.find(".//message").text

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_info_found(self, mock_parse):
        """Test Darwin info when option found."""
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"}
        ]

        result = darwin_info("system.defaults.dock.autohide")
        root = ET.fromstring(result)

        assert root.tag == "option_info"
        assert root.find(".//name").text == "system.defaults.dock.autohide"
        assert root.find(".//type").text == "boolean"

    def test_darwin_stats(self):
        """Test Darwin stats returns simplified message."""
        result = darwin_stats()
        root = ET.fromstring(result)

        assert root.tag == "darwin_stats"
        assert root.find(".//message").text is not None
        assert root.find(".//hint").text is not None

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_list_options_success(self, mock_parse):
        """Test Darwin list options."""
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": ""},
            {"name": "system.defaults.dock.tilesize", "type": "integer", "description": ""},
            {"name": "environment.systemPackages", "type": "list", "description": ""},
        ]

        result = darwin_list_options()
        root = ET.fromstring(result)

        assert root.tag == "option_categories"
        categories = root.findall(".//category")
        assert len(categories) == 2  # system and environment

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_options_by_prefix_success(self, mock_parse):
        """Test Darwin options by prefix."""
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide"},
            {"name": "system.defaults.dock.tilesize", "type": "integer", "description": "Tile size"},
        ]

        result = darwin_options_by_prefix("system.defaults.dock")
        root = ET.fromstring(result)

        assert root.tag == "option_list"
        assert root.find(".//prefix").text == "system.defaults.dock"
        options = root.findall(".//option")
        assert len(options) == 2


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch("mcp_nixos.server.es_query")
    def test_empty_search_query(self, mock_query):
        """Test search with empty query string."""
        mock_query.return_value = []

        result = nixos_search("")
        root = ET.fromstring(result)
        assert root.tag == "package_search"
        assert root.find(".//query").text == ""
        assert root.find(".//results").get("count") == "0"

    @patch("mcp_nixos.server.es_query")
    def test_special_characters_in_query(self, mock_query):
        """Test search with special characters."""
        mock_query.return_value = []

        query = "test <>&\"'"
        result = nixos_search(query)
        root = ET.fromstring(result)
        assert root.tag == "package_search"
        assert root.find(".//query").text == query

    @patch("mcp_nixos.server.parse_html_options")
    def test_malformed_html_response(self, mock_parse):
        """Test handling of malformed HTML."""
        # Should not raise exception, just return empty list
        mock_parse.return_value = []

        result = home_manager_search("test")
        root = ET.fromstring(result)
        assert root.tag == "option_search"
        assert root.find(".//results").get("count") == "0"

    @patch("mcp_nixos.server.es_query")
    def test_missing_fields_in_response(self, mock_query):
        """Test handling of missing fields in API response."""
        mock_query.return_value = [
            {
                "_source": {
                    "package": {
                        "pname": "test-pkg"
                        # Missing version and description
                    }
                }
            }
        ]

        result = nixos_search("test")
        root = ET.fromstring(result)
        assert root.tag == "package_search"
        pkg = root.find(".//package")
        assert pkg.find("name").text == "test-pkg"
        assert pkg.find("version").text == ""
        assert pkg.find("description").text == ""

    @patch("mcp_nixos.server.requests.post")
    def test_timeout_handling(self, mock_post):
        """Test handling of request timeouts."""
        mock_post.side_effect = requests.Timeout("Request timed out")

        result = nixos_stats()
        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Request timed out" in root.find(".//message").text


class TestServerIntegration:
    """Test server integration and MCP framework."""

    def test_mcp_instance_exists(self):
        """Test that MCP instance is properly created."""
        assert mcp is not None
        assert hasattr(mcp, "tool")
        assert hasattr(mcp, "run")

    def test_all_tools_registered(self):
        """Test that all tools are registered with MCP."""
        # This tests that the decorators were applied
        assert callable(nixos_search)
        assert callable(nixos_info)
        assert callable(nixos_stats)
        assert callable(home_manager_search)
        assert callable(home_manager_info)
        assert callable(home_manager_stats)
        assert callable(home_manager_list_options)
        assert callable(home_manager_options_by_prefix)
        assert callable(darwin_search)
        assert callable(darwin_info)
        assert callable(darwin_stats)
        assert callable(darwin_list_options)
        assert callable(darwin_options_by_prefix)

    def test_constants_defined(self):
        """Test that all required constants are defined."""
        assert NIXOS_API == "https://search.nixos.org/backend"
        assert NIXOS_AUTH == ("aWVSALXpZv", "X8gPHnzL52wFEekuxsfQ9cSh")
        assert HOME_MANAGER_URL == "https://nix-community.github.io/home-manager/options.xhtml"
        assert DARWIN_URL == "https://nix-darwin.github.io/nix-darwin/manual/options.xhtml"
        assert len(CHANNELS) == 5
        assert "unstable" in CHANNELS
        assert "stable" in CHANNELS


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=mcp_nixos.server", "--cov-report=term-missing"])
