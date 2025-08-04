"""Test suite for plain text output validation."""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos import server
from mcp_nixos.server import error


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
darwin_search = get_tool_function("darwin_search")
hm_show = get_tool_function("hm_show")
hm_options = get_tool_function("hm_options")
hm_search = get_tool_function("hm_search")
hm_stats = get_tool_function("hm_stats")
show = get_tool_function("show")
search = get_tool_function("search")
stats = get_tool_function("stats")


@pytest.fixture(autouse=True)
def mock_channel_cache():
    """Mock channel cache to avoid API calls during tests."""
    with patch("mcp_nixos.server.channel_cache") as mock_cache:
        # Mock the channel cache methods
        mock_cache.get_resolved.return_value = {
            "unstable": "latest-43-nixos-unstable",
            "stable": "latest-43-nixos-25.05",
            "25.05": "latest-43-nixos-25.05",
            "24.11": "latest-43-nixos-24.11",
        }
        mock_cache.get_available.return_value = {
            "latest-43-nixos-unstable": 150000,
            "latest-43-nixos-25.05": 140000,
            "latest-43-nixos-24.11": 130000,
        }
        yield mock_cache


class TestPlainTextOutput:
    """Validate all functions return plain text, not XML."""

    def test_error_plain_text(self):
        """Test error returns plain text."""
        result = error("Test message")
        assert result == "Error (ERROR): Test message"
        assert "<error>" not in result

    def test_error_with_code_plain_text(self):
        """Test error with code returns plain text."""
        result = error("Not found", "NOT_FOUND")
        assert result == "Error (NOT_FOUND): Not found"
        assert "<error>" not in result

    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_search_plain_text(self, mock_post):
        """Test search returns plain text."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "firefox",
                            "package_pversion": "123.0",
                            "package_description": "A web browser",
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = await search("firefox", search_type="packages", limit=5)
        assert "SEARCH: packages" in result
        assert "Results: 1 packages found" in result
        assert "• firefox (123.0)" in result
        assert "   A web browser" in result
        # Check no XML tags (but allow placeholders like <package>)
        lines = result.split("\n")
        for line in lines:
            # Skip lines with allowed placeholders
            if any(placeholder in line for placeholder in ["<package>", "<command>", "<tool>"]):
                continue
            # Check for any other XML-like tags
            assert "<" not in line or ">" not in line

    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_show_plain_text(self, mock_post):
        """Test show returns plain text."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "firefox",
                            "package_pversion": "123.0",
                            "package_description": "A web browser",
                            "package_homepage": ["https://firefox.com"],
                            "package_license_set": ["MPL-2.0"],
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = await show("firefox", type="package")
        assert "Name: firefox" in result
        assert "Version: 123.0" in result
        assert "Description: A web browser" in result
        assert "Homepage: https://firefox.com" in result
        assert "License: MPL-2.0" in result
        assert "<package_info>" not in result

    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_stats_plain_text(self, mock_post):
        """Test stats returns plain text."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"count": 12345}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = await stats()
        assert "STATS: unstable" in result
        assert "• Packages: 12,345" in result
        assert "• Options: 12,345" in result
        assert "<nixos_stats>" not in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_hm_search_plain_text(self, mock_get):
        """Test hm_search returns plain text."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>programs.git.enable</dt>
            <dd>
                <p>Enable git</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = await hm_search("git", limit=5)
        assert "Found 1 Home Manager options matching 'git':" in result
        assert "• programs.git.enable" in result
        assert "  Type: boolean" in result
        assert "  Enable git" in result
        assert "<option>" not in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_hm_show_plain_text(self, mock_get):
        """Test hm_show returns plain text."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>programs.git.enable</dt>
            <dd>
                <p>Enable git</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = await hm_show("programs.git.enable")
        assert "Option: programs.git.enable" in result
        assert "Type: boolean" in result
        assert "Description: Enable git" in result
        assert "<option_info>" not in result

    @patch("mcp_nixos.server.parse_html_options")
    @pytest.mark.asyncio
    async def test_hm_stats_plain_text(self, mock_parse):
        """Test hm_stats returns plain text."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg-agent.enable", "type": "boolean", "description": "Enable GPG agent"},
            {"name": "home.packages", "type": "list", "description": "Packages to install"},
            {"name": "wayland.windowManager.sway.enable", "type": "boolean", "description": "Enable Sway"},
            {"name": "xsession.enable", "type": "boolean", "description": "Enable X session"},
        ]

        result = await hm_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
        assert "programs:" in result
        assert "services:" in result
        assert "<home_manager_stats>" not in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_hm_options_plain_text(self, mock_get):
        """Test hm_options returns plain text."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>programs.git.enable</dt>
            <dd><p>Enable git</p></dd>
            <dt>services.ssh.enable</dt>
            <dd><p>Enable SSH</p></dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = await hm_options()
        assert "Home Manager option categories (2 total):" in result
        assert "• programs (1 options)" in result
        assert "• services (1 options)" in result
        assert "<option_categories>" not in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_darwin_search_plain_text(self, mock_get):
        """Test darwin_search returns plain text."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>system.defaults.dock.autohide</dt>
            <dd>
                <p>Auto-hide the dock</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = await darwin_search("dock", limit=5)
        assert "Found 1 nix-darwin options matching 'dock':" in result
        assert "• system.defaults.dock.autohide" in result
        assert "  Type: boolean" in result
        assert "  Auto-hide the dock" in result
        assert "<option>" not in result

    @patch("mcp_nixos.server.requests.get")
    @pytest.mark.asyncio
    async def test_no_results_plain_text(self, mock_get):
        """Test empty results return appropriate plain text."""
        # Mock empty HTML response
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = await hm_search("nonexistent", limit=5)
        assert result == "No Home Manager options found matching 'nonexistent'"
        assert "<" not in result

    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_nixos_empty_search_plain_text(self, mock_post):
        """Test search with no results returns plain text."""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = await search("nonexistent", search_type="packages")
        assert "Error (NOT_FOUND): No packages found matching 'nonexistent'" in result
        assert "Try:" in result
        # Check no XML tags (but allow placeholders like <package>)
        lines = result.split("\n")
        for line in lines:
            # Skip lines with allowed placeholders
            if any(placeholder in line for placeholder in ["<package>", "<command>", "<tool>"]):
                continue
            # Check for any other XML-like tags
            assert "<" not in line or ">" not in line
