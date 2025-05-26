#!/usr/bin/env python3
"""Tests for NixHub API integration."""

from unittest.mock import patch, Mock
from mcp_nixos.server import nixhub_package_versions


class TestNixHubIntegration:
    """Test NixHub.io API integration."""

    def test_nixhub_valid_package(self):
        """Test fetching version history for a valid package."""
        mock_response = {
            "name": "firefox",
            "summary": "Web browser built from Firefox source tree",
            "releases": [
                {
                    "version": "138.0.4",
                    "last_updated": "2025-05-19T23:16:24Z",
                    "platforms_summary": "Linux and macOS",
                    "outputs_summary": "",
                    "platforms": [
                        {"attribute_path": "firefox", "commit_hash": "359c442b7d1f6229c1dc978116d32d6c07fe8440"}
                    ],
                },
                {
                    "version": "137.0.2",
                    "last_updated": "2025-05-15T10:30:00Z",
                    "platforms_summary": "Linux and macOS",
                    "platforms": [
                        {"attribute_path": "firefox", "commit_hash": "abcdef1234567890abcdef1234567890abcdef12"}
                    ],
                },
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("firefox", limit=5)

            # Check the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "firefox" in call_args[0][0]
            assert "_data=routes" in call_args[0][0]

            # Check output format
            assert "Package: firefox" in result
            assert "Web browser built from Firefox source tree" in result
            assert "Total versions: 2" in result
            assert "Version 138.0.4" in result
            assert "Version 137.0.2" in result
            assert "359c442b7d1f6229c1dc978116d32d6c07fe8440" in result
            assert "2025-05-19 23:16 UTC" in result

    def test_nixhub_package_not_found(self):
        """Test handling of non-existent package."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404)

            result = nixhub_package_versions("nonexistent-package")

            assert "Error (NOT_FOUND):" in result
            assert "nonexistent-package" in result
            assert "not found in NixHub" in result

    def test_nixhub_service_error(self):
        """Test handling of service errors."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=503)

            result = nixhub_package_versions("firefox")

            assert "Error (SERVICE_ERROR):" in result
            assert "temporarily unavailable" in result

    def test_nixhub_invalid_package_name(self):
        """Test validation of package names."""
        # Test empty name
        result = nixhub_package_versions("")
        assert "Error" in result
        assert "Package name is required" in result

        # Test invalid characters
        result = nixhub_package_versions("package$name")
        assert "Error" in result
        assert "Invalid package name" in result

        # Test SQL injection attempt
        result = nixhub_package_versions("package'; DROP TABLE--")
        assert "Error" in result
        assert "Invalid package name" in result

    def test_nixhub_limit_validation(self):
        """Test limit parameter validation."""
        mock_response = {"name": "test", "releases": []}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            # Test limits
            result = nixhub_package_versions("test", limit=0)
            assert "Error" in result
            assert "Limit must be between 1 and 50" in result

            result = nixhub_package_versions("test", limit=51)
            assert "Error" in result
            assert "Limit must be between 1 and 50" in result

    def test_nixhub_empty_releases(self):
        """Test handling of package with no version history."""
        mock_response = {"name": "test-package", "summary": "Test package", "releases": []}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("test-package")

            assert "Package: test-package" in result
            assert "No version history available" in result

    def test_nixhub_limit_application(self):
        """Test that limit is correctly applied."""
        # Create 20 releases
        releases = []
        for i in range(20):
            releases.append(
                {
                    "version": f"1.0.{i}",
                    "last_updated": "2025-01-01T00:00:00Z",
                    "platforms": [{"attribute_path": "test", "commit_hash": f"{'a' * 40}"}],
                }
            )

        mock_response = {"name": "test", "releases": releases}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("test", limit=5)

            assert "showing 5 of 20" in result
            # Count version entries (each starts with "• Version")
            version_count = result.count("• Version")
            assert version_count == 5

    def test_nixhub_commit_hash_validation(self):
        """Test validation of commit hashes."""
        mock_response = {
            "name": "test",
            "releases": [
                {"version": "1.0", "platforms": [{"commit_hash": "abcdef0123456789abcdef0123456789abcdef01"}]},
                {"version": "2.0", "platforms": [{"commit_hash": "invalid-hash"}]},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("test")

            # Valid hash should not have warning
            assert "abcdef0123456789abcdef0123456789abcdef01" in result
            assert "abcdef0123456789abcdef0123456789abcdef01 (warning" not in result

            # Invalid hash should have warning
            assert "invalid-hash (warning: invalid format)" in result

    def test_nixhub_usage_hint(self):
        """Test that usage hint is shown when commit hashes are available."""
        mock_response = {"name": "test", "releases": [{"version": "1.0", "platforms": [{"commit_hash": "a" * 40}]}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("test")

            assert "To use a specific version" in result
            assert "Pin nixpkgs to the commit hash" in result

    def test_nixhub_network_timeout(self):
        """Test handling of network timeout."""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Connection timed out")

            result = nixhub_package_versions("firefox")

            assert "Error (TIMEOUT):" in result
            assert "timed out" in result

    def test_nixhub_json_parse_error(self):
        """Test handling of invalid JSON response."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=Mock(side_effect=ValueError("Invalid JSON")))

            result = nixhub_package_versions("firefox")

            assert "Error (PARSE_ERROR):" in result
            assert "Failed to parse" in result

    def test_nixhub_attribute_path_display(self):
        """Test that attribute path is shown when different from package name."""
        mock_response = {
            "name": "firefox",
            "releases": [
                {
                    "version": "1.0",
                    "platforms": [
                        {"attribute_path": "firefox", "commit_hash": "a" * 40},
                        {"attribute_path": "firefox-esr", "commit_hash": "b" * 40},
                    ],
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("firefox")

            # Should not show attribute for firefox (same as name)
            assert "Attribute: firefox\n" not in result

            # Should show attribute for firefox-esr (different from name)
            assert "Attribute: firefox-esr" in result

    def test_nixhub_no_duplicate_commits(self):
        """Test that duplicate commit hashes are not shown multiple times."""
        mock_response = {
            "name": "ruby",
            "releases": [
                {
                    "version": "3.2.0",
                    "platforms": [
                        {"attribute_path": "ruby_3_2", "commit_hash": "a" * 40},
                        {"attribute_path": "ruby_3_2", "commit_hash": "a" * 40},
                        {"attribute_path": "ruby_3_2", "commit_hash": "a" * 40},
                        {"attribute_path": "ruby", "commit_hash": "a" * 40},
                    ],
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_package_versions("ruby")

            # Count how many times the commit hash appears
            commit_count = result.count("a" * 40)
            # Should only appear once, not 4 times
            assert commit_count == 1, f"Commit hash appeared {commit_count} times, expected 1"
