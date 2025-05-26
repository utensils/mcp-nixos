#!/usr/bin/env python3
"""Tests for improving option info lookup functionality."""

from unittest.mock import patch
from mcp_nixos.server import (
    home_manager_info,
    home_manager_options_by_prefix,
    darwin_info,
)


class TestOptionInfoImprovements:
    """Test improvements to option info lookup based on real usage."""

    def test_home_manager_info_requires_exact_match(self):
        """Test that home_manager_info requires exact option names."""
        # User tries "programs.git" but it's not a valid option
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Return git-related options but no exact "programs.git" match
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Git username"},
            ]

            result = home_manager_info("programs.git")
            assert "not found" in result.lower()

        # User provides exact option name
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
            ]

            result = home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result
            assert "Type: boolean" in result

    def test_browse_then_info_workflow(self):
        """Test the recommended workflow: browse first, then get info."""
        # Step 1: Browse to find exact names
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Git username"},
                {"name": "programs.git.userEmail", "type": "string", "description": "Git email"},
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG key"},
            ]

            result = home_manager_options_by_prefix("programs.git")
            assert "programs.git.enable" in result
            assert "programs.git.signing.key" in result

        # Step 2: Get info with exact name from browse results
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG signing key"},
            ]

            result = home_manager_info("programs.git.signing.key")
            assert "Option: programs.git.signing.key" in result
            assert "Type: string" in result

    def test_darwin_info_same_behavior(self):
        """Test that darwin_info has the same exact-match requirement."""
        # Partial name fails
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            ]

            result = darwin_info("system")
            assert "not found" in result.lower()

        # Exact name works
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            ]

            result = darwin_info("system.defaults.dock.autohide")
            assert "Option: system.defaults.dock.autohide" in result

    def test_common_user_mistakes(self):
        """Test common mistakes users make when looking up options."""
        mistakes = [
            # (what user tries, what they should use)
            ("programs.git", "programs.git.enable"),
            ("home.packages", "home.packages"),  # This one is actually valid
            ("system", "system.stateVersion"),
            ("services.gpg", "services.gpg-agent.enable"),
        ]

        for wrong_name, _ in mistakes:
            # Wrong name returns not found
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = []
                result = home_manager_info(wrong_name)
                assert "not found" in result.lower()

    def test_helpful_error_messages_needed(self):
        """Test that error messages could be more helpful."""
        # When option not found, could suggest using browse
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            result = home_manager_info("programs.git")
            assert "not found" in result.lower()
            # Could improve by suggesting: "Try home_manager_options_by_prefix('programs.git')"

    def test_case_sensitivity(self):
        """Test that option lookup is case-sensitive."""
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
            ]

            # Exact case works
            result = home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result

        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            # Wrong case fails
            result = home_manager_info("programs.Git.enable")
            assert "not found" in result.lower()

    def test_nested_option_discovery(self):
        """Test discovering deeply nested options."""
        # User wants to find git.signing options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.signing.key", "type": "null or string", "description": "GPG key ID"},
                {"name": "programs.git.signing.signByDefault", "type": "boolean", "description": "Auto-sign"},
                {"name": "programs.git.signing.gpgPath", "type": "string", "description": "Path to gpg"},
            ]

            result = home_manager_options_by_prefix("programs.git.signing")
            assert "programs.git.signing.key" in result
            assert "programs.git.signing.signByDefault" in result

    def test_option_info_with_complex_types(self):
        """Test that complex option types are displayed correctly."""
        complex_types = [
            ("null or string", "programs.git.signing.key"),
            ("attribute set of string", "programs.git.aliases"),
            ("list of string", "programs.zsh.plugins"),
            ("string or signed integer or boolean", "services.dunst.settings.global.offset"),
        ]

        for type_str, option_name in complex_types:
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = [
                    {"name": option_name, "type": type_str, "description": "Complex option"},
                ]

                result = home_manager_info(option_name)
                assert f"Type: {type_str}" in result

    def test_stats_limitations_are_clear(self):
        """Test that stats function limitations are clearly communicated."""
        from mcp_nixos.server import home_manager_stats, darwin_stats

        # Home Manager stats
        result = home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result

        # Darwin stats
        result = darwin_stats()
        assert "nix-darwin Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
