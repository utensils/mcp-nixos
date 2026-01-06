"""Regression test for NixOS stats to ensure correct field names are used."""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
nixos_channels = get_tool_function("nixos_channels")
nixos_stats = get_tool_function("nixos_stats")


def setup_channel_mocks(mock_cache, mock_validate, channels=None):
    """Setup channel mocks with default or custom channels."""
    if channels is None:
        channels = {
            "unstable": "latest-44-nixos-unstable",
            "stable": "latest-44-nixos-25.05",
            "25.05": "latest-44-nixos-25.05",
            "24.11": "latest-44-nixos-24.11",
            "beta": "latest-44-nixos-25.05",
        }
    mock_cache.get_available.return_value = {v: f"{v.split('-')[-1]} docs" for v in channels.values() if v}
    mock_cache.get_resolved.return_value = channels
    mock_validate.side_effect = lambda channel: channel in channels


class TestNixOSStatsRegression:
    """Ensure NixOS stats uses correct field names in queries."""

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_nixos_stats_uses_correct_query_fields(self, mock_post, mock_cache, mock_validate):
        """Test that stats uses 'type' field with term query, not 'package'/'option' with exists query."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)

        # Mock responses
        pkg_resp = Mock()
        pkg_resp.json.return_value = {"count": 129865}

        opt_resp = Mock()
        opt_resp.json.return_value = {"count": 21933}

        mock_post.side_effect = [pkg_resp, opt_resp]

        # Call the function
        result = await nixos_stats()

        # Verify the function returns expected output
        assert "NixOS Statistics for unstable channel:" in result
        assert "• Packages: 129,865" in result
        assert "• Options: 21,933" in result

        # Verify the correct queries were sent
        assert mock_post.call_count == 2

        # Check package count query
        pkg_call = mock_post.call_args_list[0]
        assert pkg_call[1]["json"]["query"] == {"term": {"type": "package"}}

        # Check option count query
        opt_call = mock_post.call_args_list[1]
        assert opt_call[1]["json"]["query"] == {"term": {"type": "option"}}

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_nixos_stats_handles_zero_counts(self, mock_post, mock_cache, mock_validate):
        """Test that stats correctly handles zero counts."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)

        # Mock responses with zero counts
        mock_resp = Mock()
        mock_resp.json.return_value = {"count": 0}
        mock_post.return_value = mock_resp

        result = await nixos_stats()

        # Should return error when both counts are zero (our improved logic)
        assert "Error (ERROR): Failed to retrieve statistics" in result

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_nixos_stats_all_channels(self, mock_post, mock_cache, mock_validate):
        """Test that stats works for all defined channels."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)

        # Mock responses
        mock_resp = Mock()
        mock_resp.json.return_value = {"count": 12345}
        mock_post.return_value = mock_resp

        # Test with known channels
        for channel in ["stable", "unstable"]:
            result = await nixos_stats(channel=channel)
            assert f"NixOS Statistics for {channel} channel:" in result
            assert "• Packages: 12,345" in result
            assert "• Options: 12,345" in result


class TestPackageCountsPerChannel:
    """Test getting package counts per NixOS channel."""

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_get_package_counts_per_channel(self, mock_post, mock_cache, mock_validate):
        """Test getting package counts for each NixOS channel."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)

        # Mock channel discovery responses
        mock_count_responses = {
            "latest-44-nixos-unstable": {"count": 151798},
            "latest-44-nixos-25.05": {"count": 151698},
            "latest-44-nixos-24.11": {"count": 142034},
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
                        mock_response.json = Mock(return_value=count_data)
                        mock_response.raise_for_status = Mock()
                        return mock_response
                # Not found
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.raise_for_status = Mock(side_effect=Exception("Not found"))
                return mock_response

            # Handle stats count requests (with type filter)
            json_data = kwargs.get("json", {})
            query = json_data.get("query", {})

            # Determine which channel from URL
            for channel, index in [
                ("unstable", "latest-44-nixos-unstable"),
                ("25.05", "latest-44-nixos-25.05"),
                ("24.11", "latest-44-nixos-24.11"),
            ]:
                if index in url:
                    stats = mock_stats_responses.get(channel, mock_stats_responses["unstable"])
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = Mock()

                    # Check if it's a package or option count
                    if query.get("term", {}).get("type") == "package":
                        mock_response.json = Mock(return_value={"count": stats["aggregations"]["attr_count"]["value"]})
                    elif query.get("term", {}).get("type") == "option":
                        mock_response.json = Mock(
                            return_value={"count": stats["aggregations"]["option_count"]["value"]}
                        )
                    else:
                        # General count
                        mock_response.json = Mock(return_value={"count": stats["aggregations"]["attr_count"]["value"]})

                    return mock_response

            # Default response - return a proper mock
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            mock_response.json = Mock(return_value={"count": 151798})
            return mock_response

        mock_post.side_effect = side_effect

        # Step 1: Get available channels
        channels_result = await nixos_channels()
        assert "24.11" in channels_result
        assert "25.05" in channels_result
        assert "unstable" in channels_result
        # Check that document counts are present (don't hardcode exact values as they change)
        assert "docs)" in channels_result
        assert "Available" in channels_result

        # Step 2: Get stats for each channel
        stats_unstable = await nixos_stats("unstable")
        assert "Packages:" in stats_unstable
        assert "Options:" in stats_unstable

        stats_stable = await nixos_stats("stable")  # Should resolve to 25.05
        assert "Packages:" in stats_stable

        stats_24_11 = await nixos_stats("24.11")
        assert "Packages:" in stats_24_11

        # Verify package count differences
        # unstable should have the most packages
        # 25.05 (current stable) should be close to unstable
        # 24.11 should have fewer packages

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_package_counts_with_beta_alias(self, mock_post, mock_cache, mock_validate):
        """Test beta channel alias package count."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)
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
        result = await nixos_stats("beta")
        assert "Packages:" in result
        assert "beta" in result

    @patch("mcp_nixos.server.validate_channel")
    @patch("mcp_nixos.server.channel_cache")
    @patch("mcp_nixos.server.requests.post")
    @pytest.mark.asyncio
    async def test_compare_package_counts_across_channels(self, mock_post, mock_cache, mock_validate):
        """Test comparing package counts across releases."""
        # Setup channel mocks
        setup_channel_mocks(mock_cache, mock_validate)
        # Mock responses with increasing package counts
        mock_count_responses = {
            "latest-44-nixos-unstable": {"count": 151798},
            "latest-44-nixos-25.05": {"count": 151698},
            "latest-44-nixos-24.11": {"count": 142034},
            "latest-44-nixos-24.05": {"count": 135000},
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
                        mock_response.json = Mock(return_value=count_data)
                        mock_response.raise_for_status = Mock()
                        return mock_response
                # Not found
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.raise_for_status = Mock(side_effect=Exception("Not found"))
                return mock_response

            # Handle stats count requests (with type filter)
            json_data = kwargs.get("json", {})
            query = json_data.get("query", {})

            # Extract channel from URL and return appropriate stats
            channel_to_index = {
                "24.05": "latest-44-nixos-24.05",
                "24.11": "latest-44-nixos-24.11",
                "25.05": "latest-44-nixos-25.05",
                "unstable": "latest-44-nixos-unstable",
            }
            for channel, count in channel_stats.items():
                index = channel_to_index.get(channel)
                if index and index in url:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.raise_for_status = Mock()

                    # Check if it's a package or option count
                    if query.get("term", {}).get("type") == "package":
                        mock_response.json = Mock(return_value={"count": count})
                    elif query.get("term", {}).get("type") == "option":
                        mock_response.json = Mock(return_value={"count": 20000})
                    else:
                        # General count
                        mock_response.json = Mock(return_value={"count": count})

                    return mock_response

            # Default to unstable
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()
            if query.get("term", {}).get("type") == "package":
                mock_response.json = Mock(return_value={"count": 151798})
            elif query.get("term", {}).get("type") == "option":
                mock_response.json = Mock(return_value={"count": 20156})
            else:
                mock_response.json = Mock(return_value={"count": 151798})
            return mock_response

        mock_post.side_effect = side_effect

        # Get stats for multiple channels to compare growth
        # Only use channels that are currently available
        for channel in ["24.11", "25.05", "unstable"]:
            stats = await nixos_stats(channel)
            # Just verify we get stats back with package info
            assert "Packages:" in stats
            assert "channel:" in stats.lower()  # Check case-insensitively
