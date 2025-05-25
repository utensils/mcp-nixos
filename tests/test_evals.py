"""Basic evaluation tests for MCP-NixOS to validate AI usability."""

import pytest
from unittest.mock import patch, Mock
import xml.etree.ElementTree as ET
from mcp_nixos.server import nixos_search, nixos_info, home_manager_search, darwin_search


class TestPackageDiscoveryEvals:
    """Evaluations for package discovery scenarios."""

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
                            "package": {
                                "pname": "vscode",
                                "version": "1.85.0",
                                "description": "Open source source code editor developed by Microsoft",
                            }
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        # Simulate tool call that AI would make
        result = nixos_search("vscode", type="packages")

        # Verify AI would get useful results
        root = ET.fromstring(result)
        assert root.find(".//package/name").text == "vscode"
        assert "Microsoft" in root.find(".//package/description").text

        # AI should be able to provide installation instructions from this
        assert root.tag == "package_search"
        assert int(root.find(".//results").get("count")) > 0

    @patch("mcp_nixos.server.requests.post")
    def test_find_git_command(self, mock_post):
        """User wants 'git' command - should search programs and get package info."""
        # First call - search programs
        search_response = Mock()
        search_response.json.return_value = {"hits": {"hits": [{"_source": {"program": "git", "package": "git"}}]}}

        # Second call - get package info
        info_response = Mock()
        info_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package": {
                                "pname": "git",
                                "version": "2.43.0",
                                "description": "Distributed version control system",
                                "homepage": "https://git-scm.com",
                            }
                        }
                    }
                ]
            }
        }

        mock_post.side_effect = [search_response, info_response]

        # AI would first search for the program
        result1 = nixos_search("git", type="programs")
        root1 = ET.fromstring(result1)
        assert root1.find(".//program/name").text == "git"
        assert root1.find(".//program/package").text == "git"

        # Then get detailed info
        result2 = nixos_info("git", type="package")
        root2 = ET.fromstring(result2)
        assert root2.find(".//name").text == "git"
        assert "version control" in root2.find(".//description").text


class TestServiceConfigurationEvals:
    """Evaluations for service configuration scenarios."""

    @patch("mcp_nixos.server.requests.post")
    def test_nginx_setup(self, mock_post):
        """User wants to set up nginx - should find service options."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "option": {
                                "option_name": "services.nginx.enable",
                                "option_type": "boolean",
                                "option_description": "Whether to enable the nginx web server",
                                "option_default": "false",
                            }
                        }
                    },
                    {
                        "_source": {
                            "option": {
                                "option_name": "services.nginx.virtualHosts",
                                "option_type": "attribute set of submodules",
                                "option_description": "Declarative nginx virtual hosts",
                            }
                        }
                    },
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_search("services.nginx", type="options")

        root = ET.fromstring(result)
        options = root.findall(".//option")

        # Should find enable option
        enable_found = False
        vhosts_found = False

        for opt in options:
            name = opt.find("name").text
            if name == "services.nginx.enable":
                enable_found = True
                assert opt.find("type").text == "boolean"
            elif name == "services.nginx.virtualHosts":
                vhosts_found = True
                assert "virtual hosts" in opt.find("description").text

        assert enable_found, "Should find nginx enable option"
        assert vhosts_found, "Should find virtualHosts option"


class TestHomeManagerIntegrationEvals:
    """Evaluations for Home Manager vs system configuration."""

    @patch("mcp_nixos.server.requests.get")
    def test_git_user_config(self, mock_get):
        """User asks about git config - should find Home Manager options."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">programs.git.enable</dt>
            <dd>
                <p>Whether to enable Git</p>
                <span class="term">Type: boolean</span>
            </dd>
            <dt class="option">programs.git.userName</dt>
            <dd>
                <p>Default Git user name</p>
                <span class="term">Type: string</span>
            </dd>
            <dt class="option">programs.git.userEmail</dt>
            <dd>
                <p>Default Git user email</p>
                <span class="term">Type: string</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_response

        result = home_manager_search("programs.git")

        root = ET.fromstring(result)
        options = root.findall(".//option")

        # Should find git configuration options
        option_names = [opt.find("name").text for opt in options]
        assert "programs.git.enable" in option_names
        assert "programs.git.userName" in option_names
        assert "programs.git.userEmail" in option_names

        # AI can recommend Home Manager for user-specific git config


class TestDarwinPlatformEvals:
    """Evaluations for macOS/nix-darwin scenarios."""

    @patch("mcp_nixos.server.requests.get")
    def test_macos_dock_settings(self, mock_get):
        """User wants to configure macOS dock - should find darwin options."""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <dt class="option">system.defaults.dock.autohide</dt>
            <dd>
                <p>Whether to automatically hide the dock</p>
                <span class="term">Type: boolean</span>
            </dd>
            <dt class="option">system.defaults.dock.tilesize</dt>
            <dd>
                <p>Size of dock icons</p>
                <span class="term">Type: integer</span>
            </dd>
        </html>
        """
        mock_get.return_value = mock_response

        result = darwin_search("system.defaults.dock")

        root = ET.fromstring(result)
        options = root.findall(".//option")

        # Should find dock configuration options
        option_names = [opt.find("name").text for opt in options]
        assert "system.defaults.dock.autohide" in option_names
        assert "system.defaults.dock.tilesize" in option_names

        # AI can provide darwin-configuration.nix examples


class TestErrorHandlingEvals:
    """Evaluations for error scenarios."""

    def test_invalid_channel_error(self):
        """Should provide clear error for invalid channel."""
        result = nixos_search("test", channel="invalid-channel")

        root = ET.fromstring(result)
        assert root.tag == "error"
        assert "Invalid channel" in root.find(".//message").text

        # AI should understand this is a channel error

    @patch("mcp_nixos.server.requests.post")
    def test_package_not_found(self, mock_post):
        """Should provide clear message when package not found."""
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_response

        result = nixos_info("nonexistent-package", type="package")

        root = ET.fromstring(result)
        assert root.tag == "error"
        assert root.find(".//code").text == "NOT_FOUND"
        assert "not found" in root.find(".//message").text


@pytest.mark.integration
class TestCompleteScenarioEval:
    """Full scenario evaluation."""

    @patch("mcp_nixos.server.requests.post")
    @patch("mcp_nixos.server.requests.get")
    def test_complete_firefox_installation_flow(self, mock_get, mock_post):
        """Complete flow: user wants Firefox with specific config."""
        # 1. Search for firefox package
        search_response = Mock()
        search_response.json.return_value = {
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

        # 2. Get package info
        info_response = Mock()
        info_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package": {
                                "pname": "firefox",
                                "version": "120.0",
                                "description": "Mozilla Firefox browser",
                                "homepage": "https://www.mozilla.org/firefox/",
                                "license": "MPL-2.0",
                            }
                        }
                    }
                ]
            }
        }

        mock_post.side_effect = [search_response, info_response]

        # 3. Check Home Manager for user config
        mock_get.return_value = Mock(
            text="""
        <html>
            <dt class="option">programs.firefox.enable</dt>
            <dd>
                <p>Whether to enable Firefox</p>
                <span class="term">Type: boolean</span>
            </dd>
        </html>
        """
        )

        # Execute the flow an AI would follow
        search_result = nixos_search("firefox", type="packages")
        assert "firefox" in search_result.lower()

        info_result = nixos_info("firefox", type="package")
        assert "Mozilla" in info_result

        hm_result = home_manager_search("firefox")
        assert "programs.firefox.enable" in hm_result

        # AI should now be able to provide both system and user installation options


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
