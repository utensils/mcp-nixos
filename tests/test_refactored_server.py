"""Tests for the refactored MCP-NixOS server."""

import pytest
from unittest.mock import patch, Mock
import xml.etree.ElementTree as ET
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_list_options,
    darwin_search,
    error,
    es_query,
    parse_html_options,
)


class TestErrorFormatting:
    def test_error_formatting(self):
        """Test error XML formatting."""
        result = error("Test error", "TEST_CODE")
        assert "<error>" in result
        assert "<code>TEST_CODE</code>" in result
        assert "<message>Test error</message>" in result

    def test_error_escaping(self):
        """Test XML escaping in errors."""
        result = error("Error with <>&", "CODE")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result


class TestNixOSTools:
    @patch("mcp_nixos.server.requests.post")
    def test_nixos_search_packages(self, mock_post):
        """Test searching for NixOS packages."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package": {
                                "pname": "firefox",
                                "version": "120.0",
                                "description": "Mozilla Firefox browser",
                            }
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_search("firefox", type="packages")

        # Parse XML result
        root = ET.fromstring(result)
        assert root.tag == "package_search"
        assert root.find(".//query").text == "firefox"
        assert root.find(".//package/name").text == "firefox"
        assert root.find(".//package/version").text == "120.0"

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_search_invalid_type(self, mock_post):
        """Test error handling for invalid search type."""
        result = nixos_search("test", type="invalid")
        assert "<error>" in result
        assert "Invalid type" in result

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_info_package(self, mock_post):
        """Test getting package info."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package": {
                                "pname": "git",
                                "version": "2.43.0",
                                "description": "Distributed version control system",
                                "homepage": "https://git-scm.com",
                                "license": "GPLv2",
                            }
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_info("git", type="package")

        root = ET.fromstring(result)
        assert root.tag == "package_info"
        assert root.find(".//name").text == "git"
        assert root.find(".//version").text == "2.43.0"
        assert root.find(".//homepage").text == "https://git-scm.com"

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats(self, mock_post):
        """Test getting NixOS statistics."""
        # Mock package count response
        pkg_response = Mock()
        pkg_response.json.return_value = {"count": 80000}

        # Mock option count response
        opt_response = Mock()
        opt_response.json.return_value = {"count": 15000}

        mock_post.side_effect = [pkg_response, opt_response]

        result = nixos_stats()

        root = ET.fromstring(result)
        assert root.tag == "nixos_stats"
        assert root.find(".//packages").text == "80000"
        assert root.find(".//options").text == "15000"


class TestHomeManagerTools:
    @patch("mcp_nixos.server.requests.get")
    def test_home_manager_search(self, mock_get):
        """Test searching Home Manager options."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">programs.git.enable</dt>
            <dd>
                <p>Enable git</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_response

        result = home_manager_search("git")

        root = ET.fromstring(result)
        assert root.tag == "option_search"
        assert root.find(".//option/name").text == "programs.git.enable"
        assert root.find(".//option/type").text == "boolean"

    @patch("mcp_nixos.server.requests.get")
    def test_home_manager_list_options(self, mock_get):
        """Test listing Home Manager categories."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">programs.git.enable</dt>
            <dd></dd>
            <dt class="option">programs.zsh.enable</dt>
            <dd></dd>
            <dt class="option">services.gpg-agent.enable</dt>
            <dd></dd>
        </html>
        """
        mock_get.return_value = mock_response

        result = home_manager_list_options()

        root = ET.fromstring(result)
        assert root.tag == "option_categories"
        categories = root.findall(".//category")
        assert len(categories) == 2  # programs and services

        # Check category counts
        for cat in categories:
            name = cat.find("name").text
            count = int(cat.find("count").text)
            if name == "programs":
                assert count == 2
            elif name == "services":
                assert count == 1


class TestDarwinTools:
    @patch("mcp_nixos.server.requests.get")
    def test_darwin_search(self, mock_get):
        """Test searching nix-darwin options."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">system.defaults.dock.autohide</dt>
            <dd>
                <p>Auto-hide the dock</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_response

        result = darwin_search("dock")

        root = ET.fromstring(result)
        assert root.tag == "option_search"
        assert root.find(".//option/name").text == "system.defaults.dock.autohide"
        assert "dock" in root.find(".//option/description").text.lower()


class TestHelperFunctions:
    @patch("mcp_nixos.server.requests.post")
    def test_es_query_success(self, mock_post):
        """Test successful Elasticsearch query."""
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": [{"_source": {"test": "data"}}]}}
        mock_post.return_value = mock_response

        result = es_query("test-index", {"match_all": {}})
        assert len(result) == 1
        assert result[0]["_source"]["test"] == "data"

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_error(self, mock_post):
        """Test Elasticsearch query error handling."""
        mock_post.side_effect = Exception("Connection error")

        with pytest.raises(Exception) as exc_info:
            es_query("test-index", {"match_all": {}})
        assert "API error" in str(exc_info.value)

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options(self, mock_get):
        """Test HTML option parsing."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">test.option.one</dt>
            <dd>
                <p>First option</p>
                <span class="term">Type: string</span>
            </dd>
            <dt class="option">test.option.two</dt>
            <dd>
                <p>Second option</p>
                <span class="term">Type: integer</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_response

        # Test query filtering
        options = parse_html_options("http://test.com", query="one")
        assert len(options) == 1
        assert options[0]["name"] == "test.option.one"

        # Test prefix filtering
        options = parse_html_options("http://test.com", prefix="test.option")
        assert len(options) == 2

        # Test limit
        options = parse_html_options("http://test.com", limit=1)
        assert len(options) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
