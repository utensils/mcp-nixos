"""Test eval for flakes statistics functionality."""

from unittest.mock import patch, Mock
from mcp_nixos.server import nixos_flakes_stats, nixos_flakes_search


class TestFlakesStatsEval:
    """Test evaluations for flakes statistics and counting."""

    @patch("mcp_nixos.server.requests.post")
    def test_get_total_flakes_count(self, mock_post):
        """Eval: User asks 'how many flakes are there?'"""

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
        result = nixos_flakes_stats()

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

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_search_shows_total_count(self, mock_post):
        """Eval: Flakes search should show total matching flakes."""
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
        result = nixos_flakes_search("nix", limit=2)

        # Should show both total matches and unique flakes count
        assert "total matches" in result
        assert "unique flakes" in result
        assert "nixpkgs" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_wildcard_search_shows_all(self, mock_post):
        """Eval: User searches with '*' to see all flakes."""
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
        result = nixos_flakes_search("*", limit=10)

        # Should show total count
        assert "total matches" in result

        # Should list some flakes
        assert "devenv" in result
        assert "home-manager" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_stats_with_no_flakes(self, mock_post):
        """Eval: Flakes stats when no flakes are indexed."""

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

        result = nixos_flakes_stats()

        # Should handle empty case gracefully
        assert "Available flakes: 0" in result

    @patch("mcp_nixos.server.requests.post")
    def test_flakes_stats_error_handling(self, mock_post):
        """Eval: Flakes stats handles API errors gracefully."""
        # Mock 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_post.return_value = mock_response

        result = nixos_flakes_stats()

        # Should return error message
        assert "Error" in result
        assert "Flake indices not found" in result or "Not found" in result

    @patch("mcp_nixos.server.requests.post")
    def test_compare_flakes_vs_packages(self, mock_post):
        """Eval: User wants to understand flakes vs packages relationship."""
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
            if "latest-43-group-manual" in url:
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
        flakes_result = nixos_flakes_stats()
        assert "Available flakes:" in flakes_result
        assert "4,500" in flakes_result  # From our mock

        # Should also show unique repositories
        assert "Unique repositories:" in flakes_result
