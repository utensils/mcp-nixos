#!/usr/bin/env python3
"""Evaluation tests for NixHub tool behavior with AI assistants."""

import pytest
from mcp_nixos.server import nixhub_package_versions


class TestNixHubEvaluations:
    """Test expected AI assistant behaviors when using NixHub tools."""

    def test_finding_older_ruby_version(self):
        """Test that older Ruby versions can be found with appropriate limit."""
        # Scenario: User asks for Ruby 2.6
        # Default behavior (limit=10) won't find it
        result_default = nixhub_package_versions("ruby", limit=10)
        assert "2.6" not in result_default, "Ruby 2.6 shouldn't appear with default limit"

        # But with higher limit, it should be found
        result_extended = nixhub_package_versions("ruby", limit=50)
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

    def test_incremental_search_strategy(self):
        """Test that AI should incrementally increase limit to find older versions."""
        # Test different limit values to understand the pattern
        limits_and_oldest = []

        for limit in [10, 20, 30, 40, 50]:
            result = nixhub_package_versions("ruby", limit=limit)
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

    def test_version_not_in_nixhub(self):
        """Test behavior when a version truly doesn't exist."""
        # Test with a very high limit to ensure we check everything
        result = nixhub_package_versions("ruby", limit=50)

        # Ruby 2.4 and earlier should not exist in NixHub (based on actual data)
        assert "2.4." not in result, "Ruby 2.4.x should not be available in NixHub"
        assert "2.3." not in result, "Ruby 2.3.x should not be available in NixHub"
        assert "1.9." not in result, "Ruby 1.9.x should not be available in NixHub"

        # But 2.5, 2.6 and 2.7 should exist (based on actual API data)
        assert "2.5." in result, "Ruby 2.5.x should be available"
        assert "2.6." in result, "Ruby 2.6.x should be available"
        assert "2.7." in result, "Ruby 2.7.x should be available"

    def test_package_version_recommendations(self):
        """Test that results provide actionable information."""
        result = nixhub_package_versions("python3", limit=5)

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
    def test_version_2_search_patterns(self, package, min_limit_for_v2):
        """Test that version 2.x of packages requires higher limits."""
        # Low limit shouldn't find version 2
        result_low = nixhub_package_versions(package, limit=10)

        # Count version 2.x occurrences
        v2_count_low = sum(1 for line in result_low.split("\n") if "• Version 2." in line)

        # High limit might find version 2 (if it exists)
        result_high = nixhub_package_versions(package, limit=50)
        v2_count_high = sum(1 for line in result_high.split("\n") if "• Version 2." in line)

        # Higher limit should find more or equal v2 versions
        assert v2_count_high >= v2_count_low, f"Higher limit should find at least as many v2 {package} versions"


class TestNixHubAIBehaviorPatterns:
    """Test patterns that AI assistants should follow when using NixHub."""

    def test_ai_should_try_higher_limits_for_older_versions(self):
        """Document the pattern AI should follow for finding older versions."""
        # Pattern 1: Start with default/low limit
        result1 = nixhub_package_versions("ruby", limit=10)

        # If user asks for version not found, AI should:
        # Pattern 2: Increase limit significantly
        result2 = nixhub_package_versions("ruby", limit=50)

        # Verify this pattern works
        assert "2.6" not in result1, "Step 1: Default search doesn't find old version"
        assert "2.6" in result2, "Step 2: Extended search finds old version"

        # This demonstrates the expected AI behavior pattern

    def test_ai_response_for_missing_version(self):
        """Test how AI should respond when version is not found."""
        # Search for Ruby 2.6 with default limit
        result = nixhub_package_versions("ruby", limit=10)

        if "2.6" not in result:
            # AI should recognize the pattern and try higher limit
            extended_result = nixhub_package_versions("ruby", limit=50)

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

    def test_efficient_search_strategy(self):
        """Test efficient strategies for finding specific versions."""
        # Strategy 1: If looking for very old version, start with higher limit
        # This is more efficient than multiple calls

        # Inefficient: Multiple calls
        calls_made = 0
        found = False
        for limit in [10, 20, 30, 40, 50]:
            calls_made += 1
            result = nixhub_package_versions("ruby", limit=limit)
            if "2.6.7" in result:
                found = True
                break

        assert found, "Should eventually find Ruby 2.6.7"
        assert calls_made > 3, "Inefficient approach needs multiple calls"

        # Efficient: Start with reasonable limit for old versions
        result = nixhub_package_versions("ruby", limit=50)
        assert "2.6.7" in result, "Efficient approach finds it in one call"

        # This demonstrates why AI should use higher limits for older versions
