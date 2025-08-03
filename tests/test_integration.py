"""Real integration tests that verify actual API responses."""

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
darwin_info = get_tool_function("darwin_info")
darwin_options_by_prefix = get_tool_function("darwin_options_by_prefix")
darwin_search = get_tool_function("darwin_search")
home_manager_info = get_tool_function("home_manager_info")
home_manager_list_options = get_tool_function("home_manager_list_options")
home_manager_search = get_tool_function("home_manager_search")
home_manager_options_by_prefix = get_tool_function("home_manager_options_by_prefix")
nixos_info = get_tool_function("nixos_info")
nixos_search = get_tool_function("nixos_search")
nixos_stats = get_tool_function("nixos_stats")


@pytest.mark.integration
class TestRealIntegration:
    """Test against real APIs to ensure implementation works."""

    @pytest.mark.asyncio
    async def test_nixos_search_real(self):
        """Test real NixOS package search."""
        result = await nixos_search("firefox", search_type="packages", limit=3)
        assert "Found" in result
        assert "firefox" in result
        assert "•" in result  # Bullet point
        assert "(" in result  # Version in parentheses
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_nixos_info_real(self):
        """Test real NixOS package info."""
        result = await nixos_info("firefox", type="package")
        assert "Package: firefox" in result
        assert "Version:" in result
        assert "Description:" in result
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_nixos_option_search_real(self):
        """Test real NixOS option search."""
        result = await nixos_search("nginx", search_type="options", limit=3)
        # Should find nginx options (now using wildcard, may find options with nginx anywhere)
        assert "nginx" in result.lower() or "No options found" in result
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_nixos_option_info_real(self):
        """Test real NixOS option info."""
        # Test with a common option that should exist
        result = await nixos_info("services.nginx.enable", type="option")
        if "NOT_FOUND" not in result:
            assert "Option: services.nginx.enable" in result
            assert "Type:" in result
            assert "<" not in result  # No XML
        else:
            # If not found, try another common option
            result = await nixos_info("boot.loader.grub.enable", type="option")
            if "NOT_FOUND" not in result:
                assert "Option: boot.loader.grub.enable" in result

    @pytest.mark.asyncio
    async def test_nixos_stats_real(self):
        """Test real NixOS stats."""
        result = await nixos_stats()
        assert "NixOS Statistics" in result
        assert "Packages:" in result
        assert "Options:" in result
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_home_manager_search_real(self):
        """Test real Home Manager search."""
        result = await home_manager_search("git", limit=3)
        # Should find git-related options
        assert "git" in result.lower() or "No Home Manager options found" in result
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_home_manager_info_real(self):
        """Test real Home Manager info."""
        result = await home_manager_info("programs.git.enable")
        assert "Option: programs.git.enable" in result or "not found" in result
        assert "<" not in result  # No XML

    @pytest.mark.asyncio
    async def test_darwin_search_real(self):
        """Test real Darwin search."""
        result = await darwin_search("dock", limit=3)
        # Should find dock-related options
        assert "dock" in result.lower() or "No nix-darwin options found" in result
        # Allow <name> as it's a placeholder, not XML
        if "<" in result:
            assert "<name>" in result  # This is OK, it's a placeholder
            assert "</" not in result  # No closing XML tags

    @pytest.mark.asyncio
    async def test_plain_text_format_consistency(self):
        """Ensure all outputs follow consistent plain text format."""
        # Test various searches
        results = [
            await nixos_search("python", search_type="packages", limit=2),
            await home_manager_search("shell", limit=2),
            await darwin_search("system", limit=2),
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

    @pytest.mark.asyncio
    async def test_error_handling_plain_text(self):
        """Test error messages are plain text."""
        # Test with invalid type
        result = await nixos_search("test", search_type="invalid")
        assert "Error" in result
        assert "<" not in result

        # Test with invalid channel
        result = await nixos_search("test", channel="invalid")
        assert "Error" in result
        assert "Invalid channel" in result
        assert "<" not in result


# ===== Content from test_advanced_integration.py =====
@pytest.mark.integration
class TestAdvancedIntegration:
    """Test advanced scenarios with real APIs."""

    @pytest.mark.asyncio
    async def test_nixos_search_special_characters(self):
        """Test searching with special characters and symbols."""
        # Test with hyphens
        result = await nixos_search("ruby-build", search_type="packages")
        assert "ruby-build" in result or "No packages found" in result

        # Test with dots
        result = await nixos_search("lib.so", search_type="packages")
        # Should handle dots in search gracefully
        assert "Error" not in result

        # Test with underscores
        result = await nixos_search("python3_12", search_type="packages")
        assert "Error" not in result

    @pytest.mark.asyncio
    async def test_nixos_search_case_sensitivity(self):
        """Test case sensitivity in searches."""
        # Search with different cases
        result_lower = await nixos_search("firefox", search_type="packages", limit=5)
        result_upper = await nixos_search("FIREFOX", search_type="packages", limit=5)
        result_mixed = await nixos_search("FireFox", search_type="packages", limit=5)

        # All should find firefox (case-insensitive search)
        assert "firefox" in result_lower.lower()
        assert "firefox" in result_upper.lower()
        assert "firefox" in result_mixed.lower()

    @pytest.mark.asyncio
    async def test_nixos_option_hierarchical_search(self):
        """Test searching hierarchical option names."""
        # Search for nested options
        result = await nixos_search("systemd.services", search_type="options", limit=10)
        assert "systemd.services" in result or "No options found" in result

        # Search for deeply nested options
        result = await nixos_search("networking.firewall.allowedTCPPorts", search_type="options", limit=5)
        # Should handle long option names
        assert "Error" not in result

    @pytest.mark.asyncio
    async def test_nixos_cross_channel_consistency(self):
        """Test that different channels return consistent data structure."""
        channels = ["unstable", "stable"]

        for channel in channels:
            # Stats should work for all channels
            stats = await nixos_stats(channel=channel)
            assert "Packages:" in stats
            assert "Options:" in stats
            assert "Error" not in stats

            # Search should return same structure
            search = await nixos_search("git", search_type="packages", channel=channel, limit=3)
            if "Found" in search:
                assert "•" in search  # Bullet points
                assert "(" in search  # Version in parentheses

    @pytest.mark.asyncio
    async def test_nixos_info_edge_packages(self):
        """Test info retrieval for packages with unusual names."""
        # Test package with version in name
        edge_packages = [
            "python3",  # Common package
            "gcc",  # Short name
            "gnome.nautilus",  # Namespaced package
        ]

        for pkg in edge_packages:
            result = await nixos_info(pkg, type="package")
            if "not found" not in result:
                assert "Package:" in result
                assert "Version:" in result

    @pytest.mark.asyncio
    async def test_home_manager_search_complex_queries(self):
        """Test complex search patterns in Home Manager."""
        # Search for options with dots
        result = await home_manager_search("programs.git.delta", limit=10)
        if "Found" in result:
            assert "programs.git.delta" in result

        # Search for options with underscores
        result = await home_manager_search("enable_", limit=10)
        # Should handle underscore in search
        assert "Error" not in result

        # Search for very short terms
        result = await home_manager_search("qt", limit=5)
        assert "Error" not in result

    @pytest.mark.asyncio
    async def test_home_manager_category_completeness(self):
        """Test that list_options returns all major categories."""
        result = await home_manager_list_options()

        # Check for expected major categories
        expected_categories = ["programs", "services", "home", "xdg"]
        for category in expected_categories:
            assert category in result

        # Verify format consistency
        assert "total)" in result
        assert "• " in result
        assert " options)" in result

    @pytest.mark.asyncio
    async def test_home_manager_prefix_navigation(self):
        """Test navigating option hierarchy with prefixes."""
        # Start with top-level
        result = await home_manager_options_by_prefix("programs")
        if "Found" not in result and "found)" in result:
            # Drill down to specific program
            result_git = await home_manager_options_by_prefix("programs.git")
            if "found)" in result_git:
                assert "programs.git" in result_git

                # Drill down further
                result_delta = await home_manager_options_by_prefix("programs.git.delta")
                assert "Error" not in result_delta

    @pytest.mark.asyncio
    async def test_home_manager_info_name_variants(self):
        """Test info retrieval with different name formats."""
        # Test with placeholder names
        result = await home_manager_info("programs.firefox.profiles.<name>.settings")
        # Should handle <name> placeholders
        if "not found" not in result:
            assert "Option:" in result

    @pytest.mark.asyncio
    async def test_darwin_search_macos_specific(self):
        """Test searching macOS-specific options."""
        # Search for macOS-specific terms
        macos_terms = ["homebrew", "launchd", "defaults", "dock"]

        for term in macos_terms:
            result = await darwin_search(term, limit=5)
            if "Found" in result:
                assert term in result.lower()
                assert "•" in result

    @pytest.mark.asyncio
    async def test_darwin_system_defaults_exploration(self):
        """Test exploring system.defaults hierarchy."""
        # List all system.defaults options
        result = await darwin_options_by_prefix("system.defaults")

        if "found)" in result:
            # Should have many system defaults
            assert "system.defaults" in result

            # Test specific subcategories
            subcategories = ["NSGlobalDomain", "dock", "finder"]
            for subcat in subcategories:
                sub_result = await darwin_options_by_prefix(f"system.defaults.{subcat}")
                # Should not error even if no results
                assert "Error" not in sub_result

    @pytest.mark.asyncio
    async def test_darwin_info_detailed_options(self):
        """Test retrieving detailed darwin option info."""
        # Test well-known options
        known_options = ["system.defaults.dock.autohide", "environment.systemPath", "programs.zsh.enable"]

        for opt in known_options:
            result = await darwin_info(opt)
            if "not found" not in result:
                assert "Option:" in result
                # Darwin options often have descriptions
                assert "Description:" in result or "Type:" in result

    @pytest.mark.asyncio
    async def test_performance_large_searches(self):
        """Test performance with large result sets."""
        import time

        # NixOS large search
        start = time.time()
        result = await nixos_search("lib", search_type="packages", limit=100)
        elapsed = time.time() - start
        assert elapsed < 30  # Should complete within 30 seconds
        assert "Error" not in result

        # Home Manager large listing
        start = time.time()
        result = await home_manager_list_options()
        elapsed = time.time() - start
        assert elapsed < 30  # HTML parsing should be reasonably fast

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """Test handling concurrent API calls."""
        import asyncio

        queries = ["python", "ruby", "nodejs", "rust", "go"]

        # Run searches concurrently
        tasks = [nixos_search(query, limit=5) for query in queries]
        results = await asyncio.gather(*tasks)

        # All searches should complete without errors
        for result in results:
            assert "Error" not in result or "No packages found" in result

    @pytest.mark.asyncio
    async def test_unicode_handling(self):
        """Test handling of unicode in searches and results."""
        # Search with unicode
        result = await nixos_search("文字", search_type="packages", limit=5)
        # Should handle unicode gracefully
        assert "Error" not in result

        # Some packages might have unicode in descriptions
        result = await nixos_info("font-awesome")
        if "not found" not in result:
            # Should display unicode properly if present
            assert "Package:" in result

    @pytest.mark.asyncio
    async def test_empty_and_whitespace_queries(self):
        """Test handling of empty and whitespace-only queries."""
        # Empty string
        result = await nixos_search("", search_type="packages", limit=5)
        assert "No packages found" in result or "Found" in result

        # Whitespace only
        result = await home_manager_search("   ", limit=5)
        assert "Error" not in result

        # Newlines and tabs
        result = await darwin_search("\n\t", limit=5)
        assert "Error" not in result

    @pytest.mark.asyncio
    async def test_option_type_complexity(self):
        """Test handling of complex option types."""
        # Search for options with complex types
        result = await nixos_search("extraConfig", search_type="options", limit=10)

        if "Found" in result and "Type:" in result:
            # Complex types like "null or string" should be handled
            assert "Error" not in result

    @pytest.mark.asyncio
    async def test_api_timeout_resilience(self):
        """Test behavior with slow API responses."""
        # This might occasionally fail if API is very slow
        # Using programs type which might have more processing
        result = await nixos_search("compiler", search_type="programs", limit=50)

        # Should either succeed or timeout gracefully
        assert "packages found" in result or "programs found" in result or "Error" in result

    @pytest.mark.asyncio
    async def test_html_parsing_edge_cases(self):
        """Test HTML parsing with real documentation quirks."""
        # Test getting options that might have complex HTML
        complex_prefixes = ["programs.neovim.plugins", "services.nginx.virtualHosts", "systemd.services"]

        for prefix in complex_prefixes:
            result = await home_manager_options_by_prefix(prefix)
            # Should handle any HTML structure
            assert "Error" not in result or "No Home Manager options found" in result
