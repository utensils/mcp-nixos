"""Basic evaluation tests for MCP-NixOS to validate AI usability."""

import pytest
from unittest.mock import patch, Mock
from mcp_nixos.server import nixos_search, nixos_info, home_manager_search, darwin_search


class TestPackageDiscoveryEvals:
    """Evaluations for package discovery scenarios."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    @patch("mcp_nixos.server.requests.post")
    def test_find_vscode_package(self, mock_post):
        """User wants to install VSCode - should find the correct package."""
        # Mock search response
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "vscode",
                            "package_pversion": "1.85.0",
                            "package_description": "Open source source code editor developed by Microsoft",
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Simulate tool call that AI would make
        result = nixos_search("vscode", search_type="packages")

        # Verify AI would get useful results
        assert "Found 1 packages matching 'vscode':" in result
        assert "• vscode (1.85.0)" in result
        assert "Open source source code editor developed by Microsoft" in result

    @patch("mcp_nixos.server.requests.post")
    def test_find_git_command(self, mock_post):
        """User wants 'git' command - should search programs and get package info."""
        # First call - search programs
        search_response = Mock()
        search_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_programs": ["git"],
                            "package_pname": "git",
                        }
                    }
                ]
            }
        }
        search_response.raise_for_status = Mock()

        # Second call - get package info
        info_response = Mock()
        info_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "git",
                            "package_pversion": "2.43.0",
                            "package_description": "Distributed version control system",
                            "package_homepage": ["https://git-scm.com"],
                        }
                    }
                ]
            }
        }
        info_response.raise_for_status = Mock()

        mock_post.side_effect = [search_response, info_response]

        # AI would first search for the program
        result1 = nixos_search("git", search_type="programs")
        assert "Found 1 programs matching 'git':" in result1
        assert "• git (provided by git)" in result1

        # Then get detailed info
        result2 = nixos_info("git", type="package")
        assert "Package: git" in result2
        assert "Version: 2.43.0" in result2
        assert "Distributed version control system" in result2


class TestServiceConfigurationEvals:
    """Evaluations for service configuration scenarios."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    @patch("mcp_nixos.server.requests.post")
    def test_nginx_setup(self, mock_post):
        """User wants to set up nginx - should find service options."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "option_name": "services.nginx.enable",
                            "option_type": "boolean",
                            "option_description": "Whether to enable Nginx Web Server.",
                            "option_default": "false",
                        }
                    },
                    {
                        "_source": {
                            "option_name": "services.nginx.virtualHosts",
                            "option_type": "attribute set of submodules",
                            "option_description": "Definition of nginx virtual hosts.",
                        }
                    },
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # AI searches for nginx options
        result = nixos_search("nginx", search_type="options")

        # Should get service configuration options
        assert "Found 2 options matching 'nginx':" in result
        assert "• services.nginx.enable" in result
        assert "• services.nginx.virtualHosts" in result
        assert "Whether to enable Nginx Web Server" in result


class TestHomeManagerIntegrationEvals:
    """Evaluations for Home Manager configuration scenarios."""

    @patch("mcp_nixos.server.requests.get")
    def test_git_user_config(self, mock_get):
        """User wants to configure git via Home Manager."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>programs.git.enable</dt>
            <dd>
                <p>Whether to enable Git.</p>
                <span class="term">Type: boolean</span>
            </dd>
            <dt>programs.git.userName</dt>
            <dd>
                <p>Default user name to use.</p>
                <span class="term">Type: null or string</span>
            </dd>
            <dt>programs.git.userEmail</dt>
            <dd>
                <p>Default user email to use.</p>
                <span class="term">Type: null or string</span>
            </dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # AI searches for git configuration
        result = home_manager_search("git")

        # Should find user-level git options
        assert "Found 3 Home Manager options matching 'git':" in result
        assert "• programs.git.enable" in result
        assert "• programs.git.userName" in result
        assert "• programs.git.userEmail" in result


class TestDarwinPlatformEvals:
    """Evaluations for macOS-specific scenarios."""

    @patch("mcp_nixos.server.requests.get")
    def test_macos_dock_settings(self, mock_get):
        """User wants to configure macOS dock behavior."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt>system.defaults.dock.autohide</dt>
            <dd>
                <p>Whether to automatically hide and show the dock.</p>
                <span class="term">Type: null or boolean</span>
            </dd>
            <dt>system.defaults.dock.autohide-delay</dt>
            <dd>
                <p>Sets the speed of the autohide delay.</p>
                <span class="term">Type: null or float</span>
            </dd>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # AI searches for dock settings
        result = darwin_search("dock")

        # Should find macOS dock options
        assert "Found 2 nix-darwin options matching 'dock':" in result
        assert "• system.defaults.dock.autohide" in result
        assert "Whether to automatically hide and show the dock" in result


class TestErrorHandlingEvals:
    """Evaluations for error scenarios."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    def test_invalid_channel_error(self):
        """User specifies invalid channel - should get clear error."""
        result = nixos_search("firefox", channel="invalid-channel")

        # Should get a clear error message
        assert "Error (ERROR): Invalid channel 'invalid-channel'" in result

    @patch("mcp_nixos.server.requests.post")
    def test_package_not_found(self, mock_post):
        """User searches for non-existent package."""
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = nixos_info("nonexistentpackage", type="package")

        # Should get informative not found error
        assert "Error (NOT_FOUND): Package 'nonexistentpackage' not found" in result


class TestCompleteScenarioEval:
    """End-to-end scenario evaluation."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    @patch("mcp_nixos.server.requests.post")
    @patch("mcp_nixos.server.requests.get")
    def test_complete_firefox_installation_flow(self, mock_get, mock_post):
        """Complete flow: user wants Firefox with specific Home Manager config."""
        # Step 1: Search for Firefox package
        search_resp = Mock()
        search_resp.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "firefox",
                            "package_pversion": "121.0",
                            "package_description": "A web browser built from Firefox source tree",
                        }
                    }
                ]
            }
        }
        search_resp.raise_for_status = Mock()

        # Step 2: Get package details
        info_resp = Mock()
        info_resp.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_pname": "firefox",
                            "package_pversion": "121.0",
                            "package_description": "A web browser built from Firefox source tree",
                            "package_homepage": ["https://www.mozilla.org/firefox/"],
                            "package_license_set": ["MPL-2.0"],
                        }
                    }
                ]
            }
        }
        info_resp.raise_for_status = Mock()

        # Step 3: Search Home Manager options
        hm_resp = Mock()
        hm_resp.text = """
        <html>
            <dt>programs.firefox.enable</dt>
            <dd>
                <p>Whether to enable Firefox.</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        hm_resp.raise_for_status = Mock()

        mock_post.side_effect = [search_resp, info_resp]
        mock_get.return_value = hm_resp

        # Execute the flow
        # 1. Search for Firefox
        result1 = nixos_search("firefox")
        assert "Found 1 packages matching 'firefox':" in result1
        assert "• firefox (121.0)" in result1

        # 2. Get detailed info
        result2 = nixos_info("firefox")
        assert "Package: firefox" in result2
        assert "Homepage: https://www.mozilla.org/firefox/" in result2

        # 3. Check Home Manager options
        result3 = home_manager_search("firefox")
        assert "• programs.firefox.enable" in result3

        # AI should now have all info needed to guide user through installation
