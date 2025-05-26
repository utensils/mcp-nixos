"""Tests for improved flake search functionality based on manual testing."""

import pytest
from unittest.mock import patch

from mcp_nixos.server import nixos_flakes_search


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
    def test_empty_query_returns_all_flakes(self, mock_post, mock_empty_flake_response):
        """Test that empty query returns all flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_flake_response

        result = nixos_flakes_search("", limit=50)

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
    def test_wildcard_query_returns_all_flakes(self, mock_post, mock_empty_flake_response):
        """Test that * query returns all flakes."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_empty_flake_response

        nixos_flakes_search("*", limit=50)  # Result not used in this test

        # Should use match_all query for wildcard
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        # The query is wrapped in bool->filter->must structure
        assert "match_all" in str(query_data["query"])

    @patch("requests.post")
    def test_search_by_owner(self, mock_post):
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

        nixos_flakes_search("nix-community", limit=20)  # Result tested via assertions

        # Should search in owner field
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        # The query structure has bool->filter and bool->must
        assert "nix-community" in str(query_data["query"])

    @patch("requests.post")
    def test_deduplication_by_repo(self, mock_post):
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

        result = nixos_flakes_search("haskell", limit=20)

        # Should show only one flake with multiple packages
        assert "1 unique flakes" in result
        assert "input-output-hk/haskell.nix" in result
        assert "Packages: hix, hix-build, hix-env" in result

    @patch("requests.post")
    def test_handles_flakes_without_name(self, mock_post):
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

        result = nixos_flakes_search("home-manager", limit=20)

        # Should use repo name when flake_name is empty
        assert "home-manager" in result
        assert "nix-community/home-manager" in result

    @patch("requests.post")
    def test_no_results_shows_suggestions(self, mock_post):
        """Test that no results shows helpful suggestions."""
        mock_response = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = nixos_flakes_search("nonexistent", limit=20)

        assert "No flakes found" in result
        assert "Popular flakes: nixpkgs, home-manager, flake-utils, devenv" in result
        assert "By owner: nix-community, numtide, cachix" in result
        assert "GitHub: https://github.com/topics/nix-flakes" in result
        assert "FlakeHub: https://flakehub.com/" in result

    @patch("requests.post")
    def test_handles_git_urls(self, mock_post):
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

        result = nixos_flakes_search("python", limit=20)

        assert "python-trovo" in result

    @patch("requests.post")
    def test_search_tracks_total_hits(self, mock_post):
        """Test that search tracks total hits."""
        mock_response = {"hits": {"total": {"value": 894}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        # Make the call
        nixos_flakes_search("", limit=20)

        # Check that track_total_hits was set
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        assert query_data.get("track_total_hits") is True

    @patch("requests.post")
    def test_increased_size_multiplier(self, mock_post):
        """Test that we request more results to account for duplicates."""
        mock_response = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        nixos_flakes_search("test", limit=20)

        # Should request more than limit to account for duplicates
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]
        assert query_data["size"] > 20  # Should be limit * 5 = 100
