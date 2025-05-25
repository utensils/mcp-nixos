"""Real integration tests that verify actual API responses."""

import pytest
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_info,
    darwin_search,
)


@pytest.mark.integration
class TestRealIntegration:
    """Test against real APIs to ensure implementation works."""

    def test_nixos_search_real(self):
        """Test real NixOS package search."""
        result = nixos_search("firefox", type="packages", limit=3)
        assert "Found" in result
        assert "firefox" in result
        assert "•" in result  # Bullet point
        assert "(" in result  # Version in parentheses
        assert "<" not in result  # No XML

    def test_nixos_info_real(self):
        """Test real NixOS package info."""
        result = nixos_info("firefox", type="package")
        assert "Package: firefox" in result
        assert "Version:" in result
        assert "Description:" in result
        assert "<" not in result  # No XML

    def test_nixos_option_search_real(self):
        """Test real NixOS option search."""
        result = nixos_search("nginx", type="options", limit=3)
        # Should find nginx options
        assert "services.nginx" in result or "No options found" in result
        assert "<" not in result  # No XML

    def test_nixos_stats_real(self):
        """Test real NixOS stats."""
        result = nixos_stats()
        assert "NixOS Statistics" in result
        assert "Packages:" in result
        assert "Options:" in result
        assert "<" not in result  # No XML

    def test_home_manager_search_real(self):
        """Test real Home Manager search."""
        result = home_manager_search("git", limit=3)
        assert "programs.git" in result or "No Home Manager options found" in result
        assert "<" not in result  # No XML

    def test_home_manager_info_real(self):
        """Test real Home Manager info."""
        result = home_manager_info("programs.git.enable")
        assert "Option: programs.git.enable" in result or "not found" in result
        assert "<" not in result  # No XML

    def test_darwin_search_real(self):
        """Test real Darwin search."""
        result = darwin_search("dock", limit=3)
        assert "system.defaults" in result or "No nix-darwin options found" in result
        assert "<" not in result  # No XML

    def test_plain_text_format_consistency(self):
        """Ensure all outputs follow consistent plain text format."""
        # Test various searches
        results = [
            nixos_search("python", type="packages", limit=2),
            home_manager_search("shell", limit=2),
            darwin_search("system", limit=2),
        ]

        for result in results:
            # Check for common plain text patterns
            if "Found" in result:
                assert ":" in result  # Colon after "Found X matching"
                assert "•" in result  # Bullet points for items
            elif "No" in result:
                assert "found" in result  # "No X found"

            # Ensure no XML tags
            assert "<" not in result
            assert ">" not in result

    def test_error_handling_plain_text(self):
        """Test error messages are plain text."""
        # Test with invalid type
        result = nixos_search("test", type="invalid")
        assert "Error" in result
        assert "<" not in result

        # Test with invalid channel
        result = nixos_search("test", channel="invalid")
        assert "Error" in result
        assert "Invalid channel" in result
        assert "<" not in result
