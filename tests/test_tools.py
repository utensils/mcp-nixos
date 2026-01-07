"""Tests for the nix and nix_versions MCP tools.

IMPORTANT: This test file should ONLY test the MCP tools directly.
- Do NOT run bash commands or shell operations
- Do NOT interact with the filesystem beyond what the tools do internally
- Do NOT spawn subprocesses or external commands
- ONLY call the nix_fn and nix_versions_fn functions to test tool behavior

These tests verify:
- Input validation and error handling
- Correct response formatting (plain text, no XML/JSON leakage)
- API interaction through the tool interfaces
- Edge cases and boundary conditions
"""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos.server import nix, nix_versions

# Get underlying functions from MCP tool wrappers
nix_fn = nix.fn
nix_versions_fn = nix_versions.fn


class TestNixToolValidation:
    """Test input validation for the nix tool."""

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        result = await nix_fn(action="invalid")
        assert "Error" in result
        assert "search|info|stats|options|channels" in result

    @pytest.mark.asyncio
    async def test_search_requires_query(self):
        result = await nix_fn(action="search", query="")
        assert "Error" in result
        assert "Query required" in result

    @pytest.mark.asyncio
    async def test_info_requires_query(self):
        result = await nix_fn(action="info", query="")
        assert "Error" in result
        assert "Name required" in result

    @pytest.mark.asyncio
    async def test_invalid_source(self):
        result = await nix_fn(action="search", query="test", source="invalid")
        assert "Error" in result
        assert "nixos|home-manager|darwin|flakes|flakehub|nixvim" in result

    @pytest.mark.asyncio
    async def test_options_only_for_hm_darwin_nixvim(self):
        result = await nix_fn(action="options", source="nixos")
        assert "Error" in result
        assert "home-manager|darwin|nixvim" in result

    @pytest.mark.asyncio
    async def test_limit_too_low(self):
        result = await nix_fn(action="search", query="test", limit=0)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_negative(self):
        result = await nix_fn(action="search", query="test", limit=-1)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_too_high(self):
        result = await nix_fn(action="search", query="test", limit=101)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_at_minimum_boundary(self):
        """Verify limit=1 is valid (doesn't return error)."""
        # This will fail at the search step (no mock), but should NOT fail limit validation
        result = await nix_fn(action="search", query="", limit=1)
        assert "1-100" not in result  # Should not be a limit error

    @pytest.mark.asyncio
    async def test_limit_at_maximum_boundary(self):
        """Verify limit=100 is valid (doesn't return error)."""
        # This will fail at the search step (no mock), but should NOT fail limit validation
        result = await nix_fn(action="search", query="", limit=100)
        assert "1-100" not in result  # Should not be a limit error


class TestNixToolSearch:
    """Test nix tool search action."""

    @patch("mcp_nixos.server._search_nixos")
    @pytest.mark.asyncio
    async def test_search_nixos_packages(self, mock_search):
        mock_search.return_value = "Found 3 packages"
        result = await nix_fn(action="search", query="firefox", source="nixos", type="packages")
        assert result == "Found 3 packages"
        mock_search.assert_called_once_with("firefox", "packages", 20, "unstable")

    @patch("mcp_nixos.server._search_nixos")
    @pytest.mark.asyncio
    async def test_search_nixos_options(self, mock_search):
        mock_search.return_value = "Found 2 options"
        result = await nix_fn(action="search", query="nginx", source="nixos", type="options")
        assert result == "Found 2 options"

    @patch("mcp_nixos.server._search_home_manager")
    @pytest.mark.asyncio
    async def test_search_home_manager(self, mock_search):
        mock_search.return_value = "Found git options"
        result = await nix_fn(action="search", query="git", source="home-manager")
        assert result == "Found git options"
        mock_search.assert_called_once_with("git", 20)

    @patch("mcp_nixos.server._search_darwin")
    @pytest.mark.asyncio
    async def test_search_darwin(self, mock_search):
        mock_search.return_value = "Found darwin options"
        result = await nix_fn(action="search", query="dock", source="darwin")
        assert result == "Found darwin options"
        mock_search.assert_called_once_with("dock", 20)

    @patch("mcp_nixos.server._search_flakes")
    @pytest.mark.asyncio
    async def test_search_flakes(self, mock_search):
        mock_search.return_value = "Found flakes"
        result = await nix_fn(action="search", query="neovim", source="flakes")
        assert result == "Found flakes"
        mock_search.assert_called_once_with("neovim", 20)

    @patch("mcp_nixos.server._search_flakehub")
    @pytest.mark.asyncio
    async def test_search_flakehub(self, mock_search):
        mock_search.return_value = "Found FlakeHub flakes"
        result = await nix_fn(action="search", query="nixpkgs", source="flakehub")
        assert result == "Found FlakeHub flakes"
        mock_search.assert_called_once_with("nixpkgs", 20)


class TestNixToolInfo:
    """Test nix tool info action."""

    @patch("mcp_nixos.server._info_nixos")
    @pytest.mark.asyncio
    async def test_info_nixos_package(self, mock_info):
        mock_info.return_value = "Package: firefox"
        result = await nix_fn(action="info", query="firefox", source="nixos", type="package")
        assert result == "Package: firefox"
        mock_info.assert_called_once_with("firefox", "package", "unstable")

    @patch("mcp_nixos.server._info_nixos")
    @pytest.mark.asyncio
    async def test_info_nixos_option(self, mock_info):
        mock_info.return_value = "Option: services.nginx.enable"
        result = await nix_fn(
            action="info",
            query="services.nginx.enable",
            source="nixos",
            type="option",
        )
        assert result == "Option: services.nginx.enable"
        mock_info.assert_called_once_with("services.nginx.enable", "option", "unstable")

    @patch("mcp_nixos.server._info_home_manager")
    @pytest.mark.asyncio
    async def test_info_home_manager(self, mock_info):
        mock_info.return_value = "Option: programs.git.enable"
        result = await nix_fn(action="info", query="programs.git.enable", source="home-manager")
        assert result == "Option: programs.git.enable"
        mock_info.assert_called_once_with("programs.git.enable")

    @patch("mcp_nixos.server._info_darwin")
    @pytest.mark.asyncio
    async def test_info_darwin(self, mock_info):
        mock_info.return_value = "Option: system.defaults.dock.autohide"
        result = await nix_fn(action="info", query="system.defaults.dock.autohide", source="darwin")
        assert result == "Option: system.defaults.dock.autohide"
        mock_info.assert_called_once_with("system.defaults.dock.autohide")

    @patch("mcp_nixos.server._info_flakehub")
    @pytest.mark.asyncio
    async def test_info_flakehub(self, mock_info):
        mock_info.return_value = "FlakeHub Flake: NixOS/nixpkgs"
        result = await nix_fn(action="info", query="NixOS/nixpkgs", source="flakehub")
        assert result == "FlakeHub Flake: NixOS/nixpkgs"
        mock_info.assert_called_once_with("NixOS/nixpkgs")


class TestNixToolStats:
    """Test nix tool stats action."""

    @patch("mcp_nixos.server._stats_nixos")
    @pytest.mark.asyncio
    async def test_stats_nixos(self, mock_stats):
        mock_stats.return_value = "NixOS Statistics"
        result = await nix_fn(action="stats", source="nixos")
        assert result == "NixOS Statistics"
        mock_stats.assert_called_once_with("unstable")

    @patch("mcp_nixos.server._stats_home_manager")
    @pytest.mark.asyncio
    async def test_stats_home_manager(self, mock_stats):
        mock_stats.return_value = "Home Manager Statistics"
        result = await nix_fn(action="stats", source="home-manager")
        assert result == "Home Manager Statistics"

    @patch("mcp_nixos.server._stats_darwin")
    @pytest.mark.asyncio
    async def test_stats_darwin(self, mock_stats):
        mock_stats.return_value = "Darwin Statistics"
        result = await nix_fn(action="stats", source="darwin")
        assert result == "Darwin Statistics"

    @patch("mcp_nixos.server._stats_flakes")
    @pytest.mark.asyncio
    async def test_stats_flakes(self, mock_stats):
        mock_stats.return_value = "Flakes Statistics"
        result = await nix_fn(action="stats", source="flakes")
        assert result == "Flakes Statistics"

    @patch("mcp_nixos.server._stats_flakehub")
    @pytest.mark.asyncio
    async def test_stats_flakehub(self, mock_stats):
        mock_stats.return_value = "FlakeHub Statistics"
        result = await nix_fn(action="stats", source="flakehub")
        assert result == "FlakeHub Statistics"


class TestNixToolOptions:
    """Test nix tool options action."""

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_home_manager(self, mock_browse):
        mock_browse.return_value = "Home Manager categories"
        result = await nix_fn(action="options", source="home-manager", query="")
        assert result == "Home Manager categories"
        mock_browse.assert_called_once_with("home-manager", "")

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_darwin(self, mock_browse):
        mock_browse.return_value = "Darwin categories"
        result = await nix_fn(action="options", source="darwin", query="")
        assert result == "Darwin categories"
        mock_browse.assert_called_once_with("darwin", "")

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_with_prefix(self, mock_browse):
        mock_browse.return_value = "Options with prefix"
        result = await nix_fn(action="options", source="home-manager", query="programs.git")
        assert result == "Options with prefix"
        mock_browse.assert_called_once_with("home-manager", "programs.git")


class TestNixToolChannels:
    """Test nix tool channels action."""

    @patch("mcp_nixos.server._list_channels")
    @pytest.mark.asyncio
    async def test_list_channels(self, mock_list):
        mock_list.return_value = "Available channels"
        result = await nix_fn(action="channels")
        assert result == "Available channels"
        mock_list.assert_called_once()


class TestNixVersionsValidation:
    """Test input validation for nix_versions tool."""

    @pytest.mark.asyncio
    async def test_empty_package(self):
        result = await nix_versions_fn(package="")
        assert "Error" in result
        assert "Package name required" in result

    @pytest.mark.asyncio
    async def test_whitespace_package(self):
        result = await nix_versions_fn(package="   ")
        assert "Error" in result
        assert "Package name required" in result

    @pytest.mark.asyncio
    async def test_invalid_package_name(self):
        result = await nix_versions_fn(package="invalid<>package")
        assert "Error" in result
        assert "Invalid package name" in result

    @pytest.mark.asyncio
    async def test_limit_too_low(self):
        result = await nix_versions_fn(package="python", limit=0)
        assert "Error" in result
        assert "1-50" in result

    @pytest.mark.asyncio
    async def test_limit_too_high(self):
        result = await nix_versions_fn(package="python", limit=100)
        assert "Error" in result
        assert "1-50" in result


class TestNixVersionsAPI:
    """Test nix_versions API interactions."""

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "releases": [
                {
                    "version": "3.12.0",
                    "platforms": [{"commit_hash": "abc123def456", "attribute_path": "python312"}],
                },
                {"version": "3.11.0", "platforms": []},
            ]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        assert "Package: python" in result
        assert "3.12.0" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_find_specific_version(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "releases": [
                {
                    "version": "3.12.0",
                    "platforms": [{"commit_hash": "a" * 40, "attribute_path": "python312"}],
                },
            ]
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python", version="3.12.0")
        assert "Found python version 3.12.0" in result
        assert "commit" in result.lower()

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_version_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"releases": [{"version": "3.12.0", "platforms": []}]}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python", version="2.7.0")
        assert "not found" in result.lower()
        assert "3.12.0" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_package_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="nonexistent-package-xyz")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_service_error(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "SERVICE_ERROR" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_timeout(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout()

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_network_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "NETWORK_ERROR" in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_no_releases(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"releases": []}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        assert "No version history" in result


class TestNixvimSearch:
    """Test nix tool search action for Nixvim source."""

    @patch("mcp_nixos.server._search_nixvim")
    @pytest.mark.asyncio
    async def test_search_nixvim(self, mock_search):
        mock_search.return_value = "Found telescope options"
        result = await nix_fn(action="search", query="telescope", source="nixvim")
        assert result == "Found telescope options"
        mock_search.assert_called_once_with("telescope", 20)

    @patch("mcp_nixos.server._search_nixvim")
    @pytest.mark.asyncio
    async def test_search_nixvim_with_limit(self, mock_search):
        mock_search.return_value = "Found 5 options"
        result = await nix_fn(action="search", query="lsp", source="nixvim", limit=5)
        assert result == "Found 5 options"
        mock_search.assert_called_once_with("lsp", 5)


class TestNixvimInfo:
    """Test nix tool info action for Nixvim source."""

    @patch("mcp_nixos.server._info_nixvim")
    @pytest.mark.asyncio
    async def test_info_nixvim(self, mock_info):
        mock_info.return_value = "Nixvim Option: plugins.telescope.enable"
        result = await nix_fn(action="info", query="plugins.telescope.enable", source="nixvim")
        assert result == "Nixvim Option: plugins.telescope.enable"
        mock_info.assert_called_once_with("plugins.telescope.enable")


class TestNixvimStats:
    """Test nix tool stats action for Nixvim source."""

    @patch("mcp_nixos.server._stats_nixvim")
    @pytest.mark.asyncio
    async def test_stats_nixvim(self, mock_stats):
        mock_stats.return_value = "Nixvim Statistics:\n* Total options: 5,000"
        result = await nix_fn(action="stats", source="nixvim")
        assert result == "Nixvim Statistics:\n* Total options: 5,000"
        mock_stats.assert_called_once()


class TestNixvimOptions:
    """Test nix tool options action for Nixvim source."""

    @patch("mcp_nixos.server._browse_nixvim_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_categories(self, mock_browse):
        mock_browse.return_value = "Nixvim option categories"
        result = await nix_fn(action="options", source="nixvim", query="")
        assert result == "Nixvim option categories"
        mock_browse.assert_called_once_with("")

    @patch("mcp_nixos.server._browse_nixvim_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_with_prefix(self, mock_browse):
        mock_browse.return_value = "Nixvim options with prefix 'plugins'"
        result = await nix_fn(action="options", source="nixvim", query="plugins")
        assert result == "Nixvim options with prefix 'plugins'"
        mock_browse.assert_called_once_with("plugins")


@pytest.mark.unit
class TestNixvimInternalFunctions:
    """Test Nixvim internal functions with mocked data."""

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_search_nixvim_finds_matches(self, mock_get_options):
        from mcp_nixos.server import _search_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": "Telescope settings"},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": "Enable LSP"},
        ]
        result = _search_nixvim("telescope", 10)
        assert "Found 2 Nixvim options" in result
        assert "plugins.telescope.enable" in result
        assert "plugins.telescope.settings" in result
        assert "plugins.lsp.enable" not in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_search_nixvim_no_matches(self, mock_get_options):
        from mcp_nixos.server import _search_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
        ]
        result = _search_nixvim("nonexistent", 10)
        assert "No Nixvim options found" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_info_nixvim_exact_match(self, mock_get_options):
        from mcp_nixos.server import _info_nixvim

        mock_get_options.return_value = [
            {
                "name": "plugins.telescope.enable",
                "type": "boolean",
                "description": "<p>Enable telescope</p>",
                "default": "<code>false</code>",
                "declarations": ["https://github.com/nix-community/nixvim/blob/main/plugins/telescope.nix"],
            },
        ]
        result = _info_nixvim("plugins.telescope.enable")
        assert "Nixvim Option: plugins.telescope.enable" in result
        assert "Type: boolean" in result
        assert "Enable telescope" in result
        assert "Default: false" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_info_nixvim_not_found(self, mock_get_options):
        from mcp_nixos.server import _info_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
        ]
        result = _info_nixvim("nonexistent.option")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_stats_nixvim(self, mock_get_options):
        from mcp_nixos.server import _stats_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": ""},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": ""},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": ""},
            {"name": "colorschemes.catppuccin.enable", "type": "boolean", "description": ""},
        ]
        result = _stats_nixvim()
        assert "Nixvim Statistics:" in result
        assert "Total options: 4" in result
        assert "Categories: 2" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_categories(self, mock_get_options):
        from mcp_nixos.server import _browse_nixvim_options

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": ""},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": ""},
            {"name": "colorschemes.catppuccin.enable", "type": "boolean", "description": ""},
        ]
        result = _browse_nixvim_options("")
        assert "Nixvim option categories" in result
        assert "plugins (2 options)" in result
        assert "colorschemes (1 options)" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_with_prefix(self, mock_get_options):
        from mcp_nixos.server import _browse_nixvim_options

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": "Settings"},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": "Enable LSP"},
        ]
        result = _browse_nixvim_options("plugins.telescope")
        assert "Nixvim options with prefix 'plugins.telescope'" in result
        assert "plugins.telescope.enable" in result
        assert "plugins.telescope.settings" in result
        assert "plugins.lsp.enable" not in result


@pytest.mark.unit
class TestFlakeHubInternalFunctions:
    """Test FlakeHub internal functions with mocked API responses."""

    @patch("mcp_nixos.server.requests.get")
    def test_search_flakehub_success(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {
                "org": "NixOS",
                "project": "nixpkgs",
                "description": "A collection of packages",
                "labels": ["nixpkgs", "nix"],
            },
            {
                "org": "nix-community",
                "project": "home-manager",
                "description": "Manage user environment",
                "labels": ["home-manager"],
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("nix", 10)
        assert "Found 2 flakes on FlakeHub" in result
        assert "NixOS/nixpkgs" in result
        assert "nix-community/home-manager" in result
        assert "flakehub.com/flake/NixOS/nixpkgs" in result

    @patch("mcp_nixos.server.requests.get")
    def test_search_flakehub_no_results(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("nonexistent", 10)
        assert "No flakes found on FlakeHub" in result

    @patch("mcp_nixos.server.requests.get")
    def test_search_flakehub_normalizes_whitespace(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {
                "org": "test",
                "project": "flake",
                "description": "  Description\n\twith\n  whitespace  ",
                "labels": [],
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("test", 10)
        assert "Description with whitespace" in result
        assert "\n\t" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_search_flakehub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _search_flakehub

        mock_get.side_effect = requests.Timeout()

        result = _search_flakehub("test", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.server.requests.get")
    def test_info_flakehub_success(self, mock_get):
        from mcp_nixos.server import _info_flakehub

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "description": "A collection of packages",
            "simplified_version": "0.2511.123456",
            "revision": "abc123def456",
            "commit_count": 900000,
            "visibility": "public",
            "published_at": "2025-01-01T12:00:00Z",
            "mirrored": True,
            "pretty_download_url": "https://flakehub.com/f/NixOS/nixpkgs/0.2511.123456.tar.gz",
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_flakehub("NixOS/nixpkgs")
        assert "FlakeHub Flake: NixOS/nixpkgs" in result
        assert "A collection of packages" in result
        assert "0.2511.123456" in result
        assert "public" in result

    @patch("mcp_nixos.server.requests.get")
    def test_info_flakehub_not_found(self, mock_get):
        from mcp_nixos.server import _info_flakehub

        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = _info_flakehub("nonexistent/flake")
        assert "Error" in result
        assert "NOT_FOUND" in result

    def test_info_flakehub_invalid_format(self):
        from mcp_nixos.server import _info_flakehub

        result = _info_flakehub("invalid-no-slash")
        assert "Error" in result
        assert "org/project" in result

    @patch("mcp_nixos.server.requests.get")
    def test_stats_flakehub_success(self, mock_get):
        from mcp_nixos.server import _stats_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {"org": "NixOS", "project": "nixpkgs", "labels": ["nix", "nixos"]},
            {"org": "NixOS", "project": "nix", "labels": ["nix"]},
            {"org": "nix-community", "project": "home-manager", "labels": ["nix"]},
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _stats_flakehub()
        assert "FlakeHub Statistics:" in result
        assert "Total flakes: 3" in result
        assert "Organizations: 2" in result
        assert "NixOS" in result

    @patch("mcp_nixos.server.requests.get")
    def test_stats_flakehub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _stats_flakehub

        mock_get.side_effect = requests.Timeout()

        result = _stats_flakehub()
        assert "Error" in result
        assert "TIMEOUT" in result


@pytest.mark.unit
class TestStripHtml:
    """Test HTML stripping utility."""

    def test_strip_html_basic(self):
        from mcp_nixos.server import strip_html

        assert strip_html("<p>Hello world</p>") == "Hello world"

    def test_strip_html_nested(self):
        from mcp_nixos.server import strip_html

        assert strip_html("<p><code>foo</code> bar</p>") == "foo bar"

    def test_strip_html_empty(self):
        from mcp_nixos.server import strip_html

        assert strip_html("") == ""
        assert strip_html(None) == ""

    def test_strip_html_spans(self):
        from mcp_nixos.server import strip_html

        html = '<span class="code">value</span>'
        assert strip_html(html) == "value"


@pytest.mark.unit
class TestPlainTextOutput:
    """Verify MCP tools return plain text."""

    @pytest.mark.asyncio
    async def test_nix_error_no_xml(self):
        result = await nix_fn(action="invalid")
        assert "<error>" not in result
        assert "</error>" not in result

    @pytest.mark.asyncio
    async def test_nix_versions_error_no_xml(self):
        result = await nix_versions_fn(package="")
        assert "<error>" not in result
        assert "</error>" not in result
