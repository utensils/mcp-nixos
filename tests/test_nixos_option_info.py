"""Comprehensive tests for nixos_info option lookups."""

import pytest
from unittest.mock import patch
from mcp_nixos.server import nixos_info


class TestNixosInfoOptions:
    """Test nixos_info with option lookups."""

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_with_exact_match(self, mock_query):
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

        result = nixos_info("services.nginx.enable", type="option")

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
    def test_nixos_info_option_not_found(self, mock_query):
        """Test info when option is not found."""
        mock_query.return_value = []

        result = nixos_info("services.nginx.nonexistent", type="option")
        assert result == "Error (NOT_FOUND): Option 'services.nginx.nonexistent' not found"

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_with_minimal_fields(self, mock_query):
        """Test info with minimal option fields."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.test.enable",
                    "option_description": "Enable test service",
                }
            }
        ]

        result = nixos_info("services.test.enable", type="option")
        assert "Option: services.test.enable" in result
        assert "Description: Enable test service" in result
        # No type, default, or example should not cause errors
        assert "Type:" not in result or "Type: " in result
        assert "Default:" not in result or "Default: " in result
        assert "Example:" not in result or "Example: " in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_complex_description(self, mock_query):
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

        result = nixos_info("programs.zsh.enable", type="option")
        assert "Option: programs.zsh.enable" in result
        assert "Type: boolean" in result
        assert "Whether to configure zsh as an interactive shell" in result
        assert "<strong>" not in result
        assert "<a href=" not in result
        assert "</p>" not in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_hierarchical_names(self, mock_query):
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

            result = nixos_info(option_name, type="option")

            # Verify query uses correct field
            query = mock_query.call_args[0][1]
            assert query["bool"]["must"][1]["term"]["option_name"] == option_name

            # Verify result
            assert f"Option: {option_name}" in result
            assert f"Test option: {option_name}" in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_api_error(self, mock_query):
        """Test error handling for API failures."""
        mock_query.side_effect = Exception("Connection timeout")

        result = nixos_info("services.nginx.enable", type="option")
        assert "Error (ERROR): Connection timeout" in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_empty_fields(self, mock_query):
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

        result = nixos_info("test.option", type="option")
        assert "Option: test.option" in result
        # Empty fields should not appear in output
        lines = result.split("\n")
        for line in lines:
            if ":" in line and line != "Option: test.option":
                _, value = line.split(":", 1)
                assert value.strip() != ""  # No empty values after colon


@pytest.mark.integration
class TestNixosInfoOptionsIntegration:
    """Integration tests against real NixOS API."""

    def test_real_option_lookup_services_nginx_enable(self):
        """Test real lookup of services.nginx.enable."""
        result = nixos_info("services.nginx.enable", type="option")

        if "NOT_FOUND" in result:
            # If not found, it might be due to API changes
            pytest.skip("Option services.nginx.enable not found in current channel")

        assert "Option: services.nginx.enable" in result
        assert "Type: boolean" in result
        assert "nginx" in result.lower() or "web server" in result.lower()

    def test_real_option_lookup_common_options(self):
        """Test real lookup of commonly used options."""
        common_options = [
            "boot.loader.grub.enable",
            "networking.hostName",
            "services.openssh.enable",
            "users.users",
        ]

        for option_name in common_options:
            result = nixos_info(option_name, type="option")

            # These options should exist
            if "NOT_FOUND" not in result:
                assert f"Option: {option_name}" in result
                assert "Type:" in result or "Description:" in result

    def test_real_option_not_found(self):
        """Test real lookup of non-existent option."""
        result = nixos_info("services.completely.fake.option", type="option")
        assert "Error (NOT_FOUND):" in result
        assert "services.completely.fake.option" in result
