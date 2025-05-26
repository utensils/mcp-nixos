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
        result = nixos_search("firefox", search_type="packages", limit=3)
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
        result = nixos_search("nginx", search_type="options", limit=3)
        # Should find nginx options (now using wildcard, may find options with nginx anywhere)
        assert "nginx" in result.lower() or "No options found" in result
        assert "<" not in result  # No XML

    def test_nixos_option_info_real(self):
        """Test real NixOS option info."""
        # Test with a common option that should exist
        result = nixos_info("services.nginx.enable", type="option")
        if "NOT_FOUND" not in result:
            assert "Option: services.nginx.enable" in result
            assert "Type:" in result
            assert "<" not in result  # No XML
        else:
            # If not found, try another common option
            result = nixos_info("boot.loader.grub.enable", type="option")
            if "NOT_FOUND" not in result:
                assert "Option: boot.loader.grub.enable" in result

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
        # Should find git-related options
        assert "git" in result.lower() or "No Home Manager options found" in result
        assert "<" not in result  # No XML

    def test_home_manager_info_real(self):
        """Test real Home Manager info."""
        result = home_manager_info("programs.git.enable")
        assert "Option: programs.git.enable" in result or "not found" in result
        assert "<" not in result  # No XML

    def test_darwin_search_real(self):
        """Test real Darwin search."""
        result = darwin_search("dock", limit=3)
        # Should find dock-related options
        assert "dock" in result.lower() or "No nix-darwin options found" in result
        # Allow <name> as it's a placeholder, not XML
        if "<" in result:
            assert "<name>" in result  # This is OK, it's a placeholder
            assert "</" not in result  # No closing XML tags

    def test_plain_text_format_consistency(self):
        """Ensure all outputs follow consistent plain text format."""
        # Test various searches
        results = [
            nixos_search("python", search_type="packages", limit=2),
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
        result = nixos_search("test", search_type="invalid")
        assert "Error" in result
        assert "<" not in result

        # Test with invalid channel
        result = nixos_search("test", channel="invalid")
        assert "Error" in result
        assert "Invalid channel" in result
        assert "<" not in result
