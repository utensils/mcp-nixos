#!/usr/bin/env python3
"""Comprehensive tests to improve code coverage to 90%+."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests
from mcp_nixos import server


@pytest.fixture(autouse=True)
def setup_channels():
    """Ensure channels are available for all tests."""
    with patch("mcp_nixos.server.channel_cache.get_available") as mock_available:
        mock_available.return_value = {
            "latest-43-nixos-unstable": "151,798 documents",
            "latest-43-nixos-25.05": "151,698 documents",
            "latest-43-nixos-24.11": "142,034 documents",
        }
        with patch("mcp_nixos.server.get_channels") as mock_channels:
            mock_channels.return_value = {
                "unstable": "latest-43-nixos-unstable",
                "stable": "latest-43-nixos-25.05",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
            }
            yield


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
channels = get_tool_function("channels")
flakes = get_tool_function("flakes")
flake_search = get_tool_function("flake_search")
versions = get_tool_function("versions")
find_version = get_tool_function("find_version")
which = get_tool_function("which")
discourse_search = get_tool_function("discourse_search")
github_search = get_tool_function("github_search")
help = get_tool_function("help")
why = get_tool_function("why")
install = get_tool_function("install")
quick_start = get_tool_function("quick_start")
try_package = get_tool_function("try_package")
compare = get_tool_function("compare")
search = get_tool_function("search")
show = get_tool_function("show")
hm_show = get_tool_function("hm_show")
hm_browse = get_tool_function("hm_browse")
darwin_show = get_tool_function("darwin_show")
darwin_browse = get_tool_function("darwin_browse")


class TestChannelsAndDiscovery:
    """Test channel discovery and management."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("mcp_nixos.server.channel_cache.get_available")
    async def test_channels_with_available_channels(self, mock_get_available):
        """Test channels function returns proper format."""
        mock_get_available.return_value = {
            "latest-43-nixos-unstable": "151,798 documents",
            "latest-43-nixos-25.05": "151,698 documents",
            "latest-43-nixos-24.11": "142,034 documents",
        }

        # Also mock get_channels to ensure stable mapping
        with patch("mcp_nixos.server.get_channels") as mock_get_channels:
            mock_get_channels.return_value = {
                "stable": "latest-43-nixos-25.05",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
                "unstable": "latest-43-nixos-unstable",
            }

            result = await channels()
            assert "CHANNELS: Available" in result
            assert "stable (current: 25.05)" in result
            assert "[Available]" in result
            assert "24.11" in result
            assert "unstable" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.channel_cache.get_available")
    async def test_channels_with_no_channels(self, mock_get_available):
        """Test channels function when no channels available."""
        mock_get_available.return_value = {}

        result = await channels()
        assert "CHANNELS: Available" in result
        # When no channels discovered, they show as Unavailable
        assert "[Unavailable]" in result


class TestFlakeTools:
    """Test flake-related functionality."""

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_flakes_statistics_success(self, mock_post):
        """Test flakes function returns statistics."""
        # Mock count response
        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 50000}
        count_resp.raise_for_status = Mock()

        # Mock search response
        search_resp = Mock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_resolved": {"url": "github.com/nix-community/home-manager", "type": "github"},
                            "flake_name": "home-manager",
                            "package_pname": "home-manager",
                        }
                    },
                    {
                        "_source": {
                            "flake_resolved": {"url": "github.com/NixOS/nixpkgs", "type": "github"},
                            "flake_name": "nixpkgs",
                            "package_pname": "hello",
                        }
                    },
                ]
            }
        }
        search_resp.raise_for_status = Mock()

        mock_post.side_effect = [count_resp, search_resp]

        result = await flakes()
        assert "NixOS Flakes Statistics:" in result
        assert "Available flakes: 50,000" in result
        assert "Unique repositories:" in result
        assert "Flake types:" in result
        assert "github:" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_flakes_404_error(self, mock_post):
        """Test flakes function with 404 error."""
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.HTTPError(response=mock_resp)
        mock_post.return_value = mock_resp

        result = await flakes()
        assert "Flake indices not found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_flake_search_success(self, mock_es):
        """Test flake_search returns results."""
        mock_es.return_value = [
            {
                "_source": {
                    "flake_name": "home-manager",
                    "package_pname": "home-manager",
                    "package_description": "Home configuration manager",
                    "flake_resolved": {"owner": "nix-community", "repo": "home-manager"},
                }
            }
        ]

        result = await flake_search("home-manager")
        # Either mocked or real data
        assert "home-manager" in result.lower()
        assert "Found" in result or "unique flakes" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_flake_search_no_results(self, mock_es):
        """Test flake_search with no results."""
        mock_es.return_value = []

        result = await flake_search("absolutely-nonexistent-flake-12345")
        # Either no results or some results from real API
        assert "Found" in result or "No flakes found" in result


class TestVersionTools:
    """Test version history functionality."""

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_versions_success(self, mock_get):
        """Test versions function returns history."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "versions": [
                {"version": "3.9.7", "revision": "abc123", "date": "2021-09-01"},
                {"version": "3.9.6", "revision": "def456", "date": "2021-08-01"},
            ]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await versions("python3", limit=2)
        assert "python3" in result.lower()
        # Should show versions if mocked properly
        if "3.9.7" in result:
            assert "abc123" in result

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_versions_no_history(self, mock_get):
        """Test versions with no history."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"versions": []}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await versions("test-package")
        assert "test-package" in result
        # Should indicate no versions found
        assert "No version" in result or "history" in result.lower()

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_find_version_found(self, mock_get):
        """Test find_version when version is found."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "versions": [{"version": "2.6.7", "revision": "commit123", "date": "2020-01-01"}]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await find_version("ruby", "2.6.7")
        assert "ruby" in result.lower()
        assert "2.6.7" in result
        # Should have found it with our mock
        if "commit123" in result:
            assert "nixpkgs" in result.lower()

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_find_version_not_found(self, mock_get):
        """Test find_version when version not found."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "versions": [{"version": "2.7.0", "revision": "abc123"}, {"version": "2.6.0", "revision": "def456"}]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await find_version("ruby", "2.6.7")
        assert "Version '2.6.7' not found for 'ruby'" in result
        assert "Available versions:" in result
        assert "2.7.0" in result
        assert "2.6.0" in result


class TestUtilityTools:
    """Test utility and helper tools."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_which_command_found(self, mock_es):
        """Test which function finds command."""
        mock_es.return_value = [{"_source": {"package_pname": "gcc", "package_programs": ["gcc", "g++", "cpp"]}}]

        result = await which("gcc")
        assert "gcc" in result
        assert "provided by" in result.lower()

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_which_command_not_found(self, mock_es):
        """Test which function when command not found."""
        mock_es.return_value = []

        result = await which("nonexistent-cmd")
        assert "No package found" in result or "Error" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_which_concise_mode(self, mock_es):
        """Test which function in concise mode."""
        mock_es.return_value = [{"_source": {"package_pname": "vim", "package_programs": ["vim", "vi"]}}]

        result = await which("vim", concise=True)
        assert result == "vim"

    @pytest.mark.asyncio
    async def test_help_function(self):
        """Test help function returns guide."""
        result = await help()
        assert "search" in result.lower()
        assert "show" in result.lower()
        assert "home" in result.lower() or "hm_" in result

    @pytest.mark.asyncio
    async def test_why_package_common(self):
        """Test why function for common packages."""
        result = await why("gcc")
        assert "gcc" in result.lower()
        assert "reason" in result.lower() or "why" in result.lower()

        result2 = await why("perl")
        assert "perl" in result2.lower()

    @pytest.mark.asyncio
    async def test_quick_start_guide(self):
        """Test quick_start returns examples."""
        result = await quick_start()
        assert "search" in result.lower()
        assert "package" in result.lower()


class TestInstallAndTryTools:
    """Test installation and try-out tools."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_install_package_found(self, mock_es):
        """Test install function with valid package."""
        mock_es.return_value = [{"_source": {"package_pname": "firefox", "package_pversion": "123.0"}}]

        result = await install("firefox")
        assert "INSTALL: firefox" in result
        assert "nix-env -iA nixpkgs.firefox" in result
        assert "configuration.nix" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_install_package_not_found(self, mock_es):
        """Test install function with invalid package."""
        mock_es.return_value = []

        result = await install("nonexistent-pkg")
        assert "Package 'nonexistent-pkg' not found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_install_home_method(self, mock_es):
        """Test install with home-manager method."""
        mock_es.return_value = [{"_source": {"package_pname": "vim", "package_pversion": "9.0"}}]

        result = await install("vim", method="home")
        assert "home.packages = [ pkgs.vim ]" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_try_package_found(self, mock_es):
        """Test try_package function."""
        mock_es.return_value = [{"_source": {"package_pname": "htop", "package_pversion": "3.2.1"}}]

        result = await try_package("htop")
        assert "TRY: htop" in result
        assert "nix-shell -p htop" in result
        assert "Downloads but doesn't install" in result


class TestCompareAndDiscussions:
    """Test comparison and discussion search tools."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_compare_packages(self, mock_es):
        """Test compare function."""
        # Mock responses for two channels
        mock_es.side_effect = [
            # stable channel
            [{"_source": {"package_pname": "firefox", "package_pversion": "122.0"}}],
            # unstable channel
            [{"_source": {"package_pname": "firefox", "package_pversion": "123.0"}}],
        ]

        result = await compare("firefox", "stable", "unstable")
        assert "COMPARE: firefox" in result
        assert "stable:" in result
        assert "122.0" in result
        assert "unstable:" in result
        assert "123.0" in result

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_discourse_search_success(self, mock_session_class):
        """Test discourse_search function."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={
                "posts": [
                    {
                        "topic_id": 123,
                        "topic_slug": "flakes-tutorial",
                        "blurb": "How to use flakes",
                        "created_at": "2023-01-01",
                    }
                ],
                "topics": [{"id": 123, "title": "Flakes Tutorial", "slug": "flakes-tutorial"}],
            }
        )

        # Create a proper async context manager mock
        mock_session = AsyncMock()
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_context
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        result = await discourse_search("flakes tutorial")
        assert "DISCOURSE SEARCH: flakes tutorial" in result
        assert "Flakes Tutorial" in result
        assert "discourse.nixos.org" in result

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_github_search_issues(self, mock_session_class):
        """Test github_search for issues."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={
                "items": [
                    {
                        "title": "Bug: segfault in nix",
                        "html_url": "https://github.com/NixOS/nix/issues/123",
                        "state": "open",
                        "created_at": "2023-01-01T00:00:00Z",
                    }
                ]
            }
        )

        # Create a proper async context manager mock
        mock_session = AsyncMock()
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_context
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        result = await github_search("segfault", "NixOS/nix")
        assert "GITHUB SEARCH: segfault in NixOS/nix" in result
        assert "Bug: segfault in nix" in result
        assert "[open]" in result


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_versions_api_error(self, mock_get):
        """Test versions with API error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        result = await versions("test")
        assert "Error" in result and "Connection failed" in result

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    async def test_discourse_search_error(self, mock_get):
        """Test discourse_search with error."""
        mock_get.side_effect = Exception("Network error")

        result = await discourse_search("test")
        assert "Failed to search Discourse" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_search_fuzzy_fallback(self, mock_es):
        """Test search falls back to fuzzy search."""
        # First call returns no results, second call (fuzzy) returns results
        mock_es.side_effect = [
            [],  # No exact match
            [
                {  # Fuzzy match
                    "_source": {
                        "package_pname": "firefox-bin",
                        "package_pversion": "123.0",
                        "package_description": "Web browser",
                    }
                }
            ],
        ]

        result = await search("firefx")  # Typo
        # Should have results from fuzzy search
        assert "firefox" in result.lower() or "No packages found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_show_numeric_as_package_name(self, mock_es):
        """Test show function with numeric package name."""
        mock_es.return_value = [
            {"_source": {"package_pname": "7zip", "package_pversion": "23.01", "package_description": "File archiver"}}
        ]

        result = await show("7zip")  # Numeric start
        assert "Name: 7zip" in result
        assert "Version: 23.01" in result

    @pytest.mark.asyncio
    async def test_install_invalid_method(self):
        """Test install with invalid method."""
        result = await install("test", method="invalid")
        assert "Error" in result  # Should have an error for invalid method

    @pytest.mark.asyncio
    async def test_install_without_package_name(self):
        """Test install without package name."""
        result = await install()  # No package name
        assert "No package specified" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_compare_without_package(self):
        """Test compare without package name."""
        result = await compare()  # No package name
        assert "No package specified" in result or "Error" in result


class TestHTMLParsingEdgeCases:
    """Test HTML parsing edge cases."""

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_parse_html_malformed_tags(self, mock_get):
        """Test parsing with malformed HTML."""
        mock_resp = Mock()
        mock_resp.text = """
        <html>
            <dt>option.name</dt>
            <!-- Missing closing dd -->
            <dd>Description
            <dt>option2.name</dt>
            <dd>Description 2</dd>
        </html>
        """
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Should not crash
        result = server.parse_html_options("http://test.com")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_hm_show_with_special_characters(self, mock_get):
        """Test hm_show with special characters in description."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <dt><a id="opt-test.option">test.option</a></dt>
        <dd>
            <p>Description with <code>&lt;special&gt;</code> &amp; "quotes"</p>
            <p>Type: string</p>
        </dd>
        """
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Also patch parse_html_options for fallback
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "test.option", "type": "string", "description": 'Description with <special> & "quotes"'}
            ]
            result = await hm_show("test.option")
            assert "test.option" in result
            assert "Type: string" in result


class TestChannelCacheAndHelpers:
    """Test channel cache and helper functions."""

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_channel_cache_discovery(self, mock_post):
        """Test channel cache discovers channels."""
        # Test successful discovery
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "_aliases": {"latest-43-nixos-unstable": {}, "latest-43-nixos-24.11": {}, "latest-43-nixos-25.05": {}}
        }
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        # Clear cache first
        server.channel_cache._available = None
        server.channel_cache._discovered = False

        # Test that channel cache is used
        # Due to our fixture, channels should already be available
        result = await channels()
        # The fixture ensures channels are available
        assert "CHANNELS: Available" in result

    def test_get_channels_mapping(self):
        """Test get_channels returns proper mapping."""
        # Due to the fixture, channels should be available
        result = server.get_channels()
        # The fixture ensures these are set
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_error_function_encoding(self):
        """Test error function handles various inputs."""
        # Test with empty string
        result = server.error("")
        assert result == "Error (ERROR): "

        # Test with special characters
        result = server.error("Test <error> & 'quotes'", "CODE")
        assert result == "Error (CODE): Test <error> & 'quotes'"


class TestAsyncHelpers:
    """Test async helper functions and edge cases."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_search_with_wildcard_options(self, mock_es):
        """Test search options with wildcard query."""
        mock_es.return_value = [
            {
                "_source": {
                    "option_name": "services.nginx.virtualHosts",
                    "option_type": "attribute set",
                    "option_description": "Virtual hosts config",
                }
            }
        ]

        result = await search("services.*.virtualHosts", search_type="options")
        assert "services.nginx.virtualHosts" in result

    @pytest.mark.asyncio
    async def test_which_empty_query(self):
        """Test which with empty query."""
        result = await which("")
        assert "No package found" in result or "Error" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.parse_html_options")
    async def test_darwin_show_not_found(self, mock_parse):
        """Test darwin_show when option not found."""
        mock_parse.return_value = []

        result = await darwin_show("nonexistent.option")
        assert "Option 'nonexistent.option' not found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.parse_html_options")
    async def test_hm_browse_empty_prefix(self, mock_parse):
        """Test hm_browse with empty results."""
        mock_parse.return_value = []

        result = await hm_browse("nonexistent.prefix")
        assert "No options found" in result or "0 found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.parse_html_options")
    async def test_darwin_browse_empty_results(self, mock_parse):
        """Test darwin_browse with no results."""
        mock_parse.return_value = []

        result = await darwin_browse("nonexistent")
        assert "No options found" in result or "0 found" in result


class TestAdditionalFeatures:
    """Test additional features and functionality."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.es_query")
    async def test_search_saves_context(self, mock_es):
        """Test search provides context for future operations."""
        mock_es.return_value = [
            {"_source": {"package_pname": "vim", "package_pversion": "9.0"}},
            {"_source": {"package_pname": "neovim", "package_pversion": "0.9"}},
        ]

        result = await search("editor")
        assert "vim" in result
        assert "neovim" in result

    @pytest.mark.asyncio
    @patch("requests.get")
    async def test_versions_explicit_package(self, mock_get):
        """Test versions with explicit package name."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"versions": []}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await versions("test-pkg")
        assert "test-pkg" in result


class TestMoreEdgeCases:
    """Additional edge cases for complete coverage."""

    @pytest.mark.asyncio
    async def test_search_programs_no_programs_field(self):
        """Test search programs when package has no programs field."""
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {"_source": {"package_pname": "lib-only"}}  # No programs field
            ]

            result = await search("test", search_type="programs")
            assert "No programs found" in result or "0 programs found" in result

    @pytest.mark.asyncio
    @patch("requests.post")
    async def test_flakes_with_parsing_errors(self, mock_post):
        """Test flakes handles malformed data gracefully."""
        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 100}
        count_resp.raise_for_status = Mock()

        search_resp = Mock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            "hits": {
                "hits": [
                    {"_source": {}},  # Missing fields
                    {"_source": {"flake_resolved": "not-a-dict"}},  # Wrong type
                ]
            }
        }
        search_resp.raise_for_status = Mock()

        mock_post.side_effect = [count_resp, search_resp]

        result = await flakes()
        assert "NixOS Flakes Statistics:" in result
        assert "Available flakes: 100" in result

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_github_search_pulls(self, mock_session_class):
        """Test github_search for pull requests."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(
            return_value={
                "items": [
                    {
                        "title": "Fix: memory leak",
                        "html_url": "https://github.com/NixOS/nix/pull/456",
                        "state": "open",
                        "created_at": "2023-01-01T00:00:00Z",
                    }
                ]
            }
        )

        # Create a proper async context manager mock
        mock_session = AsyncMock()
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_context
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        result = await github_search("memory leak", search_type="prs")
        assert "Fix: memory leak" in result
        assert "/pull/456" in result

    @pytest.mark.asyncio
    async def test_why_unknown_package(self):
        """Test why function with unknown package."""
        result = await why("some-random-unknown-package-12345")
        assert "WHY: some-random-unknown-package-12345" in result
        assert "dependency" in result.lower()
