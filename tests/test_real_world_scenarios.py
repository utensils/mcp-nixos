#!/usr/bin/env python3
"""Real-world scenario tests based on actual MCP tool usage patterns."""

from unittest.mock import patch, Mock
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    nixos_channels,
    home_manager_search,
    home_manager_info,
    home_manager_options_by_prefix,
    home_manager_stats,
    darwin_search,
    darwin_options_by_prefix,
)


class TestRealWorldScenarios:
    """Test scenarios based on real user interactions with the MCP tools."""

    def test_scenario_installing_development_tools(self):
        """User wants to set up a development environment with Git."""
        # Step 1: Search for Git package
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                    }
                }
            ]

            result = nixos_search("git")
            assert "git (2.49.0)" in result
            assert "Distributed version control system" in result

        # Step 2: Get package details
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                        "package_homepage": ["https://git-scm.com/"],
                    }
                }
            ]

            result = nixos_info("git")
            assert "Package: git" in result
            assert "Homepage: https://git-scm.com/" in result

        # Step 3: Configure Git in Home Manager
        # First, discover available options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Whether to enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Default user name"},
                {"name": "programs.git.userEmail", "type": "string", "description": "Default user email"},
            ]

            result = home_manager_options_by_prefix("programs.git")
            assert "programs.git.enable" in result
            assert "programs.git.userName" in result

        # Step 4: Get specific option details
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                }
            ]

            result = home_manager_info("programs.git.enable")
            assert "Type: boolean" in result

    def test_scenario_migrating_nixos_channels(self):
        """User wants to understand and migrate between NixOS channels."""
        # Step 1: Check available channels
        with patch("mcp_nixos.server.channel_cache.get_available") as mock_discover:
            mock_discover.return_value = {
                "latest-43-nixos-25.05": "151,698 documents",
                "latest-43-nixos-24.11": "142,034 documents",
                "latest-43-nixos-unstable": "151,798 documents",
            }

            result = nixos_channels()
            assert "stable (current: 25.05)" in result
            assert "24.11" in result
            assert "unstable" in result

        # Step 2: Compare package availability across channels
        channels_to_test = ["stable", "24.11", "unstable"]

        for channel in channels_to_test:
            with patch("mcp_nixos.server.get_channels") as mock_get:
                mock_get.return_value = {
                    "stable": "latest-43-nixos-25.05",
                    "24.11": "latest-43-nixos-24.11",
                    "unstable": "latest-43-nixos-unstable",
                }

                with patch("mcp_nixos.server.es_query") as mock_es:
                    mock_es.return_value = []
                    result = nixos_search("firefox", channel=channel)
                    # Should work with all valid channels
                    assert "Error" not in result or "Invalid channel" not in result

    def test_scenario_configuring_macos_with_darwin(self):
        """User wants to configure macOS system settings."""
        # Step 1: Search for dock settings
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "system.defaults.dock.autohide",
                    "type": "boolean",
                    "description": "Whether to automatically hide the dock",
                }
            ]

            result = darwin_search("dock autohide")
            assert "system.defaults.dock.autohide" in result

        # Step 2: Browse all dock options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
                {"name": "system.defaults.dock.autohide-delay", "type": "float", "description": "Auto-hide delay"},
                {"name": "system.defaults.dock.orientation", "type": "string", "description": "Dock position"},
                {"name": "system.defaults.dock.show-recents", "type": "boolean", "description": "Show recent apps"},
            ]

            result = darwin_options_by_prefix("system.defaults.dock")
            assert "system.defaults.dock.autohide" in result
            assert "system.defaults.dock.orientation" in result

    def test_scenario_discovering_program_options(self):
        """User exploring what programs can be configured in Home Manager."""
        # Step 1: Search for shell configuration
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.zsh.enable", "type": "boolean", "description": "Whether to enable zsh"},
                {"name": "programs.bash.enable", "type": "boolean", "description": "Whether to enable bash"},
                {"name": "programs.fish.enable", "type": "boolean", "description": "Whether to enable fish"},
            ]

            result = home_manager_search("shell")
            # At least one shell option should be found
            assert any(shell in result for shell in ["zsh", "bash", "fish"])

        # Step 2: Explore specific shell options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.zsh.enable", "type": "boolean", "description": "Whether to enable zsh"},
                {"name": "programs.zsh.oh-my-zsh.enable", "type": "boolean", "description": "Enable oh-my-zsh"},
                {"name": "programs.zsh.oh-my-zsh.theme", "type": "string", "description": "oh-my-zsh theme"},
                {"name": "programs.zsh.shellAliases", "type": "attribute set", "description": "Shell aliases"},
            ]

            result = home_manager_options_by_prefix("programs.zsh")
            assert "programs.zsh.oh-my-zsh.enable" in result
            assert "programs.zsh.shellAliases" in result

    def test_scenario_invalid_option_names(self):
        """Test what happens when users provide invalid option names."""
        # Common mistake: using partial names
        test_cases = [
            ("programs.git", "programs.git.enable"),  # Missing .enable
            ("git", "programs.git.enable"),  # Missing programs prefix
            ("system", "system.defaults"),  # Too generic
        ]

        for invalid_name, _ in test_cases:
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = []  # No exact match

                result = home_manager_info(invalid_name)
                assert "not found" in result.lower()

    def test_scenario_exploring_available_packages_by_type(self):
        """User wants to find packages by category."""
        # Search for different types of packages
        package_types = [
            ("editor", ["neovim", "vim", "emacs"]),
            ("browser", ["firefox", "chromium"]),
            ("terminal", ["alacritty", "kitty", "wezterm"]),
        ]

        for search_term, expected_packages in package_types:
            with patch("mcp_nixos.server.es_query") as mock_es:
                # Return at least one expected package
                mock_es.return_value = [
                    {
                        "_source": {
                            "type": "package",
                            "package_pname": expected_packages[0],
                            "package_pversion": "1.0.0",
                            "package_description": f"A {search_term}",
                        }
                    }
                ]

                result = nixos_search(search_term)
                assert any(pkg in result for pkg in expected_packages)

    def test_scenario_understanding_option_types(self):
        """User needs to understand different option types in configurations."""
        # Different option types in Home Manager
        option_examples = [
            ("programs.git.enable", "boolean", "true/false value"),
            ("programs.git.userName", "string", "text value"),
            ("home.packages", "list of package", "list of packages"),
            ("programs.git.aliases", "attribute set of string", "key-value pairs"),
            (
                "services.dunst.settings",
                "attribute set of (attribute set of (string or signed integer or boolean))",
                "complex nested structure",
            ),
        ]

        for option_name, type_str, _ in option_examples:
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = [
                    {
                        "name": option_name,
                        "type": type_str,
                        "description": "Test option",
                    }
                ]

                result = home_manager_info(option_name)
                assert f"Type: {type_str}" in result

    def test_scenario_channel_suggestions_for_typos(self):
        """User makes typos in channel names and needs suggestions."""
        typo_tests = [
            ("stabel", ["stable"]),  # Typo
            ("25.11", ["25.05", "24.11"]),  # Future version
            ("nixos-24.11", ["24.11"]),  # Wrong format
        ]

        for typo, expected_suggestions in typo_tests:
            with patch("mcp_nixos.server.get_channels") as mock_get:
                mock_get.return_value = {
                    "stable": "latest-43-nixos-25.05",
                    "unstable": "latest-43-nixos-unstable",
                    "25.05": "latest-43-nixos-25.05",
                    "24.11": "latest-43-nixos-24.11",
                }

                result = nixos_search("test", channel=typo)
                assert "Invalid channel" in result
                assert "Available channels:" in result
                # At least one suggestion should be present
                assert any(sug in result for sug in expected_suggestions)

    def test_scenario_performance_with_wildcards(self):
        """User uses wildcards in searches."""
        # NixOS option search with wildcards
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "option",
                        "option_name": "services.nginx.enable",
                        "option_type": "boolean",
                        "option_description": "Whether to enable nginx",
                    }
                }
            ]

            # Search for options with wildcards
            result = nixos_search("*.nginx.*", search_type="options")
            assert "services.nginx.enable" in result

    def test_scenario_stats_usage_patterns(self):
        """User wants to understand the scale of available packages/options."""
        # Get stats for different channels
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "unstable": "latest-43-nixos-unstable",
                "stable": "latest-43-nixos-25.05",
            }

            with patch("requests.post") as mock_post:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.side_effect = [
                    {"count": 129865},  # packages
                    {"count": 21933},  # options
                ]
                mock_resp.raise_for_status.return_value = None
                mock_post.return_value = mock_resp

                result = nixos_stats("unstable")
                assert "129,865" in result  # Formatted number
                assert "21,933" in result

        # Stats functions now return actual statistics
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
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
