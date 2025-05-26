"""Evaluation tests for nixos_info option functionality."""

import pytest
from unittest.mock import patch
from mcp_nixos.server import nixos_info


class TestNixosInfoOptionEvals:
    """Evaluation tests for nixos_info with options."""

    @patch("mcp_nixos.server.es_query")
    def test_eval_services_nginx_enable_info(self, mock_query):
        """Evaluate getting info about services.nginx.enable option."""
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
        result = nixos_info("services.nginx.enable", type="option")

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
    def test_eval_nested_option_lookup(self, mock_query):
        """Evaluate looking up deeply nested options."""
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
        result = nixos_info("services.xserver.displayManager.gdm.enable", type="option")

        # Expected: should handle long hierarchical names correctly
        assert "Option: services.xserver.displayManager.gdm.enable" in result
        assert "Type: boolean" in result
        assert "GDM display manager" in result

    @patch("mcp_nixos.server.es_query")
    def test_eval_option_not_found_behavior(self, mock_query):
        """Evaluate behavior when option is not found."""
        # Mock empty response
        mock_query.return_value = []

        # User query: "Get info about services.fake.option"
        result = nixos_info("services.fake.option", type="option")

        # Expected: clear error message
        assert "Error (NOT_FOUND):" in result
        assert "services.fake.option" in result
        assert "Option" in result

    @patch("mcp_nixos.server.es_query")
    def test_eval_common_options_lookup(self, mock_query):
        """Evaluate looking up commonly used NixOS options."""
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

            result = nixos_info(option_name, type="option")

            # Verify each option is handled correctly
            assert f"Option: {option_name}" in result
            assert f"Type: {option_type}" in result
            assert description in result or description.replace("<name>", "_name_") in result

    @patch("mcp_nixos.server.es_query")
    def test_eval_option_with_complex_html(self, mock_query):
        """Evaluate handling of options with complex HTML descriptions."""
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

        result = nixos_info("programs.firefox.policies", type="option")

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
    def test_eval_real_option_lookup_integration(self):
        """Integration test: evaluate real option lookup behavior."""
        # Test with a real option that should exist
        result = nixos_info("services.nginx.enable", type="option")

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
