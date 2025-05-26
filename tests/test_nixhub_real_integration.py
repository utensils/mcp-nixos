#!/usr/bin/env python3
"""Real integration tests for NixHub API (requires network)."""

import pytest
from mcp_nixos.server import nixhub_package_versions


@pytest.mark.integration
class TestNixHubRealIntegration:
    """Test actual NixHub API calls."""

    def test_nixhub_real_firefox(self):
        """Test fetching real data for Firefox package."""
        result = nixhub_package_versions("firefox", limit=3)

        # Should not be an error
        assert "Error" not in result

        # Should contain expected fields
        assert "Package: firefox" in result
        assert "Web browser" in result  # Part of description
        assert "Total versions:" in result
        assert "Version history" in result
        assert "• Version" in result
        assert "Nixpkgs commit:" in result

        # Should have valid commit hashes (40 hex chars)
        lines = result.split("\n")
        commit_lines = [line for line in lines if "Nixpkgs commit:" in line]
        assert len(commit_lines) > 0

        for line in commit_lines:
            # Extract commit hash
            if "(warning" not in line:
                commit = line.split("Nixpkgs commit:")[-1].strip()
                assert len(commit) == 40
                assert all(c in "0123456789abcdefABCDEF" for c in commit)

    def test_nixhub_real_python(self):
        """Test fetching real data for Python package."""
        result = nixhub_package_versions("python3", limit=2)

        # Should not be an error
        assert "Error" not in result

        # Should contain python-specific content
        assert "Package: python3" in result
        assert "Version history" in result

    def test_nixhub_real_nonexistent(self):
        """Test fetching data for non-existent package."""
        result = nixhub_package_versions("definitely-not-a-real-package-xyz123")

        # Should be a proper error
        assert "Error (NOT_FOUND):" in result
        assert "not found in NixHub" in result

    def test_nixhub_real_usage_hint(self):
        """Test that usage hint appears for packages with commits."""
        result = nixhub_package_versions("git", limit=1)

        if "Error" not in result and "Nixpkgs commit:" in result:
            assert "To use a specific version" in result
            assert "Pin nixpkgs to the commit hash" in result
