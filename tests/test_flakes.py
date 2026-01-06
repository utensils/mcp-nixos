"""Tests for flake search and stats functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
darwin_stats = get_tool_function("darwin_stats")
home_manager_stats = get_tool_function("home_manager_stats")
nixos_flakes_search = get_tool_function("nixos_flakes_search")
nixos_flakes_stats = get_tool_function("nixos_flakes_stats")
nixos_search = get_tool_function("nixos_search")


class TestFlakeSearchScenarios:
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
    @pytest.mark.asyncio
    async def test_flake_search_basic(self, mock_post, mock_flake_response):
        """Test basic flake search functionality."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_flake_response

        result = await nixos_search("neovim", search_type="flakes")

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
    @pytest.mark.asyncio
    async def test_flake_search_deduplication(self, mock_post, mock_flake_response):
        """Test that flake deduplication works correctly."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_flake_response

        result = await nixos_search("neovim", search_type="flakes")

        # Should deduplicate neovim-nightly entries
        assert result.count("neovim-nightly") == 1
        # But should show it has multiple packages
        assert "Neovim nightly builds" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_flake_search_popular(self, mock_post, mock_popular_flakes_response):
        """Test searching for popular flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_popular_flakes_response

        result = await nixos_search("home-manager devenv agenix", search_type="flakes")

        assert "Found 5 total matches (4 unique flakes)" in result or "Found 4 unique flakes" in result
        assert "• home-manager" in result
        assert "• devenv" in result
        assert "• agenix" in result
        assert "Manage a user environment using Nix" in result
        assert "Fast, Declarative, Reproducible, and Composable Developer Environments" in result
        assert "age-encrypted secrets for NixOS" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_flake_search_no_results(self, mock_post, mock_empty_response):
        """Test flake search with no results."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_response

        result = await nixos_search("nonexistentflake123", search_type="flakes")

        assert "No flakes found" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_flake_search_wildcard(self, mock_post):
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

        result = await nixos_search("*vim*", search_type="flakes")

        assert "Found 2 unique flakes" in result
        assert "• nixvim" in result
        assert "• vim-plugins" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_flake_search_error_handling(self, mock_post):
        """Test flake search error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b"Internal Server Error"

        # Create an HTTPError with a response attribute
        http_error = requests.HTTPError("500 Server Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error

        mock_post.return_value = mock_response

        result = await nixos_search("test", search_type="flakes")

        assert "Error" in result
        # The actual error message will be the exception string
        assert "'NoneType' object has no attribute 'status_code'" not in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_flake_search_malformed_response(self, mock_post):
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

        result = await nixos_search("broken", search_type="flakes")

        # Should handle gracefully - with missing fields, no flakes will be created
        assert "Found 1 total matches (0 unique flakes)" in result


class TestStatsFormatting:
    """Test stats output formatting."""

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_home_manager_stats_with_data(self, mock_get):
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
        mock_get.return_value.content = mock_html.encode("utf-8")

        result = await home_manager_stats()

        assert "Home Manager Statistics:" in result
        assert "Total options: 3" in result
        assert "Categories:" in result
        assert "- programs: 2 options" in result
        assert "- services: 1 options" in result

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_home_manager_stats_error_handling(self, mock_get):
        """Test home_manager_stats error handling."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.content = b"Not Found"

        result = await home_manager_stats()

        assert "Error" in result

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_darwin_stats_with_data(self, mock_get):
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
        mock_get.return_value.content = mock_html.encode("utf-8")

        result = await darwin_stats()

        assert "nix-darwin Statistics:" in result
        assert "Total options: 4" in result
        assert "Categories:" in result
        assert "- system: 2 options" in result
        assert "- homebrew: 2 options" in result

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_darwin_stats_error_handling(self, mock_get):
        """Test darwin_stats error handling."""
        mock_get.return_value.status_code = 500
        mock_get.return_value.content = b"Server Error"

        result = await darwin_stats()

        assert "Error" in result

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_stats_with_complex_categories(self, mock_get):
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
        mock_get.return_value.content = mock_html.encode("utf-8")

        result = await home_manager_stats()

        assert "Total options: 4" in result
        assert "- programs: 2 options" in result
        assert "- services: 1 options" in result
        assert "- home: 1 options" in result

    @patch("requests.get")
    @pytest.mark.asyncio
    async def test_stats_with_empty_html(self, mock_get):
        """Test stats functions with empty HTML."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"<html><body></body></html>"

        result = await home_manager_stats()

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
    @pytest.mark.asyncio
    async def test_developer_workflow_flake_search(self, mock_post):
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

        result = await nixos_search("devenv", search_type="flakes")

        assert "• devenv" in result
        assert "Fast, Declarative, Reproducible, and Composable Developer Environments" in result
        assert "Developer Environments" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_system_configuration_flake_search(self, mock_post):
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

        result = await nixos_search("nixosModules", search_type="flakes")

        assert "Found 3 unique flakes" in result
        assert "• impermanence" in result
        assert "• home-manager" in result
        assert "• sops-nix" in result
        assert "ephemeral root storage" in result
        assert "secret provisioning" in result

    @patch("requests.get")
    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_combined_workflow_stats_and_search(self, mock_post, mock_get):
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
        mock_get.return_value.content = stats_html.encode("utf-8")

        stats_result = await home_manager_stats()

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

        search_result = await nixos_search("nixvim", search_type="flakes")

        assert "• nixvim" in search_result
        assert "Configure Neovim with Nix" in search_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ===== Content from test_flake_search_improved.py =====
class TestImprovedFlakeSearch:
    """Test improved flake search functionality."""

    @pytest.fixture
    def mock_empty_flake_response(self):
        """Mock response for empty query with various flake types."""
        return {
            "hits": {
                "total": {"value": 894},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "",
                            "flake_description": "Home Manager for Nix",
                            "package_pname": "home-manager",
                            "package_attr_name": "docs-json",
                            "flake_source": {"type": "github", "owner": "nix-community", "repo": "home-manager"},
                            "flake_resolved": {"type": "github", "owner": "nix-community", "repo": "home-manager"},
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "haskell.nix",
                            "flake_description": "Alternative Haskell Infrastructure for Nixpkgs",
                            "package_pname": "hix",
                            "package_attr_name": "hix",
                            "flake_source": {"type": "github", "owner": "input-output-hk", "repo": "haskell.nix"},
                            "flake_resolved": {"type": "github", "owner": "input-output-hk", "repo": "haskell.nix"},
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "nix-vscode-extensions",
                            "flake_description": (
                                "VS Code Marketplace (~40K) and Open VSX (~3K) extensions as Nix expressions."
                            ),
                            "package_pname": "updateExtensions",
                            "package_attr_name": "updateExtensions",
                            "flake_source": {
                                "type": "github",
                                "owner": "nix-community",
                                "repo": "nix-vscode-extensions",
                            },
                            "flake_resolved": {
                                "type": "github",
                                "owner": "nix-community",
                                "repo": "nix-vscode-extensions",
                            },
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "",
                            "flake_description": "A Python wrapper for the Trovo API",
                            "package_pname": "python3.11-python-trovo-0.1.7",
                            "package_attr_name": "default",
                            "flake_source": {"type": "git", "url": "https://codeberg.org/wolfangaukang/python-trovo"},
                            "flake_resolved": {"type": "git", "url": "https://codeberg.org/wolfangaukang/python-trovo"},
                        }
                    },
                ],
            }
        }

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_empty_query_returns_all_flakes(self, mock_post, mock_empty_flake_response):
        """Test that empty query returns all flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_flake_response

        result = await nixos_flakes_search("", limit=50)

        # Should use match_all query for empty search
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        # The query is wrapped in bool->filter->must structure
        assert "match_all" in str(query_data["query"])

        # Should show results
        assert "4 unique flakes" in result
        assert "home-manager" in result
        assert "haskell.nix" in result
        assert "nix-vscode-extensions" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_wildcard_query_returns_all_flakes(self, mock_post, mock_empty_flake_response):
        """Test that * query returns all flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_flake_response

        await nixos_flakes_search("*", limit=50)  # Result not used in this test

        # Should use match_all query for wildcard
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        # The query is wrapped in bool->filter->must structure
        assert "match_all" in str(query_data["query"])

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_search_by_owner(self, mock_post):
        """Test searching by owner like nix-community."""
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "package_pname": "home-manager",
                            "flake_resolved": {"type": "github", "owner": "nix-community", "repo": "home-manager"},
                        }
                    }
                ],
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        await nixos_flakes_search("nix-community", limit=20)  # Result tested via assertions

        # Should search in owner field
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        # The query structure has bool->filter and bool->must
        assert "nix-community" in str(query_data["query"])

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_deduplication_by_repo(self, mock_post):
        """Test that multiple packages from same repo are deduplicated."""
        mock_response = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "",
                            "package_pname": "hix",
                            "package_attr_name": "hix",
                            "flake_resolved": {"owner": "input-output-hk", "repo": "haskell.nix"},
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "",
                            "package_pname": "hix-build",
                            "package_attr_name": "hix-build",
                            "flake_resolved": {"owner": "input-output-hk", "repo": "haskell.nix"},
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "",
                            "package_pname": "hix-env",
                            "package_attr_name": "hix-env",
                            "flake_resolved": {"owner": "input-output-hk", "repo": "haskell.nix"},
                        }
                    },
                ],
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = await nixos_flakes_search("haskell", limit=20)

        # Should show only one flake with multiple packages
        assert "1 unique flakes" in result
        assert "input-output-hk/haskell.nix" in result
        assert "Packages: hix, hix-build, hix-env" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_handles_flakes_without_name(self, mock_post):
        """Test handling flakes with empty flake_name."""
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "",
                            "flake_description": "Home Manager for Nix",
                            "package_pname": "home-manager",
                            "flake_resolved": {"owner": "nix-community", "repo": "home-manager"},
                        }
                    }
                ],
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = await nixos_flakes_search("home-manager", limit=20)

        # Should use repo name when flake_name is empty
        assert "home-manager" in result
        assert "nix-community/home-manager" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_no_results_shows_suggestions(self, mock_post):
        """Test that no results shows helpful suggestions."""
        mock_response = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = await nixos_flakes_search("nonexistent", limit=20)

        assert "No flakes found" in result
        assert "Popular flakes: nixpkgs, home-manager, flake-utils, devenv" in result
        assert "By owner: nix-community, numtide, cachix" in result
        assert "GitHub: https://github.com/topics/nix-flakes" in result
        assert "FlakeHub: https://flakehub.com/" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_handles_git_urls(self, mock_post):
        """Test handling of non-GitHub Git URLs."""
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "",
                            "package_pname": "python-trovo",
                            "flake_resolved": {"type": "git", "url": "https://codeberg.org/wolfangaukang/python-trovo"},
                        }
                    }
                ],
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = await nixos_flakes_search("python", limit=20)

        assert "python-trovo" in result

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_search_tracks_total_hits(self, mock_post):
        """Test that search tracks total hits."""
        mock_response = {"hits": {"total": {"value": 894}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        # Make the call
        await nixos_flakes_search("", limit=20)

        # Check that track_total_hits was set
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        assert query_data.get("track_total_hits") is True

    @patch("requests.post")
    @pytest.mark.asyncio
    async def test_increased_size_multiplier(self, mock_post):
        """Test that we request more results to account for duplicates."""
        mock_response = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        await nixos_flakes_search("test", limit=20)

        # Should request more than limit to account for duplicates
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        assert query_data["size"] > 20  # Should be limit * 5 = 100


# ===== Content from test_flake_search.py =====
class TestFlakeSearch:
    """Test flake search functionality."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_empty_query(self, mock_post):
        """Test flake search with empty query returns all flakes."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 100},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Home Manager for Nix",
                            "flake_resolved": {
                                "type": "github",
                                "owner": "nix-community",
                                "repo": "home-manager",
                            },
                            "package_pname": "home-manager",
                            "package_attr_name": "default",
                        }
                    }
                ],
            }
        }
        mock_post.return_value = mock_response

        result = await nixos_flakes_search("", limit=10)

        assert "Found 100 total matches" in result
        assert "home-manager" in result
        assert "nix-community/home-manager" in result
        assert "Home Manager for Nix" in result

        # Verify the query structure
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]["query"]
        # Should have a bool query with filter and must
        assert "bool" in query_data
        assert "filter" in query_data["bool"]
        assert "must" in query_data["bool"]

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_with_query(self, mock_post):
        """Test flake search with specific query."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 5},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "devenv",
                            "flake_description": "Fast, Declarative, Reproducible Developer Environments",
                            "flake_resolved": {
                                "type": "github",
                                "owner": "cachix",
                                "repo": "devenv",
                            },
                            "package_pname": "devenv",
                            "package_attr_name": "default",
                        }
                    }
                ],
            }
        }
        mock_post.return_value = mock_response

        result = await nixos_flakes_search("devenv", limit=10)

        assert "Found 5" in result
        assert "devenv" in result
        assert "cachix/devenv" in result
        assert "Fast, Declarative" in result

        # Verify the query structure has filter and inner bool
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]["query"]
        assert "bool" in query_data
        assert "filter" in query_data["bool"]
        assert "must" in query_data["bool"]
        # The actual search query is inside must
        inner_query = query_data["bool"]["must"][0]
        assert "bool" in inner_query
        assert "should" in inner_query["bool"]

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_no_results(self, mock_post):
        """Test flake search with no results."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value = mock_response

        result = await nixos_flakes_search("nonexistent", limit=10)

        assert "No flakes found matching 'nonexistent'" in result
        assert "Try searching for:" in result
        assert "Popular flakes:" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_deduplication(self, mock_post):
        """Test flake search properly deduplicates flakes."""
        # Mock response with duplicate flakes
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 4},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_resolved": {"type": "github", "owner": "NixOS", "repo": "nixpkgs"},
                            "package_pname": "hello",
                            "package_attr_name": "hello",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_resolved": {"type": "github", "owner": "NixOS", "repo": "nixpkgs"},
                            "package_pname": "git",
                            "package_attr_name": "git",
                        }
                    },
                ],
            }
        }
        mock_post.return_value = mock_response

        result = await nixos_flakes_search("nixpkgs", limit=10)

        # Should show 1 unique flake with 2 packages
        assert "Found 4 total matches (1 unique flakes)" in result
        assert "nixpkgs" in result
        assert "NixOS/nixpkgs" in result
        assert "Packages: git, hello" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_stats(self, mock_post):
        """Test flake statistics."""
        # Mock responses
        mock_count_response = Mock()
        mock_count_response.status_code = 200
        mock_count_response.json.return_value = {"count": 452176}

        # Mock search response for sampling
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_resolved": {
                                "url": "https://github.com/nix-community/home-manager",
                                "type": "github",
                            },
                            "package_pname": "home-manager",
                        }
                    },
                    {
                        "_source": {
                            "flake_resolved": {"url": "https://github.com/NixOS/nixpkgs", "type": "github"},
                            "package_pname": "hello",
                        }
                    },
                ]
            }
        }

        mock_post.side_effect = [mock_count_response, mock_search_response]

        result = await nixos_flakes_stats()

        assert "Available flakes: 452,176" in result
        # Stats now samples documents, not using aggregations
        # So we won't see the mocked aggregation values

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_error_handling(self, mock_post):
        """Test flake search error handling."""
        # Mock 404 response with HTTPError
        from requests import HTTPError

        mock_response = Mock()
        mock_response.status_code = 404
        error = HTTPError()
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_post.return_value = mock_response

        result = await nixos_flakes_search("test", limit=10)

        assert "Error" in result
        assert "Flake indices not found" in result


class TestFlakesStatsQueries:
    """Test flakes statistics and counting queries."""

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_get_total_flakes_count(self, mock_post):
        """Test getting total flakes count."""

        # Mock flakes stats responses
        def side_effect(*args, **kwargs):
            url = args[0]
            if "/_count" in url:
                # Count request
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"count": 4500}
                return mock_response
            # Regular search request
            # Search request to get sample documents
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "hits": {
                    "total": {"value": 4500},
                    "hits": [
                        {
                            "_source": {
                                "flake_resolved": {"url": "https://github.com/NixOS/nixpkgs", "type": "github"},
                                "package_pname": "hello",
                            }
                        },
                        {
                            "_source": {
                                "flake_resolved": {
                                    "url": "https://github.com/nix-community/home-manager",
                                    "type": "github",
                                },
                                "package_pname": "home-manager",
                            }
                        },
                    ]
                    * 10,  # Simulate more hits
                }
            }
            return mock_response

        mock_post.side_effect = side_effect

        # Get flakes stats
        result = await nixos_flakes_stats()

        # Should show available flakes count (formatted with comma)
        assert "Available flakes:" in result
        assert "4,500" in result  # Matches our mock data

        # Should show unique repositories count
        assert "Unique repositories:" in result
        # The actual count depends on unique URLs in mock data

        # Should show breakdown by type
        assert "Flake types:" in result
        assert "github:" in result  # Our mock data only has github type

        # Should show top contributors
        assert "Top contributors:" in result
        assert "NixOS:" in result
        assert "nix-community:" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_search_shows_total_count(self, mock_post):
        """Test that flakes search shows total matching flakes."""
        # Mock search response with multiple hits
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 156},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_description": "Nix Packages collection",
                            "flake_resolved": {
                                "owner": "NixOS",
                                "repo": "nixpkgs",
                            },
                            "package_attr_name": "packages.x86_64-linux.hello",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_description": "Nix Packages collection",
                            "flake_resolved": {
                                "owner": "NixOS",
                                "repo": "nixpkgs",
                            },
                            "package_attr_name": "packages.x86_64-linux.git",
                        }
                    },
                ],
            }
        }
        mock_post.return_value = mock_response

        # Search for nix
        result = await nixos_flakes_search("nix", limit=2)

        # Should show both total matches and unique flakes count
        assert "total matches" in result
        assert "unique flakes" in result
        assert "nixpkgs" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_wildcard_search_shows_all(self, mock_post):
        """Test that wildcard search returns all flakes."""
        # Mock response with many flakes
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 4500},
                "hits": [
                    {
                        "_source": {
                            "flake_name": "devenv",
                            "flake_description": "Development environments",
                            "flake_resolved": {"owner": "cachix", "repo": "devenv"},
                            "package_attr_name": "packages.x86_64-linux.devenv",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "home-manager",
                            "flake_description": "Manage user configuration",
                            "flake_resolved": {"owner": "nix-community", "repo": "home-manager"},
                            "package_attr_name": "packages.x86_64-linux.home-manager",
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "",
                            "flake_description": "Flake utilities",
                            "flake_resolved": {"owner": "numtide", "repo": "flake-utils"},
                            "package_attr_name": "lib.eachDefaultSystem",
                        }
                    },
                ],
            }
        }
        mock_post.return_value = mock_response

        # Wildcard search
        result = await nixos_flakes_search("*", limit=10)

        # Should show total count
        assert "total matches" in result

        # Should list some flakes
        assert "devenv" in result
        assert "home-manager" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_stats_with_no_flakes(self, mock_post):
        """Test flakes stats when no flakes are indexed."""

        # Mock empty response
        def side_effect(*args, **kwargs):
            url = args[0]
            mock_response = Mock()
            mock_response.status_code = 200

            if "/_count" in url:
                # Count request
                mock_response.json.return_value = {"count": 0}
            else:
                # Search with aggregations
                mock_response.json.return_value = {
                    "hits": {"total": {"value": 0}},
                    "aggregations": {
                        "unique_flakes": {"value": 0},
                        "flake_types": {"buckets": []},
                        "top_owners": {"buckets": []},
                    },
                }
            return mock_response

        mock_post.side_effect = side_effect

        result = await nixos_flakes_stats()

        # Should handle empty case gracefully
        assert "Available flakes: 0" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_flakes_stats_error_handling(self, mock_post):
        """Test that flakes stats handles API errors gracefully."""
        # Mock 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_post.return_value = mock_response

        result = await nixos_flakes_stats()

        # Should return error message
        assert "Error" in result
        assert "Flake indices not found" in result or "Not found" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.requests.post")
    async def test_compare_flakes_vs_packages(self, mock_post):
        """Test comparing flakes and packages statistics."""
        # First call: flakes stats
        mock_flakes_response = Mock()
        mock_flakes_response.status_code = 200
        mock_flakes_response.json.return_value = {
            "hits": {"total": {"value": 4500}},
            "aggregations": {
                "unique_flakes": {"value": 894},
                "flake_types": {
                    "buckets": [
                        {"key": "github", "doc_count": 3800},
                    ]
                },
                "top_contributors": {
                    "buckets": [
                        {"key": "NixOS", "doc_count": 450},
                    ]
                },
            },
        }

        # Second call: regular packages stats (for comparison)
        mock_packages_response = Mock()
        mock_packages_response.json.return_value = {
            "aggregations": {
                "attr_count": {"value": 151798},
                "option_count": {"value": 20156},
                "program_count": {"value": 3421},
                "license_count": {"value": 125},
                "maintainer_count": {"value": 3254},
                "platform_counts": {"buckets": []},
            }
        }

        def side_effect(*args, **kwargs):
            url = args[0]
            if "latest-44-group-manual" in url:
                if "/_count" in url:
                    # Count request
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"count": 4500}
                    return mock_response
                # Search request - return sample hits
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "hits": {
                        "hits": [
                            {
                                "_source": {
                                    "flake_resolved": {"url": "https://github.com/NixOS/nixpkgs", "type": "github"}
                                }
                            }
                        ]
                        * 5
                    }
                }
                return mock_response
            return mock_packages_response

        mock_post.side_effect = side_effect

        # Get flakes stats
        flakes_result = await nixos_flakes_stats()
        assert "Available flakes:" in flakes_result
        assert "4,500" in flakes_result  # From our mock

        # Should also show unique repositories
        assert "Unique repositories:" in flakes_result
