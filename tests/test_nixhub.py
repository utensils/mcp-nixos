#!/usr/bin/env python3
"""Tests for NixHub API integration."""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
nixhub_find_version = get_tool_function("nixhub_find_version")
nixhub_package_versions = get_tool_function("nixhub_package_versions")


class TestNixHubIntegration:
    """Test NixHub.io API integration."""

    @pytest.mark.asyncio
    async def test_nixhub_valid_package(self):
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

            result = await nixhub_package_versions("firefox", limit=5)

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

    @pytest.mark.asyncio
    async def test_nixhub_package_not_found(self):
        """Test handling of non-existent package."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404)

            result = await nixhub_package_versions("nonexistent-package")

            assert "Error (NOT_FOUND):" in result
            assert "nonexistent-package" in result
            assert "not found in NixHub" in result

    @pytest.mark.asyncio
    async def test_nixhub_service_error(self):
        """Test handling of service errors."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=503)

            result = await nixhub_package_versions("firefox")

            assert "Error (SERVICE_ERROR):" in result
            assert "temporarily unavailable" in result

    @pytest.mark.asyncio
    async def test_nixhub_invalid_package_name(self):
        """Test validation of package names."""
        # Test empty name
        result = await nixhub_package_versions("")
        assert "Error" in result
        assert "Package name is required" in result

        # Test invalid characters
        result = await nixhub_package_versions("package$name")
        assert "Error" in result
        assert "Invalid package name" in result

        # Test SQL injection attempt
        result = await nixhub_package_versions("package'; DROP TABLE--")
        assert "Error" in result
        assert "Invalid package name" in result

    @pytest.mark.asyncio
    async def test_nixhub_limit_validation(self):
        """Test limit parameter validation."""
        mock_response = {"name": "test", "releases": []}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            # Test limits
            result = await nixhub_package_versions("test", limit=0)
            assert "Error" in result
            assert "Limit must be between 1 and 50" in result

            result = await nixhub_package_versions("test", limit=51)
            assert "Error" in result
            assert "Limit must be between 1 and 50" in result

    @pytest.mark.asyncio
    async def test_nixhub_empty_releases(self):
        """Test handling of package with no version history."""
        mock_response = {"name": "test-package", "summary": "Test package", "releases": []}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = await nixhub_package_versions("test-package")

            assert "Package: test-package" in result
            assert "No version history available" in result

    @pytest.mark.asyncio
    async def test_nixhub_limit_application(self):
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

            result = await nixhub_package_versions("test", limit=5)

            assert "showing 5 of 20" in result
            # Count version entries (each starts with "• Version")
            version_count = result.count("• Version")
            assert version_count == 5

    @pytest.mark.asyncio
    async def test_nixhub_commit_hash_validation(self):
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

            result = await nixhub_package_versions("test")

            # Valid hash should not have warning
            assert "abcdef0123456789abcdef0123456789abcdef01" in result
            assert "abcdef0123456789abcdef0123456789abcdef01 (warning" not in result

            # Invalid hash should have warning
            assert "invalid-hash (warning: invalid format)" in result

    @pytest.mark.asyncio
    async def test_nixhub_usage_hint(self):
        """Test that usage hint is shown when commit hashes are available."""
        mock_response = {"name": "test", "releases": [{"version": "1.0", "platforms": [{"commit_hash": "a" * 40}]}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            result = await nixhub_package_versions("test")

            assert "To use a specific version" in result
            assert "Pin nixpkgs to the commit hash" in result

    @pytest.mark.asyncio
    async def test_nixhub_network_timeout(self):
        """Test handling of network timeout."""
        import requests

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Connection timed out")

            result = await nixhub_package_versions("firefox")

            assert "Error (TIMEOUT):" in result
            assert "timed out" in result

    @pytest.mark.asyncio
    async def test_nixhub_json_parse_error(self):
        """Test handling of invalid JSON response."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=Mock(side_effect=ValueError("Invalid JSON")))

            result = await nixhub_package_versions("firefox")

            assert "Error (PARSE_ERROR):" in result
            assert "Failed to parse" in result

    @pytest.mark.asyncio
    async def test_nixhub_attribute_path_display(self):
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

            result = await nixhub_package_versions("firefox")

            # Should not show attribute for firefox (same as name)
            assert "Attribute: firefox\n" not in result

            # Should show attribute for firefox-esr (different from name)
            assert "Attribute: firefox-esr" in result

    @pytest.mark.asyncio
    async def test_nixhub_no_duplicate_commits(self):
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

            result = await nixhub_package_versions("ruby")

            # Count how many times the commit hash appears
            commit_count = result.count("a" * 40)
            # Should only appear once, not 4 times
            assert commit_count == 1, f"Commit hash appeared {commit_count} times, expected 1"


# ===== Content from test_nixhub_real_integration.py =====
@pytest.mark.integration
class TestNixHubRealIntegration:
    """Test actual NixHub API calls."""

    @pytest.mark.asyncio
    async def test_nixhub_real_firefox(self):
        """Test fetching real data for Firefox package."""
        result = await nixhub_package_versions("firefox", limit=3)

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

    @pytest.mark.asyncio
    async def test_nixhub_real_python(self):
        """Test fetching real data for Python package."""
        result = await nixhub_package_versions("python3", limit=2)

        # Should not be an error
        assert "Error" not in result

        # Should contain python-specific content
        assert "Package: python3" in result
        assert "Version history" in result

    @pytest.mark.asyncio
    async def test_nixhub_real_nonexistent(self):
        """Test fetching data for non-existent package."""
        result = await nixhub_package_versions("definitely-not-a-real-package-xyz123")

        # Should be a proper error
        assert "Error (NOT_FOUND):" in result
        assert "not found in NixHub" in result

    @pytest.mark.asyncio
    async def test_nixhub_real_usage_hint(self):
        """Test that usage hint appears for packages with commits."""
        result = await nixhub_package_versions("git", limit=1)

        if "Error" not in result and "Nixpkgs commit:" in result:
            assert "To use a specific version" in result
            assert "Pin nixpkgs to the commit hash" in result


# ===== Content from test_nixhub_find_version.py =====
class TestNixHubFindVersion:
    """Test the smart version finding functionality."""

    @pytest.mark.asyncio
    async def test_find_existing_version(self):
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

            result = await nixhub_find_version("ruby", "2.6.7")

            assert "✓ Found ruby version 2.6.7" in result
            assert "2021-07-05 19:22 UTC" in result
            assert "3e0ce8c5d478d06b37a4faa7a4cc8642c6bb97de" in result
            assert "ruby_2_6" in result
            assert "To use this version:" in result

    @pytest.mark.asyncio
    async def test_version_not_found(self):
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

            result = await nixhub_find_version("python3", "3.5.9")

            assert "✗ python3 version 3.5.9 not found" in result
            assert "Newest: 3.12.0" in result
            assert "Oldest: 3.7.7" in result
            assert "Major versions available: 3" in result
            assert "Version 3.5.9 is older than the oldest available" in result
            assert "Alternatives:" in result

    @pytest.mark.asyncio
    async def test_incremental_search(self):
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
            result = await nixhub_find_version("ruby", "2.6.7")

            assert "✓ Found ruby version 2.6.7" in result
            # Should have tried with limit=10 first, then limit=25 and found it
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_package_not_found(self):
        """Test when package doesn't exist."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=404)

            result = await nixhub_find_version("nonexistent", "1.0.0")

            assert "Error (NOT_FOUND):" in result
            assert "nonexistent" in result

    @pytest.mark.asyncio
    async def test_package_name_mapping(self):
        """Test that common package names are mapped correctly."""
        mock_response = {"name": "python", "releases": [{"version": "3.12.0"}]}

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: mock_response)

            # Test "python" -> "python3" mapping
            await nixhub_find_version("python", "3.12.0")

            call_args = mock_get.call_args[0][0]
            assert "python3" in call_args
            assert "python3?_data=" in call_args

    @pytest.mark.asyncio
    async def test_version_sorting(self):
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

            result = await nixhub_find_version("test", "3.7.0")

            # Check correct version ordering
            assert "Newest: 3.11.1" in result
            assert "Oldest: 3.8.15" in result

    @pytest.mark.asyncio
    async def test_version_comparison_logic(self):
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
            result = await nixhub_find_version("test", "3.6.0")
            assert "Version 3.6.0 is older than the oldest available (3.7.0)" in result

            # Test same major, older minor
            result = await nixhub_find_version("test", "3.5.0")
            assert "Version 3.5.0 is older than the oldest available (3.7.0)" in result

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test various error conditions."""
        # Test timeout
        import requests

        with patch("requests.get", side_effect=requests.Timeout("Timeout")):
            result = await nixhub_find_version("test", "1.0.0")
            assert "Error (TIMEOUT):" in result

        # Test service error
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=503)
            result = await nixhub_find_version("test", "1.0.0")
            assert "Error (SERVICE_ERROR):" in result

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation."""
        # Empty package name
        result = await nixhub_find_version("", "1.0.0")
        assert "Package name is required" in result

        # Empty version
        result = await nixhub_find_version("test", "")
        assert "Version is required" in result

        # Invalid package name
        result = await nixhub_find_version("test$package", "1.0.0")
        assert "Invalid package name" in result

    @pytest.mark.asyncio
    async def test_commit_hash_deduplication(self):
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

            result = await nixhub_find_version("test", "1.0.0")

            # Should only show each commit once
            assert result.count("a" * 40) == 1
            assert result.count("b" * 40) == 1


# ===== Content from test_nixhub_evals.py =====
class TestNixHubEvaluations:
    """Test expected AI assistant behaviors when using NixHub tools."""

    @pytest.mark.asyncio
    async def test_finding_older_ruby_version(self):
        """Test that older Ruby versions can be found with appropriate limit."""
        # Scenario: User asks for Ruby 2.6
        # Default behavior (limit=10) won't find it
        result_default = await nixhub_package_versions("ruby", limit=10)
        assert "2.6" not in result_default, "Ruby 2.6 shouldn't appear with default limit"

        # But with higher limit, it should be found
        result_extended = await nixhub_package_versions("ruby", limit=50)
        assert "2.6.7" in result_extended, "Ruby 2.6.7 should be found with limit=50"
        assert "ruby_2_6" in result_extended, "Should show ruby_2_6 attribute"

        # Extract the commit hash for Ruby 2.6.7
        lines = result_extended.split("\n")
        in_ruby_26 = False
        commit_hash = None

        for line in lines:
            if "• Version 2.6.7" in line:
                in_ruby_26 = True
            elif in_ruby_26 and "Nixpkgs commit:" in line:
                commit_hash = line.split("Nixpkgs commit:")[-1].strip()
                break
            elif in_ruby_26 and line.startswith("• Version"):
                # Moved to next version
                break

        assert commit_hash is not None, "Should find a commit hash for Ruby 2.6.7"
        assert len(commit_hash) == 40, f"Commit hash should be 40 chars, got {len(commit_hash)}"
        assert commit_hash == "3e0ce8c5d478d06b37a4faa7a4cc8642c6bb97de", "Should find specific commit for Ruby 2.6.7"

    @pytest.mark.asyncio
    async def test_incremental_search_strategy(self):
        """Test that AI should incrementally increase limit to find older versions."""
        # Test different limit values to understand the pattern
        limits_and_oldest = []

        for limit in [10, 20, 30, 40, 50]:
            result = await nixhub_package_versions("ruby", limit=limit)
            lines = result.split("\n")

            # Find oldest version in this result
            oldest_version = None
            for line in lines:
                if "• Version" in line:
                    version = line.split("• Version")[1].strip()
                    oldest_version = version

            has_ruby_26 = "2.6" in result
            limits_and_oldest.append((limit, oldest_version, has_ruby_26))

        # Verify that Ruby 2.6 requires a higher limit than default
        # Based on actual API data (as of testing), Ruby 2.6 appears around position 18-20
        # This position may change as new versions are added
        assert not limits_and_oldest[0][2], "Ruby 2.6 should NOT be in limit=10"

        # Find where Ruby 2.6 first appears
        first_appearance = None
        for limit, _, has_26 in limits_and_oldest:
            if has_26:
                first_appearance = limit
                break

        assert first_appearance is not None, "Ruby 2.6 should be found with higher limits"
        assert first_appearance > 10, f"Ruby 2.6 requires limit > 10 (found at limit={first_appearance})"

        # This demonstrates the AI needs to increase limit when searching for older versions

    @pytest.mark.asyncio
    async def test_version_not_in_nixhub(self):
        """Test behavior when a version truly doesn't exist."""
        # Test with a very high limit to ensure we check everything
        result = await nixhub_package_versions("ruby", limit=50)

        # Ruby 2.5 and earlier should not exist in NixHub (based on actual data)
        assert "2.5." not in result, "Ruby 2.5.x should not be available in NixHub"
        assert "2.4." not in result, "Ruby 2.4.x should not be available in NixHub"
        assert "2.3." not in result, "Ruby 2.3.x should not be available in NixHub"
        assert "1.9." not in result, "Ruby 1.9.x should not be available in NixHub"

        # But 2.6 and 2.7 should exist (based on actual API data)
        assert "2.6." in result, "Ruby 2.6.x should be available"
        assert "2.7." in result, "Ruby 2.7.x should be available"

    @pytest.mark.asyncio
    async def test_package_version_recommendations(self):
        """Test that results provide actionable information."""
        result = await nixhub_package_versions("python3", limit=5)

        # Should include usage instructions
        assert "To use a specific version" in result
        assert "Pin nixpkgs to the commit hash" in result

        # Should have commit hashes
        assert "Nixpkgs commit:" in result

        # Should have attribute paths
        assert "python3" in result or "python_3" in result

    @pytest.mark.parametrize(
        "package,min_limit_for_v2",
        [
            ("ruby", 40),  # Ruby 2.x appears around position 40
            ("python", 30),  # Python 2.x (if available) would need higher limit
        ],
    )
    @pytest.mark.asyncio
    async def test_version_2_search_patterns(self, package, min_limit_for_v2):
        """Test that version 2.x of packages requires higher limits."""
        # Low limit shouldn't find version 2
        result_low = await nixhub_package_versions(package, limit=10)

        # Count version 2.x occurrences
        v2_count_low = sum(1 for line in result_low.split("\n") if "• Version 2." in line)

        # High limit might find version 2 (if it exists)
        result_high = await nixhub_package_versions(package, limit=50)
        v2_count_high = sum(1 for line in result_high.split("\n") if "• Version 2." in line)

        # Higher limit should find more or equal v2 versions
        assert v2_count_high >= v2_count_low, f"Higher limit should find at least as many v2 {package} versions"


class TestNixHubAIBehaviorPatterns:
    """Test patterns that AI assistants should follow when using NixHub."""

    @pytest.mark.asyncio
    async def test_ai_should_try_higher_limits_for_older_versions(self):
        """Document the pattern AI should follow for finding older versions."""
        # Pattern 1: Start with default/low limit
        result1 = await nixhub_package_versions("ruby", limit=10)

        # If user asks for version not found, AI should:
        # Pattern 2: Increase limit significantly
        result2 = await nixhub_package_versions("ruby", limit=50)

        # Verify this pattern works
        assert "2.6" not in result1, "Step 1: Default search doesn't find old version"
        assert "2.6" in result2, "Step 2: Extended search finds old version"

        # This demonstrates the expected AI behavior pattern

    @pytest.mark.asyncio
    async def test_ai_response_for_missing_version(self):
        """Test how AI should respond when version is not found."""
        # Search for Ruby 2.6 with default limit
        result = await nixhub_package_versions("ruby", limit=10)

        if "2.6" not in result:
            # AI should recognize the pattern and try higher limit
            extended_result = await nixhub_package_versions("ruby", limit=50)

            assert "2.6" in extended_result, "Should find Ruby 2.6 with higher limit"

            # Extract and validate commit hash
            lines = extended_result.split("\n")
            commit_found = False

            for i, line in enumerate(lines):
                if "• Version 2.6.7" in line and i + 1 < len(lines):
                    # Check next few lines for commit
                    for offset in range(1, 5):
                        if i + offset >= len(lines):
                            break
                        if "Nixpkgs commit:" in lines[i + offset]:
                            commit = lines[i + offset].split("Nixpkgs commit:")[-1].strip()
                            assert len(commit) == 40, "Commit hash should be 40 chars"
                            commit_found = True
                            break
                    break

            assert commit_found, "Should find commit hash for Ruby 2.6.7"
            assert "Attribute:" in extended_result, "Should have attribute path"

    @pytest.mark.asyncio
    async def test_efficient_search_strategy(self):
        """Test efficient strategies for finding specific versions."""
        # Strategy 1: If looking for very old version, start with higher limit
        # This is more efficient than multiple calls

        # Inefficient: Multiple calls
        calls_made = 0
        found = False
        for limit in [10, 20, 30, 40, 50]:
            calls_made += 1
            result = await nixhub_package_versions("ruby", limit=limit)
            if "2.6.7" in result:
                found = True
                break

        assert found, "Should eventually find Ruby 2.6.7"
        assert calls_made > 3, "Inefficient approach needs multiple calls"

        # Efficient: Start with reasonable limit for old versions
        result = await nixhub_package_versions("ruby", limit=50)
        assert "2.6.7" in result, "Efficient approach finds it in one call"

        # This demonstrates why AI should use higher limits for older versions
