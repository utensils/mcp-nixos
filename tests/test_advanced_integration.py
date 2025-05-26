#!/usr/bin/env python3
"""Advanced integration tests for MCP-NixOS server with real APIs."""

import pytest
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_info,
    home_manager_list_options,
    home_manager_options_by_prefix,
    darwin_search,
    darwin_info,
    darwin_options_by_prefix,
)


@pytest.mark.integration
class TestAdvancedIntegration:
    """Test advanced scenarios with real APIs."""

    def test_nixos_search_special_characters(self):
        """Test searching with special characters and symbols."""
        # Test with hyphens
        result = nixos_search("ruby-build", search_type="packages")
        assert "ruby-build" in result or "No packages found" in result

        # Test with dots
        result = nixos_search("lib.so", search_type="packages")
        # Should handle dots in search gracefully
        assert "Error" not in result

        # Test with underscores
        result = nixos_search("python3_12", search_type="packages")
        assert "Error" not in result

    def test_nixos_search_case_sensitivity(self):
        """Test case sensitivity in searches."""
        # Search with different cases
        result_lower = nixos_search("firefox", search_type="packages", limit=5)
        result_upper = nixos_search("FIREFOX", search_type="packages", limit=5)
        result_mixed = nixos_search("FireFox", search_type="packages", limit=5)

        # All should find firefox (case-insensitive search)
        assert "firefox" in result_lower.lower()
        assert "firefox" in result_upper.lower()
        assert "firefox" in result_mixed.lower()

    def test_nixos_option_hierarchical_search(self):
        """Test searching hierarchical option names."""
        # Search for nested options
        result = nixos_search("systemd.services", search_type="options", limit=10)
        assert "systemd.services" in result or "No options found" in result

        # Search for deeply nested options
        result = nixos_search("networking.firewall.allowedTCPPorts", search_type="options", limit=5)
        # Should handle long option names
        assert "Error" not in result

    def test_nixos_cross_channel_consistency(self):
        """Test that different channels return consistent data structure."""
        channels = ["unstable", "stable"]

        for channel in channels:
            # Stats should work for all channels
            stats = nixos_stats(channel=channel)
            assert "Packages:" in stats
            assert "Options:" in stats
            assert "Error" not in stats

            # Search should return same structure
            search = nixos_search("git", search_type="packages", channel=channel, limit=3)
            if "Found" in search:
                assert "•" in search  # Bullet points
                assert "(" in search  # Version in parentheses

    def test_nixos_info_edge_packages(self):
        """Test info retrieval for packages with unusual names."""
        # Test package with version in name
        edge_packages = [
            "python3",  # Common package
            "gcc",  # Short name
            "gnome.nautilus",  # Namespaced package
        ]

        for pkg in edge_packages:
            result = nixos_info(pkg, type="package")
            if "not found" not in result:
                assert "Package:" in result
                assert "Version:" in result

    def test_home_manager_search_complex_queries(self):
        """Test complex search patterns in Home Manager."""
        # Search for options with dots
        result = home_manager_search("programs.git.delta", limit=10)
        if "Found" in result:
            assert "programs.git.delta" in result

        # Search for options with underscores
        result = home_manager_search("enable_", limit=10)
        # Should handle underscore in search
        assert "Error" not in result

        # Search for very short terms
        result = home_manager_search("qt", limit=5)
        assert "Error" not in result

    def test_home_manager_category_completeness(self):
        """Test that list_options returns all major categories."""
        result = home_manager_list_options()

        # Check for expected major categories
        expected_categories = ["programs", "services", "home", "xdg"]
        for category in expected_categories:
            assert category in result

        # Verify format consistency
        assert "total)" in result
        assert "• " in result
        assert " options)" in result

    def test_home_manager_prefix_navigation(self):
        """Test navigating option hierarchy with prefixes."""
        # Start with top-level
        result = home_manager_options_by_prefix("programs")
        if "Found" not in result and "found)" in result:
            # Drill down to specific program
            result_git = home_manager_options_by_prefix("programs.git")
            if "found)" in result_git:
                assert "programs.git" in result_git

                # Drill down further
                result_delta = home_manager_options_by_prefix("programs.git.delta")
                assert "Error" not in result_delta

    def test_home_manager_info_name_variants(self):
        """Test info retrieval with different name formats."""
        # Test with placeholder names
        result = home_manager_info("programs.firefox.profiles.<name>.settings")
        # Should handle <name> placeholders
        if "not found" not in result:
            assert "Option:" in result

    def test_darwin_search_macos_specific(self):
        """Test searching macOS-specific options."""
        # Search for macOS-specific terms
        macos_terms = ["homebrew", "launchd", "defaults", "dock"]

        for term in macos_terms:
            result = darwin_search(term, limit=5)
            if "Found" in result:
                assert term in result.lower()
                assert "•" in result

    def test_darwin_system_defaults_exploration(self):
        """Test exploring system.defaults hierarchy."""
        # List all system.defaults options
        result = darwin_options_by_prefix("system.defaults")

        if "found)" in result:
            # Should have many system defaults
            assert "system.defaults" in result

            # Test specific subcategories
            subcategories = ["NSGlobalDomain", "dock", "finder"]
            for subcat in subcategories:
                sub_result = darwin_options_by_prefix(f"system.defaults.{subcat}")
                # Should not error even if no results
                assert "Error" not in sub_result

    def test_darwin_info_detailed_options(self):
        """Test retrieving detailed darwin option info."""
        # Test well-known options
        known_options = ["system.defaults.dock.autohide", "environment.systemPath", "programs.zsh.enable"]

        for opt in known_options:
            result = darwin_info(opt)
            if "not found" not in result:
                assert "Option:" in result
                # Darwin options often have descriptions
                assert "Description:" in result or "Type:" in result

    def test_performance_large_searches(self):
        """Test performance with large result sets."""
        import time

        # NixOS large search
        start = time.time()
        result = nixos_search("lib", search_type="packages", limit=100)
        elapsed = time.time() - start
        assert elapsed < 30  # Should complete within 30 seconds
        assert "Error" not in result

        # Home Manager large listing
        start = time.time()
        result = home_manager_list_options()
        elapsed = time.time() - start
        assert elapsed < 30  # HTML parsing should be reasonably fast

    def test_concurrent_api_calls(self):
        """Test handling concurrent API calls."""
        import concurrent.futures

        def search_nixos(query):
            return nixos_search(query, limit=5)

        queries = ["python", "ruby", "nodejs", "rust", "go"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(search_nixos, queries))

        # All searches should complete without errors
        for result in results:
            assert "Error" not in result or "No packages found" in result

    def test_unicode_handling(self):
        """Test handling of unicode in searches and results."""
        # Search with unicode
        result = nixos_search("文字", search_type="packages", limit=5)
        # Should handle unicode gracefully
        assert "Error" not in result

        # Some packages might have unicode in descriptions
        result = nixos_info("font-awesome")
        if "not found" not in result:
            # Should display unicode properly if present
            assert "Package:" in result

    def test_empty_and_whitespace_queries(self):
        """Test handling of empty and whitespace-only queries."""
        # Empty string
        result = nixos_search("", search_type="packages", limit=5)
        assert "No packages found" in result or "Found" in result

        # Whitespace only
        result = home_manager_search("   ", limit=5)
        assert "Error" not in result

        # Newlines and tabs
        result = darwin_search("\n\t", limit=5)
        assert "Error" not in result

    def test_option_type_complexity(self):
        """Test handling of complex option types."""
        # Search for options with complex types
        result = nixos_search("extraConfig", search_type="options", limit=10)

        if "Found" in result and "Type:" in result:
            # Complex types like "null or string" should be handled
            assert "Error" not in result

    def test_api_timeout_resilience(self):
        """Test behavior with slow API responses."""
        # This might occasionally fail if API is very slow
        # Using programs type which might have more processing
        result = nixos_search("compiler", search_type="programs", limit=50)

        # Should either succeed or timeout gracefully
        assert "packages found" in result or "programs found" in result or "Error" in result

    def test_html_parsing_edge_cases(self):
        """Test HTML parsing with real documentation quirks."""
        # Test getting options that might have complex HTML
        complex_prefixes = ["programs.neovim.plugins", "services.nginx.virtualHosts", "systemd.services"]

        for prefix in complex_prefixes:
            result = home_manager_options_by_prefix(prefix)
            # Should handle any HTML structure
            assert "Error" not in result or "No Home Manager options found" in result
