#!/usr/bin/env python3
"""Tests for the nixhub_find_version smart search function."""

from unittest.mock import patch, Mock
from mcp_nixos.server import nixhub_find_version


class TestNixHubFindVersion:
    """Test the smart version finding functionality."""

    def test_find_existing_version(self):
        """Test finding a version that exists."""
        mock_response = {
            "name": "ruby",
            "releases": [
                {"version": "3.2.0", "platforms": [{"commit_hash": "a" * 40, "attribute_path": "ruby_3_2"}]},
                {
                    "version": "2.6.7",
                    "last_updated": "2021-07-05T19:22:00Z",
                    "platforms_summary": "Linux and macOS",
                    "platforms": [
                        {"commit_hash": "3e0ce8c5d478d06b37a4faa7a4cc8642c6bb97de", "attribute_path": "ruby_2_6"}
                    ],
                },
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_find_version("ruby", "2.6.7")

            assert "✓ Found ruby version 2.6.7" in result
            assert "2021-07-05 19:22 UTC" in result
            assert "3e0ce8c5d478d06b37a4faa7a4cc8642c6bb97de" in result
            assert "ruby_2_6" in result
            assert "To use this version:" in result

    def test_version_not_found(self):
        """Test when a version doesn't exist."""
        mock_response = {
            "name": "python",
            "releases": [
                {"version": "3.12.0"},
                {"version": "3.11.0"},
                {"version": "3.10.0"},
                {"version": "3.9.0"},
                {"version": "3.8.0"},
                {"version": "3.7.7"},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_find_version("python3", "3.5.9")

            assert "✗ python3 version 3.5.9 not found" in result
            assert "Newest: 3.12.0" in result
            assert "Oldest: 3.7.7" in result
            assert "Major versions available: 3" in result
            assert "Version 3.5.9 is older than the oldest available" in result
            assert "Alternatives:" in result

    def test_incremental_search(self):
        """Test that search tries multiple limits."""
        # Create releases where target is at position 15
        releases = []
        for i in range(20, 0, -1):
            if i == 6:  # Position 14 (20-6=14)
                releases.append(
                    {
                        "version": "2.6.7",
                        "platforms": [{"commit_hash": "abc" * 13 + "d", "attribute_path": "ruby_2_6"}],
                    }
                )
            else:
                releases.append({"version": f"3.{i}.0"})

        mock_response = {"name": "ruby", "releases": releases}

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return Mock(status_code=200, json=lambda: mock_response)

        with patch("requests.get", side_effect=side_effect):
            result = nixhub_find_version("ruby", "2.6.7")

            assert "✓ Found ruby version 2.6.7" in result
            # Should have tried with limit=10 first, then limit=25 and found it
            assert call_count == 2

    def test_package_not_found(self):
        """Test when package doesn't exist."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404)

            result = nixhub_find_version("nonexistent", "1.0.0")

            assert "Error (NOT_FOUND):" in result
            assert "nonexistent" in result

    def test_package_name_mapping(self):
        """Test that common package names are mapped correctly."""
        mock_response = {"name": "python", "releases": [{"version": "3.12.0"}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            # Test "python" -> "python3" mapping
            nixhub_find_version("python", "3.12.0")

            call_args = mock_get.call_args[0][0]
            assert "python3" in call_args
            assert "python3?_data=" in call_args

    def test_version_sorting(self):
        """Test that versions are sorted correctly."""
        mock_response = {
            "name": "test",
            "releases": [
                {"version": "3.9.9"},
                {"version": "3.10.0"},
                {"version": "3.8.15"},
                {"version": "3.11.1"},
                {"version": "3.10.12"},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_find_version("test", "3.7.0")

            # Check correct version ordering
            assert "Newest: 3.11.1" in result
            assert "Oldest: 3.8.15" in result

    def test_version_comparison_logic(self):
        """Test version comparison for determining if requested is older."""
        mock_response = {
            "name": "test",
            "releases": [
                {"version": "3.8.0"},
                {"version": "3.7.0"},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            # Test older version
            result = nixhub_find_version("test", "3.6.0")
            assert "Version 3.6.0 is older than the oldest available (3.7.0)" in result

            # Test same major, older minor
            result = nixhub_find_version("test", "3.5.0")
            assert "Version 3.5.0 is older than the oldest available (3.7.0)" in result

    def test_error_handling(self):
        """Test various error conditions."""
        # Test timeout
        import requests

        with patch("requests.get", side_effect=requests.Timeout("Timeout")):
            result = nixhub_find_version("test", "1.0.0")
            assert "Error (TIMEOUT):" in result

        # Test service error
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=503)
            result = nixhub_find_version("test", "1.0.0")
            assert "Error (SERVICE_ERROR):" in result

    def test_input_validation(self):
        """Test input validation."""
        # Empty package name
        result = nixhub_find_version("", "1.0.0")
        assert "Package name is required" in result

        # Empty version
        result = nixhub_find_version("test", "")
        assert "Version is required" in result

        # Invalid package name
        result = nixhub_find_version("test$package", "1.0.0")
        assert "Invalid package name" in result

    def test_commit_hash_deduplication(self):
        """Test that duplicate commit hashes are deduplicated."""
        mock_response = {
            "name": "test",
            "releases": [
                {
                    "version": "1.0.0",
                    "platforms": [
                        {"commit_hash": "a" * 40, "attribute_path": "test"},
                        {"commit_hash": "a" * 40, "attribute_path": "test"},  # Duplicate
                        {"commit_hash": "b" * 40, "attribute_path": "test2"},
                    ],
                }
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = nixhub_find_version("test", "1.0.0")

            # Should only show each commit once
            assert result.count("a" * 40) == 1
            assert result.count("b" * 40) == 1
