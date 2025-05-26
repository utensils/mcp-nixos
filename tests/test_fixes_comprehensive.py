#!/usr/bin/env python3
"""Comprehensive tests for the fixes to issues found in Claude Desktop testing."""

import pytest
from unittest.mock import patch, MagicMock
from mcp_nixos.server import nixos_flakes_search, home_manager_stats, darwin_stats


class TestFlakeSearchDeduplication:
    """Test that flake search properly deduplicates results."""

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_deduplicates_packages(self, mock_post):
        """Test that multiple packages from same flake are grouped."""
        # Mock response with duplicate flakes (different packages)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "owner": "nix-community",
                                "repo": "home-manager",
                                "type": "github",
                            },
                            "package_attr_name": "default",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "owner": "nix-community",
                                "repo": "home-manager",
                                "type": "github",
                            },
                            "package_attr_name": "docs-json",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "owner": "nix-community",
                                "repo": "home-manager",
                                "type": "github",
                            },
                            "package_attr_name": "docs-html",
                        }
                    },
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("home-manager", limit=10)

        # Should only show 1 unique flake
        assert "Found 1 unique flakes matching 'home-manager':" in result
        assert result.count("• home-manager") == 1
        # Should show all packages together
        assert "Packages: default, docs-html, docs-json" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_handles_many_packages(self, mock_post):
        """Test that flakes with many packages are handled properly."""
        # Create a flake with 10 packages
        hits = []
        for i in range(10):
            hits.append(
                {
                    "_source": {
                        "flake_name": "multi-package-flake",
                        "flake_description": "A flake with many packages",
                        "flake_resolved": {
                            "owner": "test",
                            "repo": "multi-flake",
                            "type": "github",
                        },
                        "package_attr_name": f"package{i}",
                    }
                }
            )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": hits}}
        mock_post.return_value = mock_response

        result = nixos_flakes_search("multi-package", limit=20)

        # Should show only first 5 packages with total count
        assert "Found 1 unique flakes matching 'multi-package':" in result
        assert "Packages: package0, package1, package2, package3, package4, ... (10 total)" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_handles_mixed_flakes(self, mock_post):
        """Test deduplication with multiple different flakes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    # home-manager with 2 packages
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "owner": "nix-community",
                                "repo": "home-manager",
                                "type": "github",
                            },
                            "package_attr_name": "default",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "owner": "nix-community",
                                "repo": "home-manager",
                                "type": "github",
                            },
                            "package_attr_name": "docs-json",
                        }
                    },
                    # nixpkgs with 1 package
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_description": "Nix Packages collection",
                            "flake_resolved": {
                                "owner": "NixOS",
                                "repo": "nixpkgs",
                                "type": "github",
                            },
                            "package_attr_name": "hello",
                        }
                    },
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("test", limit=10)

        # Should show 2 unique flakes
        assert "Found 2 unique flakes matching 'test':" in result
        assert result.count("• home-manager") == 1
        assert result.count("• nixpkgs") == 1
        # home-manager should show 2 packages
        assert "default, docs-json" in result
        # nixpkgs should show 1 package
        assert "hello" in result


class TestHomeManagerStats:
    """Test improved home_manager_stats functionality."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_stats_returns_statistics(self, mock_parse):
        """Test that home_manager_stats returns actual statistics."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.vim.enable", "type": "boolean", "description": "Enable vim"},
            {"name": "services.dunst.enable", "type": "boolean", "description": "Enable dunst"},
            {"name": "home.username", "type": "string", "description": "Username"},
            {"name": "home.packages", "type": "list of packages", "description": "Packages"},
            {"name": "wayland.enable", "type": "null or boolean", "description": "Enable wayland"},
        ]

        result = home_manager_stats()

        # Should return statistics, not redirect message
        assert "Home Manager Statistics:" in result
        assert "Total options: 6" in result
        assert "Categories: 4" in result
        assert "programs: 2 options" in result
        assert "services: 1 options" in result
        assert "home: 2 options" in result
        assert "wayland: 1 options" in result

        # Should not contain the old redirect message
        assert "require parsing the full documentation" not in result
        assert "Use home_manager_list_options" not in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_stats_handles_errors(self, mock_parse):
        """Test that home_manager_stats handles errors gracefully."""
        mock_parse.side_effect = Exception("Network error")

        result = home_manager_stats()

        assert "Error (ERROR): Network error" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_stats_handles_no_options(self, mock_parse):
        """Test that home_manager_stats handles empty results."""
        mock_parse.return_value = []

        result = home_manager_stats()

        assert "Error (ERROR): Failed to fetch Home Manager statistics" in result


class TestDarwinStats:
    """Test improved darwin_stats functionality."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_stats_returns_statistics(self, mock_parse):
        """Test that darwin_stats returns actual statistics."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            {
                "name": "system.defaults.NSGlobalDomain.AppleShowAllFiles",
                "type": "boolean",
                "description": "Show all files",
            },
            {"name": "services.nix-daemon.enable", "type": "boolean", "description": "Enable nix-daemon"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "homebrew.enable", "type": "boolean", "description": "Enable homebrew"},
            {"name": "launchd.agents.test", "type": "attribute set", "description": "Test agent"},
        ]

        result = darwin_stats()

        # Should return statistics, not redirect message
        assert "nix-darwin Statistics:" in result
        assert "Total options: 6" in result
        assert "Categories: 5" in result
        assert "services: 1 options" in result
        assert "system: 2 options" in result
        assert "programs: 1 options" in result
        assert "homebrew: 1 options" in result
        assert "launchd: 1 options" in result

        # Should not contain the old redirect message
        assert "require parsing the full documentation" not in result
        assert "Use darwin_list_options" not in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_stats_handles_errors(self, mock_parse):
        """Test that darwin_stats handles errors gracefully."""
        mock_parse.side_effect = Exception("Connection timeout")

        result = darwin_stats()

        assert "Error (ERROR): Connection timeout" in result

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_stats_handles_no_options(self, mock_parse):
        """Test that darwin_stats handles empty results."""
        mock_parse.return_value = []

        result = darwin_stats()

        assert "Error (ERROR): Failed to fetch nix-darwin statistics" in result


class TestIntegration:
    """Integration tests for all fixes."""

    @pytest.mark.integration
    def test_flake_search_real_deduplication(self):
        """Test flake deduplication against real API."""
        result = nixos_flakes_search("home-manager", limit=20)

        # Count how many times "• home-manager" appears
        # Should be 1 after deduplication
        home_manager_count = result.count("• home-manager")
        assert home_manager_count <= 1, f"home-manager appears {home_manager_count} times, should be deduplicated"

        # If found, should show packages
        if "• home-manager" in result:
            assert "Repository: nix-community/home-manager" in result
            assert "Packages:" in result or "Package:" in result

    @pytest.mark.integration
    @pytest.mark.slow
    def test_home_manager_stats_real_data(self):
        """Test home_manager_stats with real data."""
        result = home_manager_stats()

        # Should return real statistics
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "programs:" in result
        assert "services:" in result

        # Should have reasonable numbers
        assert "Total options: 0" not in result  # Should have some options
        assert "Categories: 0" not in result  # Should have some categories

    @pytest.mark.integration
    @pytest.mark.slow
    def test_darwin_stats_real_data(self):
        """Test darwin_stats with real data."""
        result = darwin_stats()

        # Should return real statistics
        assert "nix-darwin Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "services:" in result
        assert "system:" in result

        # Should have reasonable numbers
        assert "Total options: 0" not in result  # Should have some options
        assert "Categories: 0" not in result  # Should have some categories


# Quick smoke test
if __name__ == "__main__":
    print("Running comprehensive tests for fixes...")

    # Test flake deduplication
    test = TestFlakeSearchDeduplication()
    with patch("requests.post") as mock_post:
        # Set up mock response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"flake_resolved": {"url": "github:user/repo1"}, "package_pname": "pkg1"}},
                    {"_source": {"flake_resolved": {"url": "github:user/repo1"}, "package_pname": "pkg2"}},
                    {"_source": {"flake_resolved": {"url": "github:user/repo2"}, "package_pname": "pkg3"}},
                ]
            }
        }
        test.test_flake_search_deduplicates_packages(mock_post)
    print("✓ Flake deduplication test passed")

    # Test stats improvements
    test_hm = TestHomeManagerStats()
    with patch("mcp_nixos.server.parse_html_options") as mock_parse:
        # Set up mock response
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean"},
            {"name": "programs.neovim.enable", "type": "boolean"},
            {"name": "services.gpg-agent.enable", "type": "boolean"},
        ]
        test_hm.test_home_manager_stats_returns_statistics(mock_parse)
    print("✓ Home Manager stats test passed")

    test_darwin = TestDarwinStats()
    with patch("mcp_nixos.server.parse_html_options") as mock_parse:
        # Set up mock response
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean"},
            {"name": "services.nix-daemon.enable", "type": "boolean"},
        ]
        test_darwin.test_darwin_stats_returns_statistics(mock_parse)
    print("✓ Darwin stats test passed")

    print("\nAll tests passed!")
