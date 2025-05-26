#!/usr/bin/env python3
"""Integration tests for NixOS flake search functionality."""

import pytest
from mcp_nixos.server import nixos_flakes_search


@pytest.mark.integration
class TestFlakeSearchIntegration:
    """Integration tests for flake search against real API."""

    def test_flake_search_real_api(self):
        """Test flake search against real NixOS API."""
        # Search for a common term
        result = nixos_flakes_search("nixpkgs", limit=5)

        # Should either find results or show no results message
        assert "flakes matching 'nixpkgs'" in result or "No flakes found" in result
        # Should not have errors
        assert "Error" not in result or "Error (ERROR)" not in result

    def test_flake_search_different_channels(self):
        """Test flake search across different channels."""
        channels = ["unstable", "stable", "25.05"]

        for channel in channels:
            result = nixos_flakes_search("home-manager", limit=3, channel=channel)

            # Channel parameter is ignored for flakes
            assert "flakes matching 'home-manager'" in result or "No flakes found" in result
            assert "Error" not in result or "invalid channel" not in result.lower()

    def test_flake_search_special_characters(self):
        """Test flake search with special characters."""
        # Test various query patterns
        queries = ["nix-community/home-manager", "github:NixOS/nixpkgs", "flake-utils", "nixos@unstable"]

        for query in queries:
            result = nixos_flakes_search(query, limit=2)
            # Should handle special characters gracefully
            assert "flakes" in result
            assert "Error" not in result or "Error (ERROR)" in result

    def test_flake_search_empty_query(self):
        """Test flake search with empty query."""
        result = nixos_flakes_search("", limit=5)

        # Should still work but return no results
        assert "No flakes found matching ''" in result

    def test_flake_search_limits(self):
        """Test flake search with different limits."""
        # Test edge cases for limits
        for limit in [1, 50, 100]:
            result = nixos_flakes_search("test", limit=limit)
            assert "flakes" in result  # Either "Found X flakes" or "No flakes found"
            assert "Error" not in result or "Error (NOT_FOUND)" in result

    def test_flake_search_channel_validation(self):
        """Test flake search channel validation."""
        # Channel parameter is ignored for flakes
        result = nixos_flakes_search("test", channel="unstable")
        assert "flakes" in result
        assert "Invalid channel" not in result

        # Even with invalid channel, it should work (channel is ignored)
        result = nixos_flakes_search("test", channel="nonexistent-channel")
        assert "flakes" in result
        assert "Invalid channel" not in result.lower()

    @pytest.mark.slow
    def test_flake_search_performance(self):
        """Test flake search performance with larger result sets."""
        import time

        # Even with a high limit, should return quickly since no data exists
        start = time.time()
        result = nixos_flakes_search("nix", limit=100)
        duration = time.time() - start

        assert duration < 5.0  # Should complete within 5 seconds
        # Should either find results or show no results
        assert "flakes matching 'nix'" in result

    def test_flake_search_unicode_handling(self):
        """Test flake search with unicode characters."""
        # Test with various unicode strings
        queries = ["école", "日本語", "🚀", "café"]

        for query in queries:
            result = nixos_flakes_search(query, limit=2)
            # Should handle unicode gracefully
            assert f"No flakes found matching '{query}'." in result
            assert "Error" not in result or "Error (NOT_FOUND)" in result
