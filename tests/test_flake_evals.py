"""Evaluation tests for flake search and improved stats functionality."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from mcp_nixos.server import nixos_search, home_manager_stats, darwin_stats


class TestFlakeSearchEvals:
    """Test flake search functionality with real-world scenarios."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    @pytest.fixture
    def mock_flake_response(self):
        """Mock response for flake search results."""
        return {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "neovim",
                            "flake_name": "nixpkgs",
                            "flake_url": "github:NixOS/nixpkgs",
                            "flake_description": "Vim-fork focused on extensibility and usability",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux", "x86_64-darwin", "aarch64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "packages.x86_64-linux.neovim",
                            "flake_name": "neovim-nightly",
                            "flake_url": "github:nix-community/neovim-nightly-overlay",
                            "flake_description": "Neovim nightly builds",
                            "flake_platforms": ["x86_64-linux"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "packages.aarch64-darwin.neovim",
                            "flake_name": "neovim-nightly",
                            "flake_url": "github:nix-community/neovim-nightly-overlay",
                            "flake_description": "Neovim nightly builds",
                            "flake_platforms": ["aarch64-darwin"],
                        }
                    },
                ],
            }
        }

    @pytest.fixture
    def mock_popular_flakes_response(self):
        """Mock response for popular flakes."""
        return {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "homeConfigurations.example",
                            "flake_name": "home-manager",
                            "flake_url": "github:nix-community/home-manager",
                            "flake_description": "Manage a user environment using Nix",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux", "x86_64-darwin", "aarch64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "nixosConfigurations.example",
                            "flake_name": "nixos-hardware",
                            "flake_url": "github:NixOS/nixos-hardware",
                            "flake_description": "NixOS modules to support various hardware",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "devShells.x86_64-linux.default",
                            "flake_name": "devenv",
                            "flake_url": "github:cachix/devenv",
                            "flake_description": (
                                "Fast, Declarative, Reproducible, and Composable Developer Environments"
                            ),
                            "flake_platforms": ["x86_64-linux", "x86_64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "packages.x86_64-linux.agenix",
                            "flake_name": "agenix",
                            "flake_url": "github:ryantm/agenix",
                            "flake_description": "age-encrypted secrets for NixOS",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux", "x86_64-darwin", "aarch64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "packages.x86_64-darwin.agenix",
                            "flake_name": "agenix",
                            "flake_url": "github:ryantm/agenix",
                            "flake_description": "age-encrypted secrets for NixOS",
                            "flake_platforms": ["x86_64-darwin", "aarch64-darwin"],
                        }
                    },
                ],
            }
        }

    @pytest.fixture
    def mock_empty_response(self):
        """Mock empty response."""
        return {"hits": {"total": {"value": 0}, "hits": []}}

    @patch("requests.post")
    def test_flake_search_basic(self, mock_post, mock_flake_response):
        """Test basic flake search functionality."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_flake_response

        result = nixos_search("neovim", search_type="flakes")

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "_search" in call_args[0][0]

        # Check query structure - now using json parameter instead of data
        query_data = call_args[1]["json"]
        # The query now uses bool->filter->term for type filtering
        assert "query" in query_data
        assert "size" in query_data

        # Verify output format
        assert "unique flakes" in result
        assert "• nixpkgs" in result or "• neovim" in result
        assert "• neovim-nightly" in result

    @patch("requests.post")
    def test_flake_search_deduplication(self, mock_post, mock_flake_response):
        """Test that flake deduplication works correctly."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_flake_response

        result = nixos_search("neovim", search_type="flakes")

        # Should deduplicate neovim-nightly entries
        assert result.count("neovim-nightly") == 1
        # But should show it has multiple packages
        assert "Neovim nightly builds" in result

    @patch("requests.post")
    def test_flake_search_popular(self, mock_post, mock_popular_flakes_response):
        """Test searching for popular flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_popular_flakes_response

        result = nixos_search("home-manager devenv agenix", search_type="flakes")

        assert "Found 5 total matches (4 unique flakes)" in result or "Found 4 unique flakes" in result
        assert "• home-manager" in result
        assert "• devenv" in result
        assert "• agenix" in result
        assert "Manage a user environment using Nix" in result
        assert "Fast, Declarative, Reproducible, and Composable Developer Environments" in result
        assert "age-encrypted secrets for NixOS" in result

    @patch("requests.post")
    def test_flake_search_no_results(self, mock_post, mock_empty_response):
        """Test flake search with no results."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_response

        result = nixos_search("nonexistentflake123", search_type="flakes")

        assert "No flakes found" in result

    @patch("requests.post")
    def test_flake_search_wildcard(self, mock_post):
        """Test flake search with wildcard patterns."""
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "nixvim",
                            "flake_name": "nixvim",
                            "flake_url": "github:nix-community/nixvim",
                            "flake_description": "Configure Neovim with Nix",
                            "flake_platforms": ["x86_64-linux", "x86_64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "vim-startify",
                            "flake_name": "vim-plugins",
                            "flake_url": "github:m15a/nixpkgs-vim-extra-plugins",
                            "flake_description": "Extra Vim plugins for Nix",
                            "flake_platforms": ["x86_64-linux"],
                        }
                    },
                ],
            }
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = nixos_search("*vim*", search_type="flakes")

        assert "Found 2 unique flakes" in result
        assert "• nixvim" in result
        assert "• vim-plugins" in result

    @patch("requests.post")
    def test_flake_search_error_handling(self, mock_post):
        """Test flake search error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        # Create an HTTPError with a response attribute
        http_error = requests.HTTPError("500 Server Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        mock_post.return_value = mock_response

        result = nixos_search("test", search_type="flakes")

        assert "Error" in result
        # The actual error message will be the exception string
        assert "'NoneType' object has no attribute 'status_code'" not in result

    @patch("requests.post")
    def test_flake_search_malformed_response(self, mock_post):
        """Test handling of malformed flake responses."""
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "broken",
                            # Missing required fields
                        }
                    }
                ],
            }
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = nixos_search("broken", search_type="flakes")

        # Should handle gracefully - with missing fields, no flakes will be created
        assert "Found 1 total matches (0 unique flakes)" in result


class TestImprovedStatsEvals:
    """Test improved stats functionality."""

    @patch("requests.get")
    def test_home_manager_stats_with_data(self, mock_get):
        """Test home_manager_stats returns actual statistics."""
        mock_html = """
        <html>
        <body>
            <dl class="variablelist">
                <dt id="opt-programs.git.enable">programs.git.enable</dt>
                <dd>Enable git</dd>
                <dt id="opt-programs.vim.enable">programs.vim.enable</dt>
                <dd>Enable vim</dd>
                <dt id="opt-services.gpg-agent.enable">services.gpg-agent.enable</dt>
                <dd>Enable gpg-agent</dd>
            </dl>
        </body>
        </html>
        """

        mock_get.return_value.status_code = 200
        mock_get.return_value.text = mock_html

        result = home_manager_stats()

        assert "Home Manager Statistics:" in result
        assert "Total options: 3" in result
        assert "Categories:" in result
        assert "- programs: 2 options" in result
        assert "- services: 1 options" in result

    @patch("requests.get")
    def test_home_manager_stats_error_handling(self, mock_get):
        """Test home_manager_stats error handling."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.text = "Not Found"

        result = home_manager_stats()

        assert "Error" in result

    @patch("requests.get")
    def test_darwin_stats_with_data(self, mock_get):
        """Test darwin_stats returns actual statistics."""
        mock_html = """
        <html>
        <body>
            <div id="toc">
                <dl>
                    <dt><a href="#opt-system.defaults.dock.autohide">system.defaults.dock.autohide</a></dt>
                    <dd>Auto-hide the dock</dd>
                    <dt><a href="#opt-system.defaults.finder.ShowPathbar">system.defaults.finder.ShowPathbar</a></dt>
                    <dd>Show path bar in Finder</dd>
                    <dt><a href="#opt-homebrew.enable">homebrew.enable</a></dt>
                    <dd>Enable Homebrew</dd>
                    <dt><a href="#opt-homebrew.casks">homebrew.casks</a></dt>
                    <dd>List of Homebrew casks to install</dd>
                </dl>
            </div>
        </body>
        </html>
        """

        mock_get.return_value.status_code = 200
        mock_get.return_value.text = mock_html

        result = darwin_stats()

        assert "nix-darwin Statistics:" in result
        assert "Total options: 4" in result
        assert "Categories:" in result
        assert "- system: 2 options" in result
        assert "- homebrew: 2 options" in result

    @patch("requests.get")
    def test_darwin_stats_error_handling(self, mock_get):
        """Test darwin_stats error handling."""
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Server Error"

        result = darwin_stats()

        assert "Error" in result

    @patch("requests.get")
    def test_stats_with_complex_categories(self, mock_get):
        """Test stats functions with complex nested categories."""
        mock_html = """
        <html>
        <body>
            <dl class="variablelist">
                <dt id="opt-programs.git.enable">programs.git.enable</dt>
                <dd>Enable git</dd>
                <dt id="opt-programs.git.signing.key">programs.git.signing.key</dt>
                <dd>GPG signing key</dd>
                <dt id="opt-services.xserver.displayManager.gdm.enable">services.xserver.displayManager.gdm.enable</dt>
                <dd>Enable GDM</dd>
                <dt id="opt-home.packages">home.packages</dt>
                <dd>List of packages</dd>
            </dl>
        </body>
        </html>
        """

        mock_get.return_value.status_code = 200
        mock_get.return_value.text = mock_html

        result = home_manager_stats()

        assert "Total options: 4" in result
        assert "- programs: 2 options" in result
        assert "- services: 1 options" in result
        assert "- home: 1 options" in result

    @patch("requests.get")
    def test_stats_with_empty_html(self, mock_get):
        """Test stats functions with empty HTML."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html><body></body></html>"

        result = home_manager_stats()

        # When no options are found, the function returns an error
        assert "Error" in result
        assert "Failed to fetch Home Manager statistics" in result


class TestRealWorldScenarios:
    """Test real-world usage scenarios for flake search and stats."""

    @pytest.fixture(autouse=True)
    def mock_channel_validation(self):
        """Mock channel validation to always pass for 'unstable'."""
        with patch("mcp_nixos.server.channel_cache") as mock_cache:
            mock_cache.get_available.return_value = {"unstable": "latest-45-nixos-unstable"}
            mock_cache.get_resolved.return_value = {"unstable": "latest-45-nixos-unstable"}
            with patch("mcp_nixos.server.validate_channel") as mock_validate:
                mock_validate.return_value = True
                yield mock_cache

    @patch("requests.post")
    def test_developer_workflow_flake_search(self, mock_post):
        """Test a developer searching for development environment flakes."""
        # First search for devenv
        devenv_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "devShells.x86_64-linux.default",
                            "flake_name": "devenv",
                            "flake_url": "github:cachix/devenv",
                            "flake_description": (
                                "Fast, Declarative, Reproducible, and Composable Developer Environments"
                            ),
                            "flake_platforms": ["x86_64-linux", "x86_64-darwin"],
                        }
                    }
                ],
            }
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = devenv_response

        result = nixos_search("devenv", search_type="flakes")

        assert "• devenv" in result
        assert "Fast, Declarative, Reproducible, and Composable Developer Environments" in result
        assert "Developer Environments" in result

    @patch("requests.post")
    def test_system_configuration_flake_search(self, mock_post):
        """Test searching for system configuration flakes."""
        config_response = {
            "hits": {
                "total": {"value": 3},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "nixosModules.default",
                            "flake_name": "impermanence",
                            "flake_url": "github:nix-community/impermanence",
                            "flake_description": (
                                "Modules to help you handle persistent state on systems with ephemeral root storage"
                            ),
                            "flake_platforms": ["x86_64-linux", "aarch64-linux"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "nixosModules.home-manager",
                            "flake_name": "home-manager",
                            "flake_url": "github:nix-community/home-manager",
                            "flake_description": "Manage a user environment using Nix",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux", "x86_64-darwin", "aarch64-darwin"],
                        }
                    },
                    {
                        "_source": {
                            "flake_attr_name": "nixosModules.sops",
                            "flake_name": "sops-nix",
                            "flake_url": "github:Mic92/sops-nix",
                            "flake_description": "Atomic secret provisioning for NixOS based on sops",
                            "flake_platforms": ["x86_64-linux", "aarch64-linux"],
                        }
                    },
                ],
            }
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = config_response

        result = nixos_search("nixosModules", search_type="flakes")

        assert "Found 3 unique flakes" in result
        assert "• impermanence" in result
        assert "• home-manager" in result
        assert "• sops-nix" in result
        assert "ephemeral root storage" in result
        assert "secret provisioning" in result

    @patch("requests.get")
    @patch("requests.post")
    def test_combined_workflow_stats_and_search(self, mock_post, mock_get):
        """Test a workflow combining stats check and targeted search."""
        # First, check Home Manager stats
        stats_html = """
        <html>
        <body>
            <dl class="variablelist">
                <dt id="opt-programs.neovim.enable">programs.neovim.enable</dt>
                <dd>Enable neovim</dd>
                <dt id="opt-programs.neovim.plugins">programs.neovim.plugins</dt>
                <dd>List of vim plugins</dd>
                <dt id="opt-programs.vim.enable">programs.vim.enable</dt>
                <dd>Enable vim</dd>
            </dl>
        </body>
        </html>
        """

        mock_get.return_value.status_code = 200
        mock_get.return_value.text = stats_html

        stats_result = home_manager_stats()

        assert "Total options: 3" in stats_result
        assert "- programs: 3 options" in stats_result

        # Then search for related flakes
        flake_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "flake_attr_name": "homeManagerModules.nixvim",
                            "flake_name": "nixvim",
                            "flake_url": "github:nix-community/nixvim",
                            "flake_description": "Configure Neovim with Nix",
                            "flake_platforms": ["x86_64-linux", "x86_64-darwin"],
                        }
                    }
                ],
            }
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = flake_response

        search_result = nixos_search("nixvim", search_type="flakes")

        assert "• nixvim" in search_result
        assert "Configure Neovim with Nix" in search_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
