#!/usr/bin/env python3
"""Simple evaluation tests for NixOS flake search functionality."""

import pytest
from mcp_nixos.server import nixos_flakes_search


@pytest.mark.evals
class TestFlakeSearchSimpleEvals:
    """Simple evaluation tests for flake search functionality."""

    def test_flake_search_returns_plain_text(self):
        """Test that flake search always returns plain text, not XML."""
        # Test various queries
        queries = ["nixpkgs", "home-manager", "flake-utils", ""]

        for query in queries:
            result = nixos_flakes_search(query)

            # Check for plain text markers
            assert isinstance(result, str)
            assert "<" not in result or ">" not in result  # No XML tags
            assert "Error" in result or "No flakes found" in result or "Found" in result

            # Should not contain XML-like structures
            assert "<response>" not in result
            assert "</response>" not in result
            assert "<flake>" not in result

    def test_flake_search_error_messages(self):
        """Test that flake search provides helpful error messages."""
        # Channel parameter is ignored for flakes, so no channel errors
        result = nixos_flakes_search("test", channel="invalid-2099")
        assert "flakes" in result
        assert "Invalid channel" not in result.lower()

        # Test invalid limit
        result = nixos_flakes_search("test", limit=1000)
        assert "Error (ERROR):" in result
        assert "Limit must be 1-100" in result

    def test_flake_search_no_results_message(self):
        """Test the informative message when no flakes are found."""
        # Use a very specific query that won't match
        result = nixos_flakes_search("xyzzy-nonexistent-flake-99999")

        # If no results, should provide helpful message
        if "No flakes found" in result:
            assert "Try searching for:" in result
            assert "GitHub" in result
            assert "FlakeHub" in result
        else:
            # If it somehow finds results, that's ok too
            assert "Found" in result and "flakes matching" in result

    def test_flake_search_channel_handling(self):
        """Test that flake search handles different channels correctly."""
        channels = ["unstable", "stable", "25.05"]

        for channel in channels:
            result = nixos_flakes_search("nixpkgs", channel=channel, limit=5)

            # Should not error on valid channels
            assert "Error (ERROR): Invalid channel" not in result
            # Should return consistent format
            assert "No flakes found" in result or "Found" in result

    def test_flake_search_query_flexibility(self):
        """Test that flake search handles various query formats."""
        # Different query formats that users might try
        queries = [
            "github:NixOS/nixpkgs",
            "nixpkgs",
            "NixOS/nixpkgs",
            "flake-utils",
            "numtide/flake-utils",
            "home-manager@master",
        ]

        for query in queries:
            result = nixos_flakes_search(query, limit=10)

            # Should handle all query formats gracefully
            assert "Error" not in result or "Error (NOT_FOUND)" in result
            assert isinstance(result, str)
            assert len(result) > 0

    def test_flake_search_output_format_consistency(self):
        """Test that flake search output format is consistent."""
        result = nixos_flakes_search("test", limit=5)

        # Check structure
        lines = result.split("\n")
        assert len(lines) >= 1  # Should have at least one line

        if "No flakes found" in result:
            # No results format
            assert "Try searching for:" in result or "Browse flakes at:" in result
            assert any("GitHub" in line or "FlakeHub" in line for line in lines)
        else:
            # Results format
            assert "Found" in lines[0] and "flakes matching" in lines[0]
            # Should have bullet points for results
            assert any("•" in line for line in lines)


# Basic smoke test
if __name__ == "__main__":
    print("Running flake search evaluation tests...")
    test = TestFlakeSearchSimpleEvals()

    try:
        test.test_flake_search_returns_plain_text()
        print("✓ Plain text output test passed")
    except AssertionError as e:
        print(f"✗ Plain text output test failed: {e}")

    try:
        test.test_flake_search_no_results_message()
        print("✓ No results message test passed")
    except AssertionError as e:
        print(f"✗ No results message test failed: {e}")

    try:
        test.test_flake_search_channel_handling()
        print("✓ Channel handling test passed")
    except AssertionError as e:
        print(f"✗ Channel handling test failed: {e}")

    print("\nAll basic eval tests completed!")
