"""Test suite for plain text output validation."""

from unittest.mock import patch, Mock

from mcp_nixos.server import (
    error,
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_info,
    home_manager_stats,
    home_manager_list_options,
    darwin_search,
)


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
    def test_nixos_search_plain_text(self, mock_post):
        """Test nixos_search returns plain text."""
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

        result = nixos_search("firefox", search_type="packages", limit=5)
        assert "Found 1 packages matching 'firefox':" in result
        assert "• firefox (123.0)" in result
        assert "  A web browser" in result
        assert "<package>" not in result
        assert "<name>" not in result

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_info_plain_text(self, mock_post):
        """Test nixos_info returns plain text."""
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

        result = nixos_info("firefox", type="package")
        assert "Package: firefox" in result
        assert "Version: 123.0" in result
        assert "Description: A web browser" in result
        assert "Homepage: https://firefox.com" in result
        assert "License: MPL-2.0" in result
        assert "<package_info>" not in result

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_plain_text(self, mock_post):
        """Test nixos_stats returns plain text."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"count": 12345}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = nixos_stats()
        assert "NixOS Statistics for unstable channel:" in result
        assert "• Packages: 12,345" in result
        assert "• Options: 12,345" in result
        assert "<nixos_stats>" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_home_manager_search_plain_text(self, mock_get):
        """Test home_manager_search returns plain text."""
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

        result = home_manager_search("git", limit=5)
        assert "Found 1 Home Manager options matching 'git':" in result
        assert "• programs.git.enable" in result
        assert "  Type: boolean" in result
        assert "  Enable git" in result
        assert "<option>" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_home_manager_info_plain_text(self, mock_get):
        """Test home_manager_info returns plain text."""
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

        result = home_manager_info("programs.git.enable")
        assert "Option: programs.git.enable" in result
        assert "Type: boolean" in result
        assert "Description: Enable git" in result
        assert "<option_info>" not in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_stats_plain_text(self, mock_parse):
        """Test home_manager_stats returns plain text."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg-agent.enable", "type": "boolean", "description": "Enable GPG agent"},
            {"name": "home.packages", "type": "list", "description": "Packages to install"},
            {"name": "wayland.windowManager.sway.enable", "type": "boolean", "description": "Enable Sway"},
            {"name": "xsession.enable", "type": "boolean", "description": "Enable X session"},
        ]

        result = home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
        assert "programs:" in result
        assert "services:" in result
        assert "<home_manager_stats>" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_home_manager_list_options_plain_text(self, mock_get):
        """Test home_manager_list_options returns plain text."""
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

        result = home_manager_list_options()
        assert "Home Manager option categories (2 total):" in result
        assert "• programs (1 options)" in result
        assert "• services (1 options)" in result
        assert "<option_categories>" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_darwin_search_plain_text(self, mock_get):
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

        result = darwin_search("dock", limit=5)
        assert "Found 1 nix-darwin options matching 'dock':" in result
        assert "• system.defaults.dock.autohide" in result
        assert "  Type: boolean" in result
        assert "  Auto-hide the dock" in result
        assert "<option>" not in result

    @patch("mcp_nixos.server.requests.get")
    def test_no_results_plain_text(self, mock_get):
        """Test empty results return appropriate plain text."""
        # Mock empty HTML response
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = home_manager_search("nonexistent", limit=5)
        assert result == "No Home Manager options found matching 'nonexistent'"
        assert "<" not in result

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_empty_search_plain_text(self, mock_post):
        """Test nixos_search with no results returns plain text."""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = nixos_search("nonexistent", search_type="packages")
        assert result == "No packages found matching 'nonexistent'"
        assert "<" not in result
