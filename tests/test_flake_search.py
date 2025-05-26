#!/usr/bin/env python3
"""Updated unit tests for NixOS flake search functionality."""

from unittest.mock import patch, MagicMock
from mcp_nixos.server import nixos_flakes_search


class TestFlakeSearch:
    """Test flake search functionality."""

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_with_results(self, mock_post):
        """Test successful flake search with results."""
        # Mock response with flake data
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
                        }
                    },
                    {
                        "_source": {
                            "flake_name": "nixpkgs",
                            "flake_description": "Nix Packages collection",
                            "flake_resolved": {"owner": "NixOS", "repo": "nixpkgs", "type": "github"},
                        }
                    },
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("home-manager", limit=10)

        assert "Found 2 unique flakes matching 'home-manager':" in result
        assert "• home-manager" in result
        assert "Repository: nix-community/home-manager (github)" in result
        assert "Home Manager for Nix" in result
        assert "• nixpkgs" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_no_results(self, mock_post):
        """Test flake search with no results."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_response

        result = nixos_flakes_search("nonexistent-flake")

        assert "No flakes found matching 'nonexistent-flake'." in result
        assert "Try searching for:" in result
        assert "Popular flakes:" in result
        assert "GitHub: https://github.com/topics/nix-flakes" in result

    def test_flake_search_channel_ignored(self):
        """Test that flake search ignores channel parameter."""
        # Channel parameter is ignored for flakes
        with patch("mcp_nixos.server.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"hits": {"hits": []}}
            mock_post.return_value = mock_response

            result = nixos_flakes_search("test", channel="any-channel")
            assert "No flakes found" in result
            # Should not error on channel
            assert "invalid channel" not in result.lower()

    def test_flake_search_invalid_limit(self):
        """Test flake search with invalid limit."""
        result = nixos_flakes_search("test", limit=0)
        assert "Error (ERROR): Limit must be 1-100" in result

        result = nixos_flakes_search("test", limit=101)
        assert "Error (ERROR): Limit must be 1-100" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_api_error(self, mock_post):
        """Test flake search with API error."""
        mock_post.side_effect = Exception("Connection error")

        result = nixos_flakes_search("test")
        assert "Error (ERROR): Connection error" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_404_error(self, mock_post):
        """Test flake search with 404 error (no indices)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_post.return_value = mock_response

        result = nixos_flakes_search("test")
        assert "Error (ERROR): Flake indices not found" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_partial_data(self, mock_post):
        """Test flake search with partial/missing data."""
        # Mock response with incomplete flake data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_name": "minimal-flake",
                            # Missing description and resolved info
                        }
                    },
                    {
                        "_source": {
                            "package_pname": "package-based-flake",
                            "package_description": "A flake using package fields",
                            "flake_resolved": {
                                "owner": "someone",
                                # Missing repo
                            },
                        }
                    },
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("flake", limit=10)

        assert "Found 2 unique flakes matching 'flake':" in result
        assert "• minimal-flake" in result
        assert "• package-based-flake" in result
        assert "A flake using package fields" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_query_construction(self, mock_post):
        """Test that the flake search query is properly constructed."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_response

        nixos_flakes_search("test-query", limit=5, channel="ignored")

        # Verify the query structure
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL contains flake index pattern
        assert "group-*-manual-*" in call_args[0][0]

        # Check JSON payload
        json_data = call_args[1]["json"]
        assert "query" in json_data
        assert "size" in json_data
        assert json_data["size"] == 5

        # Check query structure
        query = json_data["query"]
        assert "bool" in query
        assert "should" in query["bool"]
        assert "minimum_should_match" in query["bool"]
        assert query["bool"]["minimum_should_match"] == 1

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_with_package_attr(self, mock_post):
        """Test flake search showing package attributes."""
        # Mock response with package attribute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_name": "devenv",
                            "flake_description": (
                                "Fast, Declarative, Reproducible, and Composable Developer Environments"
                            ),
                            "flake_resolved": {
                                "owner": "cachix",
                                "repo": "devenv",
                                "type": "github",
                            },
                            "package_attr_name": "devenv-up",
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("devenv", limit=1)

        assert "• devenv" in result
        assert "Repository: cachix/devenv (github)" in result
        assert "Fast, Declarative, Reproducible" in result
        assert "Packages: devenv-up" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flake_search_long_description_truncation(self, mock_post):
        """Test that long descriptions are truncated."""
        # Mock response with long description
        long_desc = "A" * 300  # 300 characters
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "flake_name": "long-desc-flake",
                            "flake_description": long_desc,
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        result = nixos_flakes_search("long", limit=1)

        assert "• long-desc-flake" in result
        # Should be truncated to 200 chars + "..."
        assert "A" * 200 + "..." in result
        assert long_desc not in result  # Full description not shown


# Need to import requests for HTTPError
import requests
