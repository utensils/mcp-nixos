#!/usr/bin/env python3
"""Comprehensive MCP behavior evaluation tests based on real tool testing."""

from unittest.mock import patch, Mock
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    nixos_channels,
    home_manager_search,
    home_manager_info,
    home_manager_list_options,
    home_manager_options_by_prefix,
    home_manager_stats,
    darwin_search,
    darwin_options_by_prefix,
    darwin_stats,
)


class TestMCPBehaviorComprehensive:
    """Test real-world usage patterns based on actual tool testing results."""

    def test_nixos_package_discovery_flow(self):
        """Test typical package discovery workflow."""
        # 1. Search for packages
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                    }
                },
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "gitoxide",
                        "package_pversion": "0.40.0",
                        "package_description": "Rust implementation of Git",
                    }
                },
            ]

            result = nixos_search("git", limit=5)
            assert "git (2.49.0)" in result
            assert "Distributed version control system" in result
            assert "gitoxide" in result

        # 2. Get detailed info about a specific package
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                        "package_homepage": ["https://git-scm.com/"],
                        "package_license_set": ["GNU General Public License v2.0"],
                    }
                }
            ]

            result = nixos_info("git")
            assert "Package: git" in result
            assert "Version: 2.49.0" in result
            assert "Homepage: https://git-scm.com/" in result
            assert "License: GNU General Public License v2.0" in result

    def test_nixos_channel_awareness(self):
        """Test channel discovery and usage."""
        # 1. List available channels
        with patch("mcp_nixos.server.channel_cache.get_available") as mock_discover:
            mock_discover.return_value = {
                "latest-43-nixos-unstable": "151,798 documents",
                "latest-43-nixos-25.05": "151,698 documents",
                "latest-43-nixos-24.11": "142,034 documents",
            }

            result = nixos_channels()
            assert "NixOS Channels" in result
            assert "stable (current: 25.05)" in result
            assert "unstable" in result
            assert "✓ Available" in result

        # 2. Get stats for a channel
        with patch("requests.post") as mock_post:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.side_effect = [
                {"count": 129865},  # packages
                {"count": 21933},  # options
            ]
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = nixos_stats()
            assert "NixOS Statistics" in result
            assert "129,865" in result
            assert "21,933" in result

    def test_home_manager_option_discovery_flow(self):
        """Test typical Home Manager option discovery workflow."""
        # 1. Search for options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Default Git username",
                },
                {
                    "name": "programs.git.userEmail",
                    "type": "string",
                    "description": "Default Git email",
                },
            ]

            result = home_manager_search("git", limit=3)
            assert "programs.git.enable" in result
            assert "programs.git.userName" in result
            assert "programs.git.userEmail" in result

        # 2. Browse by prefix to find exact option names
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.aliases",
                    "type": "attribute set of string",
                    "description": "Git aliases",
                },
                {
                    "name": "programs.git.delta.enable",
                    "type": "boolean",
                    "description": "Whether to enable delta syntax highlighting",
                },
            ]

            result = home_manager_options_by_prefix("programs.git")
            assert "programs.git.enable" in result
            assert "programs.git.aliases" in result
            assert "programs.git.delta.enable" in result

        # 3. Get specific option info (requires exact name)
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                }
            ]

            result = home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result
            assert "Type: boolean" in result
            assert "Whether to enable Git" in result

    def test_home_manager_category_exploration(self):
        """Test exploring Home Manager categories."""
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Simulate real category distribution
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "", "description": ""},
                {"name": "programs.vim.enable", "type": "", "description": ""},
                {"name": "services.gpg-agent.enable", "type": "", "description": ""},
                {"name": "home.packages", "type": "", "description": ""},
                {"name": "accounts.email.accounts", "type": "", "description": ""},
            ]

            result = home_manager_list_options()
            assert "Home Manager option categories" in result
            assert "programs (2 options)" in result
            assert "services (1 options)" in result
            assert "home (1 options)" in result
            assert "accounts (1 options)" in result

    def test_darwin_system_configuration_flow(self):
        """Test typical Darwin configuration workflow."""
        # 1. Search for system options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "system.defaults.dock.autohide",
                    "type": "boolean",
                    "description": "Whether to automatically hide the dock",
                },
                {
                    "name": "system.defaults.NSGlobalDomain.AppleInterfaceStyle",
                    "type": "string",
                    "description": "Set to 'Dark' to enable dark mode",
                },
                {
                    "name": "system.stateVersion",
                    "type": "string",
                    "description": "The nix-darwin state version",
                },
            ]

            result = darwin_search("system", limit=3)
            assert "system.defaults.dock.autohide" in result
            assert "system.defaults.NSGlobalDomain.AppleInterfaceStyle" in result
            assert "system.stateVersion" in result

        # 2. Browse system options by prefix
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "system.defaults.dock.autohide",
                    "type": "boolean",
                    "description": "Whether to automatically hide the dock",
                },
                {
                    "name": "system.defaults.dock.autohide-delay",
                    "type": "float",
                    "description": "Dock autohide delay",
                },
                {
                    "name": "system.defaults.dock.orientation",
                    "type": "string",
                    "description": "Dock position on screen",
                },
            ]

            result = darwin_options_by_prefix("system.defaults.dock")
            assert "system.defaults.dock.autohide" in result
            assert "system.defaults.dock.autohide-delay" in result
            assert "system.defaults.dock.orientation" in result

    def test_error_handling_with_suggestions(self):
        """Test error handling provides helpful suggestions."""
        # Invalid channel
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-43-nixos-25.05",
                "unstable": "latest-43-nixos-unstable",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
            }

            result = nixos_search("test", channel="24.05")
            assert "Invalid channel" in result
            assert "Available channels:" in result
            assert "24.11" in result or "25.05" in result

    def test_cross_tool_consistency(self):
        """Test that different tools provide consistent information."""
        # Channel consistency
        with patch("mcp_nixos.server.get_channels") as mock_get:
            channels = {
                "stable": "latest-43-nixos-25.05",
                "unstable": "latest-43-nixos-unstable",
                "25.05": "latest-43-nixos-25.05",
                "beta": "latest-43-nixos-25.05",
            }
            mock_get.return_value = channels

            # All tools should accept the same channels
            for channel in ["stable", "unstable", "25.05", "beta"]:
                with patch("mcp_nixos.server.es_query") as mock_es:
                    mock_es.return_value = []
                    result = nixos_search("test", channel=channel)
                    assert "Error" not in result or "Invalid channel" not in result

    def test_real_world_git_configuration_scenario(self):
        """Test a complete Git configuration discovery scenario."""
        # User wants to configure Git in Home Manager

        # Step 1: Search for git-related options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Default Git username",
                },
            ]

            result = home_manager_search("git user")
            assert "programs.git.userName" in result

        # Step 2: Browse all git options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Whether to enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Default Git username"},
                {"name": "programs.git.userEmail", "type": "string", "description": "Default Git email"},
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG signing key"},
                {
                    "name": "programs.git.signing.signByDefault",
                    "type": "boolean",
                    "description": "Sign commits by default",
                },
            ]

            result = home_manager_options_by_prefix("programs.git")
            assert "programs.git.userName" in result
            assert "programs.git.userEmail" in result
            assert "programs.git.signing.key" in result

        # Step 3: Get details for specific options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.signing.signByDefault",
                    "type": "boolean",
                    "description": "Whether to sign commits by default",
                }
            ]

            result = home_manager_info("programs.git.signing.signByDefault")
            assert "Type: boolean" in result
            assert "sign commits by default" in result

    def test_performance_with_large_result_sets(self):
        """Test handling of large result sets efficiently."""
        # Home Manager has 2000+ options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Simulate large option set
            mock_options = []
            for i in range(2129):  # Actual count from testing
                mock_options.append(
                    {
                        "name": f"programs.option{i}",
                        "type": "string",
                        "description": f"Option {i}",
                    }
                )
            mock_parse.return_value = mock_options

            result = home_manager_list_options()
            assert "2129 options" in result or "programs (" in result

    def test_package_not_found_behavior(self):
        """Test behavior when packages/options are not found."""
        # Package not found
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = []

            result = nixos_info("nonexistent-package")
            assert "not found" in result.lower()

        # Option not found
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            result = home_manager_info("nonexistent.option")
            assert "not found" in result.lower()

    def test_channel_migration_scenario(self):
        """Test that users can migrate from old to new channels."""
        # User on 24.11 wants to upgrade to 25.05
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-43-nixos-25.05",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
                "unstable": "latest-43-nixos-unstable",
            }

            # Can still query old channel
            with patch("mcp_nixos.server.es_query") as mock_es:
                mock_es.return_value = []
                result = nixos_search("test", channel="24.11")
                assert "Error" not in result or "Invalid channel" not in result

            # Can query new stable
            with patch("mcp_nixos.server.es_query") as mock_es:
                mock_es.return_value = []
                result = nixos_search("test", channel="stable")
                assert "Error" not in result or "Invalid channel" not in result

    def test_option_type_information(self):
        """Test that option type information is properly displayed."""
        test_cases = [
            ("boolean option", "boolean", "programs.git.enable"),
            ("string option", "string", "programs.git.userName"),
            ("attribute set", "attribute set of string", "programs.git.aliases"),
            ("list option", "list of string", "home.packages"),
            ("complex type", "null or string or signed integer", "services.dunst.settings.global.offset"),
        ]

        for desc, type_str, option_name in test_cases:
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = [
                    {
                        "name": option_name,
                        "type": type_str,
                        "description": f"Test {desc}",
                    }
                ]

                result = home_manager_info(option_name)
                assert f"Type: {type_str}" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_stats_functions_limitations(self, mock_parse):
        """Test that stats functions return actual statistics now."""
        # Mock parsed options for Home Manager
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg-agent.enable", "type": "boolean", "description": "Enable GPG agent"},
            {"name": "home.packages", "type": "list", "description": "Packages to install"},
            {"name": "wayland.windowManager.sway.enable", "type": "boolean", "description": "Enable Sway"},
            {"name": "xsession.enable", "type": "boolean", "description": "Enable X session"},
        ]

        # Home Manager stats now return actual statistics
        result = home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result

        # Mock parsed options for Darwin
        mock_parse.return_value = [
            {"name": "services.nix-daemon.enable", "type": "boolean", "description": "Enable nix-daemon"},
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            {"name": "launchd.agents.test", "type": "attribute set", "description": "Launchd agents"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "homebrew.enable", "type": "boolean", "description": "Enable Homebrew"},
        ]

        # Darwin stats now return actual statistics
        result = darwin_stats()
        assert "nix-darwin Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
