"""Test flake search functionality."""

from unittest.mock import patch, Mock
from mcp_nixos.server import nixos_flakes_search, nixos_flakes_stats


class TestFlakeSearch:
    """Test flake search functionality."""

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_empty_query(self, mock_post):
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

        result = nixos_flakes_search("", limit=10)

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

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_with_query(self, mock_post):
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

        result = nixos_flakes_search("devenv", limit=10)

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

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_no_results(self, mock_post):
        """Test flake search with no results."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_post.return_value = mock_response

        result = nixos_flakes_search("nonexistent", limit=10)

        assert "No flakes found matching 'nonexistent'" in result
        assert "Try searching for:" in result
        assert "Popular flakes:" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_deduplication(self, mock_post):
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

        result = nixos_flakes_search("nixpkgs", limit=10)

        # Should show 1 unique flake with 2 packages
        assert "Found 4 total matches (1 unique flakes)" in result
        assert "nixpkgs" in result
        assert "NixOS/nixpkgs" in result
        assert "Packages: git, hello" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_stats(self, mock_post):
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

        result = nixos_flakes_stats()

        assert "Available flakes: 452,176" in result
        # Stats now samples documents, not using aggregations
        # So we won't see the mocked aggregation values

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_error_handling(self, mock_post):
        """Test flake search error handling."""
        # Mock 404 response with HTTPError
        from requests import HTTPError

        mock_response = Mock()
        mock_response.status_code = 404
        error = HTTPError()
        error.response = mock_response
        mock_response.raise_for_status.side_effect = error
        mock_post.return_value = mock_response

        result = nixos_flakes_search("test", limit=10)

        assert "Error" in result
        assert "Flake indices not found" in result
