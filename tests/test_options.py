"""Comprehensive tests for nixos_info option lookups."""

from unittest.mock import patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
darwin_info = get_tool_function("darwin_info")
darwin_stats = get_tool_function("darwin_stats")
home_manager_info = get_tool_function("home_manager_info")
home_manager_options_by_prefix = get_tool_function("home_manager_options_by_prefix")
home_manager_stats = get_tool_function("home_manager_stats")
nixos_info = get_tool_function("nixos_info")


class TestNixosInfoOptions:
    """Test nixos_info with option lookups."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_with_exact_match(self, mock_query):
        """Test info retrieval for exact option match."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.nginx.enable",
                    "option_type": "boolean",
                    "option_description": "<rendered-html><p>Whether to enable Nginx Web Server.</p>\n</rendered-html>",
                    "option_default": "false",
                    "option_example": "true",
                }
            }
        ]

        result = await nixos_info("services.nginx.enable", type="option")

        # Verify the query
        mock_query.assert_called_once()
        query = mock_query.call_args[0][1]
        assert query["bool"]["must"][0]["term"]["type"] == "option"
        assert query["bool"]["must"][1]["term"]["option_name"] == "services.nginx.enable"

        # Verify the result
        assert "Option: services.nginx.enable" in result
        assert "Type: boolean" in result
        assert "Description: Whether to enable Nginx Web Server." in result
        assert "Default: false" in result
        assert "Example: true" in result
        assert "<rendered-html>" not in result  # HTML should be stripped

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_not_found(self, mock_query):
        """Test info when option is not found."""
        mock_query.return_value = []

        result = await nixos_info("services.nginx.nonexistent", type="option")
        assert result == "Error (NOT_FOUND): Option 'services.nginx.nonexistent' not found"

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_with_minimal_fields(self, mock_query):
        """Test info with minimal option fields."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.test.enable",
                    "option_description": "Enable test service",
                }
            }
        ]

        result = await nixos_info("services.test.enable", type="option")
        assert "Option: services.test.enable" in result
        assert "Description: Enable test service" in result
        # No type, default, or example should not cause errors
        assert "Type:" not in result or "Type: " in result
        assert "Default:" not in result or "Default: " in result
        assert "Example:" not in result or "Example: " in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_complex_description(self, mock_query):
        """Test option with complex HTML description."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "programs.zsh.enable",
                    "option_type": "boolean",
                    "option_description": (
                        "<rendered-html><p>Whether to configure <strong>zsh</strong> as an interactive shell. "
                        "See <a href='https://www.zsh.org/'>zsh docs</a>.</p></rendered-html>"
                    ),
                }
            }
        ]

        result = await nixos_info("programs.zsh.enable", type="option")
        assert "Option: programs.zsh.enable" in result
        assert "Type: boolean" in result
        assert "Whether to configure zsh as an interactive shell" in result
        assert "<strong>" not in result
        assert "<a href=" not in result
        assert "</p>" not in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_hierarchical_names(self, mock_query):
        """Test options with deeply nested hierarchical names."""
        test_cases = [
            "services.xserver.displayManager.gdm.enable",
            "networking.firewall.allowedTCPPorts",
            "users.users.root.hashedPassword",
            "boot.loader.systemd-boot.enable",
        ]

        for option_name in test_cases:
            mock_query.return_value = [
                {
                    "_source": {
                        "option_name": option_name,
                        "option_type": "test-type",
                        "option_description": f"Test option: {option_name}",
                    }
                }
            ]

            result = await nixos_info(option_name, type="option")

            # Verify query uses correct field
            query = mock_query.call_args[0][1]
            assert query["bool"]["must"][1]["term"]["option_name"] == option_name

            # Verify result
            assert f"Option: {option_name}" in result
            assert f"Test option: {option_name}" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_api_error(self, mock_query):
        """Test error handling for API failures."""
        mock_query.side_effect = Exception("Connection timeout")

        result = await nixos_info("services.nginx.enable", type="option")
        assert "Error (ERROR): Connection timeout" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nixos_info_option_empty_fields(self, mock_query):
        """Test handling of empty option fields."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "test.option",
                    "option_type": "",
                    "option_description": "",
                    "option_default": "",
                    "option_example": "",
                }
            }
        ]

        result = await nixos_info("test.option", type="option")
        assert "Option: test.option" in result
        # Empty fields should not appear in output
        lines = result.split("\n")
        for line in lines:
            if ":" in line and line != "Option: test.option":
                _, value = line.split(":", 1)
                assert value.strip() != ""  # No empty values after colon


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixosInfoOptionsIntegration:
    """Integration tests against real NixOS API."""

    @pytest.mark.asyncio
    async def test_real_option_lookup_services_nginx_enable(self):
        """Test real lookup of services.nginx.enable."""
        result = await nixos_info("services.nginx.enable", type="option")

        if "NOT_FOUND" in result:
            # If not found, it might be due to API changes
            pytest.skip("Option services.nginx.enable not found in current channel")

        assert "Option: services.nginx.enable" in result
        assert "Type: boolean" in result
        assert "nginx" in result.lower() or "web server" in result.lower()

    @pytest.mark.asyncio
    async def test_real_option_lookup_common_options(self):
        """Test real lookup of commonly used options."""
        common_options = [
            "boot.loader.grub.enable",
            "networking.hostName",
            "services.openssh.enable",
            "users.users",
        ]

        for option_name in common_options:
            result = await nixos_info(option_name, type="option")

            # These options should exist
            if "NOT_FOUND" not in result:
                assert f"Option: {option_name}" in result
                assert "Type:" in result or "Description:" in result

    @pytest.mark.asyncio
    async def test_real_option_not_found(self):
        """Test real lookup of non-existent option."""
        result = await nixos_info("services.completely.fake.option", type="option")
        assert "Error (NOT_FOUND):" in result
        assert "services.completely.fake.option" in result


class TestNixosInfoOptionScenarios:
    """Test nixos_info option lookups in various scenarios."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_services_nginx_enable_info(self, mock_query):
        """Test getting info about services.nginx.enable option."""
        # Mock the API response
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.nginx.enable",
                    "option_type": "boolean",
                    "option_description": "<rendered-html><p>Whether to enable Nginx Web Server.</p>\n</rendered-html>",
                    "option_default": "false",
                    "option_example": "true",
                }
            }
        ]

        # User query equivalent: "Get details about services.nginx.enable"
        result = await nixos_info("services.nginx.enable", type="option")

        # Expected behaviors:
        # 1. Should use correct option name without .keyword suffix
        # 2. Should display option info clearly
        # 3. Should strip HTML tags from description
        # 4. Should show all available fields

        # Verify the query
        assert mock_query.called
        query = mock_query.call_args[0][1]
        assert query["bool"]["must"][1]["term"]["option_name"] == "services.nginx.enable"
        assert "option_name.keyword" not in str(query)

        # Verify output format
        assert "Option: services.nginx.enable" in result
        assert "Type: boolean" in result
        assert "Description: Whether to enable Nginx Web Server." in result
        assert "Default: false" in result
        assert "Example: true" in result

        # Verify HTML stripping
        assert "<rendered-html>" not in result
        assert "</p>" not in result
        assert "<p>" not in result

        # Verify it's plain text
        assert all(char not in result for char in ["<", ">"] if char not in ["<name>"])

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_nested_option_lookup(self, mock_query):
        """Test looking up deeply nested options."""
        # Mock response for nested option
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.xserver.displayManager.gdm.enable",
                    "option_type": "boolean",
                    "option_description": "Whether to enable the GDM display manager",
                    "option_default": "false",
                }
            }
        ]

        # User query: "Show me the services.xserver.displayManager.gdm.enable option"
        result = await nixos_info("services.xserver.displayManager.gdm.enable", type="option")

        # Expected: should handle long hierarchical names correctly
        assert "Option: services.xserver.displayManager.gdm.enable" in result
        assert "Type: boolean" in result
        assert "GDM display manager" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_option_not_found_behavior(self, mock_query):
        """Test behavior when option is not found."""
        # Mock empty response
        mock_query.return_value = []

        # User query: "Get info about services.fake.option"
        result = await nixos_info("services.fake.option", type="option")

        # Expected: clear error message
        assert "Error (NOT_FOUND):" in result
        assert "services.fake.option" in result
        assert "Option" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_common_options_lookup(self, mock_query):
        """Test looking up commonly used NixOS options."""
        common_options = [
            ("boot.loader.grub.enable", "boolean", "Whether to enable the GRUB boot loader"),
            ("networking.hostName", "string", "The hostname of the machine"),
            ("services.openssh.enable", "boolean", "Whether to enable the OpenSSH daemon"),
            ("users.users.<name>.home", "path", "The user's home directory"),
        ]

        for option_name, option_type, description in common_options:
            mock_query.return_value = [
                {
                    "_source": {
                        "option_name": option_name,
                        "option_type": option_type,
                        "option_description": description,
                    }
                }
            ]

            result = await nixos_info(option_name, type="option")

            # Verify each option is handled correctly
            assert f"Option: {option_name}" in result
            assert f"Type: {option_type}" in result
            assert description in result or description.replace("<name>", "_name_") in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_option_with_complex_html(self, mock_query):
        """Test handling of options with complex HTML descriptions."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "programs.firefox.policies",
                    "option_type": "attribute set",
                    "option_description": (
                        "<rendered-html>"
                        "<p>Firefox policies configuration. See "
                        "<a href='https://github.com/mozilla/policy-templates'>Mozilla Policy Templates</a> "
                        "for available options. You can use <code>lib.mkForce</code> to override.</p>"
                        "<p><strong>Note:</strong> This requires Firefox ESR or Firefox with "
                        "enterprise policy support.</p>"
                        "</rendered-html>"
                    ),
                }
            }
        ]

        result = await nixos_info("programs.firefox.policies", type="option")

        # Should clean up HTML nicely
        assert "Option: programs.firefox.policies" in result
        assert "Firefox policies configuration" in result
        assert "Mozilla Policy Templates" in result

        # No HTML artifacts
        assert "<rendered-html>" not in result
        assert "<p>" not in result
        assert "<a href=" not in result
        assert "<strong>" not in result
        assert "</p>" not in result

    @pytest.mark.integration
    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    @pytest.mark.asyncio
    async def test_real_option_lookup_integration(self):
        """Integration test for real option lookup behavior."""
        # Test with a real option that should exist
        result = await nixos_info("services.nginx.enable", type="option")

        if "NOT_FOUND" not in result:
            # If found (API is available)
            assert "Option: services.nginx.enable" in result
            assert "Type:" in result  # Should have a type
            assert "nginx" in result.lower() or "web server" in result.lower()

            # No XML/HTML
            assert "<" not in result
            assert ">" not in result
        else:
            # If not found, verify error format
            assert "Error (NOT_FOUND):" in result
            assert "services.nginx.enable" in result


# ===== Content from test_option_info_improvements.py =====
class TestOptionInfoImprovements:
    """Test improvements to option info lookup based on real usage."""

    @pytest.mark.asyncio
    async def test_home_manager_info_requires_exact_match(self):
        """Test that home_manager_info requires exact option names."""
        # User tries "programs.git" but it's not a valid option
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Return git-related options but no exact "programs.git" match
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Git username"},
            ]

            result = await home_manager_info("programs.git")
            assert "not found" in result.lower()

        # User provides exact option name
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
            ]

            result = await home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result
            assert "Type: boolean" in result

    @pytest.mark.asyncio
    async def test_browse_then_info_workflow(self):
        """Test the recommended workflow: browse first, then get info."""
        # Step 1: Browse to find exact names
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Git username"},
                {"name": "programs.git.userEmail", "type": "string", "description": "Git email"},
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG key"},
            ]

            result = await home_manager_options_by_prefix("programs.git")
            assert "programs.git.enable" in result
            assert "programs.git.signing.key" in result

        # Step 2: Get info with exact name from browse results
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG signing key"},
            ]

            result = await home_manager_info("programs.git.signing.key")
            assert "Option: programs.git.signing.key" in result
            assert "Type: string" in result

    @pytest.mark.asyncio
    async def test_darwin_info_same_behavior(self):
        """Test that darwin_info has the same exact-match requirement."""
        # Partial name fails
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            ]

            result = await darwin_info("system")
            assert "not found" in result.lower()

        # Exact name works
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            ]

            result = await darwin_info("system.defaults.dock.autohide")
            assert "Option: system.defaults.dock.autohide" in result

    @pytest.mark.asyncio
    async def test_common_user_mistakes(self):
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
                result = await home_manager_info(wrong_name)
                assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_helpful_error_messages_needed(self):
        """Test that error messages could be more helpful."""
        # When option not found, could suggest using browse
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            result = await home_manager_info("programs.git")
            assert "not found" in result.lower()
            # Could improve by suggesting: "Try home_manager_options_by_prefix('programs.git')"

    @pytest.mark.asyncio
    async def test_case_sensitivity(self):
        """Test that option lookup is case-sensitive."""
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git"},
            ]

            # Exact case works
            result = await home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result

        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            # Wrong case fails
            result = await home_manager_info("programs.Git.enable")
            assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_nested_option_discovery(self):
        """Test discovering deeply nested options."""
        # User wants to find git.signing options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.signing.key", "type": "null or string", "description": "GPG key ID"},
                {"name": "programs.git.signing.signByDefault", "type": "boolean", "description": "Auto-sign"},
                {"name": "programs.git.signing.gpgPath", "type": "string", "description": "Path to gpg"},
            ]

            result = await home_manager_options_by_prefix("programs.git.signing")
            assert "programs.git.signing.key" in result
            assert "programs.git.signing.signByDefault" in result

    @pytest.mark.asyncio
    async def test_option_info_with_complex_types(self):
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

                result = await home_manager_info(option_name)
                assert f"Type: {type_str}" in result

    @pytest.mark.asyncio
    async def test_stats_limitations_are_clear(self):
        """Test that stats function limitations are clearly communicated."""
        # Home Manager stats
        result = await home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result

        # Darwin stats
        result = await darwin_stats()
        assert "nix-darwin Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
