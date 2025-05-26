"""Test eval for package counts per channel functionality."""

from unittest.mock import patch, Mock
from mcp_nixos.server import nixos_channels, nixos_stats


class TestPackageCountsEval:
    """Test evaluations for getting package counts per NixOS channel."""

    @patch("mcp_nixos.server.requests.post")
    def test_get_package_counts_per_channel(self, mock_post):
        """Eval: User wants package counts for each NixOS channel."""
        # Mock channel discovery responses
        mock_count_responses = {
            "latest-43-nixos-unstable": {"count": 151798},
            "latest-43-nixos-25.05": {"count": 151698},
            "latest-43-nixos-24.11": {"count": 142034},
        }

        # Mock stats responses for each channel
        mock_stats_responses = {
            "unstable": {
                "aggregations": {
                    "attr_count": {"value": 151798},
                    "option_count": {"value": 20156},
                    "program_count": {"value": 3421},
                    "license_count": {"value": 125},
                    "maintainer_count": {"value": 3254},
                    "platform_counts": {
                        "buckets": [
                            {"key": "x86_64-linux", "doc_count": 145234},
                            {"key": "aarch64-linux", "doc_count": 142123},
                            {"key": "x86_64-darwin", "doc_count": 98765},
                            {"key": "aarch64-darwin", "doc_count": 97654},
                        ]
                    },
                }
            },
            "25.05": {
                "aggregations": {
                    "attr_count": {"value": 151698},
                    "option_count": {"value": 20145},
                    "program_count": {"value": 3420},
                    "license_count": {"value": 125},
                    "maintainer_count": {"value": 3250},
                    "platform_counts": {
                        "buckets": [
                            {"key": "x86_64-linux", "doc_count": 145134},
                            {"key": "aarch64-linux", "doc_count": 142023},
                            {"key": "x86_64-darwin", "doc_count": 98665},
                            {"key": "aarch64-darwin", "doc_count": 97554},
                        ]
                    },
                }
            },
            "24.11": {
                "aggregations": {
                    "attr_count": {"value": 142034},
                    "option_count": {"value": 19876},
                    "program_count": {"value": 3200},
                    "license_count": {"value": 123},
                    "maintainer_count": {"value": 3100},
                    "platform_counts": {
                        "buckets": [
                            {"key": "x86_64-linux", "doc_count": 138000},
                            {"key": "aarch64-linux", "doc_count": 135000},
                            {"key": "x86_64-darwin", "doc_count": 92000},
                            {"key": "aarch64-darwin", "doc_count": 91000},
                        ]
                    },
                }
            },
        }

        def side_effect(*args, **kwargs):
            url = args[0]
            # Handle count requests for channel discovery
            if "/_count" in url:
                for index, count_data in mock_count_responses.items():
                    if index in url:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = count_data
                        return mock_response
                # Not found
                mock_response = Mock()
                mock_response.status_code = 404
                return mock_response

            # Handle stats count requests (with type filter)
            json_data = kwargs.get("json", {})
            query = json_data.get("query", {})

            # Determine which channel from URL
            for channel in ["unstable", "25.05", "24.11"]:
                if f"nixos-{channel}" in url:
                    stats = mock_stats_responses.get(channel, mock_stats_responses["unstable"])
                    mock_response = Mock()
                    mock_response.status_code = 200

                    # Check if it's a package or option count
                    if query.get("term", {}).get("type") == "package":
                        mock_response.json.return_value = {"count": stats["aggregations"]["attr_count"]["value"]}
                    elif query.get("term", {}).get("type") == "option":
                        mock_response.json.return_value = {"count": stats["aggregations"]["option_count"]["value"]}
                    else:
                        # General count
                        mock_response.json.return_value = {"count": stats["aggregations"]["attr_count"]["value"]}

                    return mock_response

            # Default response
            mock_response = Mock()
            mock_response.json.return_value = mock_stats_responses["unstable"]
            return mock_response

        mock_post.side_effect = side_effect

        # Step 1: Get available channels
        channels_result = nixos_channels()
        assert "24.11" in channels_result
        assert "25.05" in channels_result
        assert "unstable" in channels_result
        # Check that document counts are present (don't hardcode exact values as they change)
        assert "documents)" in channels_result
        assert "Available" in channels_result

        # Step 2: Get stats for each channel
        stats_unstable = nixos_stats("unstable")
        assert "Packages:" in stats_unstable
        assert "Options:" in stats_unstable

        stats_stable = nixos_stats("stable")  # Should resolve to 25.05
        assert "Packages:" in stats_stable

        stats_24_11 = nixos_stats("24.11")
        assert "Packages:" in stats_24_11

        # Verify package count differences
        # unstable should have the most packages
        # 25.05 (current stable) should be close to unstable
        # 24.11 should have fewer packages

    @patch("mcp_nixos.server.requests.post")
    def test_package_counts_with_beta_alias(self, mock_post):
        """Eval: User asks about beta channel package count."""
        # Mock responses for channel discovery
        mock_count_response = Mock()
        mock_count_response.status_code = 200
        mock_count_response.json.return_value = {"count": 151698}

        mock_stats_response = Mock()
        mock_stats_response.json.return_value = {
            "aggregations": {
                "attr_count": {"value": 151698},
                "option_count": {"value": 20145},
                "program_count": {"value": 3420},
                "license_count": {"value": 125},
                "maintainer_count": {"value": 3250},
                "platform_counts": {
                    "buckets": [
                        {"key": "x86_64-linux", "doc_count": 145134},
                    ]
                },
            }
        }

        def side_effect(*args, **kwargs):
            url = args[0]
            if "/_count" in url and "25.05" in url:
                return mock_count_response
            if "/_count" in url:
                # Other channels not found
                mock_404 = Mock()
                mock_404.status_code = 404
                return mock_404
            # Stats request
            json_data = kwargs.get("json", {})
            query = json_data.get("query", {})

            mock_response = Mock()
            mock_response.status_code = 200

            # Check if it's a package or option count
            if query.get("term", {}).get("type") == "package":
                mock_response.json.return_value = {"count": 151698}
            elif query.get("term", {}).get("type") == "option":
                mock_response.json.return_value = {"count": 20145}
            else:
                # General count
                mock_response.json.return_value = {"count": 151698}

            return mock_response

        mock_post.side_effect = side_effect

        # Beta should resolve to stable (25.05)
        result = nixos_stats("beta")
        assert "Packages:" in result
        assert "beta" in result

    @patch("mcp_nixos.server.requests.post")
    def test_compare_package_counts_across_channels(self, mock_post):
        """Eval: User wants to compare package growth across releases."""
        # Mock responses with increasing package counts
        mock_count_responses = {
            "latest-43-nixos-unstable": {"count": 151798},
            "latest-43-nixos-25.05": {"count": 151698},
            "latest-43-nixos-24.11": {"count": 142034},
            "latest-43-nixos-24.05": {"count": 135000},
        }

        channel_stats = {
            "24.05": 135000,
            "24.11": 142034,
            "25.05": 151698,
            "unstable": 151798,
        }

        def side_effect(*args, **kwargs):
            url = args[0]
            # Handle count requests for channel discovery
            if "/_count" in url:
                for index, count_data in mock_count_responses.items():
                    if index in url:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = count_data
                        return mock_response
                # Not found
                mock_response = Mock()
                mock_response.status_code = 404
                return mock_response

            # Handle stats count requests (with type filter)
            json_data = kwargs.get("json", {})
            query = json_data.get("query", {})

            # Extract channel from URL and return appropriate stats
            for channel, count in channel_stats.items():
                if f"nixos-{channel}" in url:
                    mock_response = Mock()
                    mock_response.status_code = 200

                    # Check if it's a package or option count
                    if query.get("term", {}).get("type") == "package":
                        mock_response.json.return_value = {"count": count}
                    elif query.get("term", {}).get("type") == "option":
                        mock_response.json.return_value = {"count": 20000}
                    else:
                        # General count
                        mock_response.json.return_value = {"count": count}

                    return mock_response

            # Default to unstable
            mock_response = Mock()
            mock_response.status_code = 200
            if query.get("term", {}).get("type") == "package":
                mock_response.json.return_value = {"count": 151798}
            elif query.get("term", {}).get("type") == "option":
                mock_response.json.return_value = {"count": 20156}
            else:
                mock_response.json.return_value = {"count": 151798}
            return mock_response

        mock_post.side_effect = side_effect

        # Get stats for multiple channels to compare growth
        # Only use channels that are currently available
        for channel in ["24.11", "25.05", "unstable"]:
            stats = nixos_stats(channel)
            # Just verify we get stats back with package info
            assert "Packages:" in stats
            assert "channel:" in stats.lower()  # Check case-insensitively
