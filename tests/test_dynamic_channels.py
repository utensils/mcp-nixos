#!/usr/bin/env python3
"""Comprehensive tests for dynamic channel lifecycle management."""

from unittest.mock import Mock, patch
import requests
from mcp_nixos.server import (
    channel_cache,
    get_channels,
    nixos_channels,
    nixos_stats,
    nixos_search,
    nixos_info,
)


class TestDynamicChannelLifecycle:
    """Test dynamic channel detection and lifecycle management."""

    def setup_method(self):
        """Clear caches before each test."""
        channel_cache.available_channels = None
        channel_cache.resolved_channels = None

    @patch("requests.post")
    def test_channel_discovery_future_proof(self, mock_post):
        """Test discovery works with future NixOS releases."""
        # Simulate future release state
        future_responses = {
            "latest-44-nixos-unstable": {"count": 160000},
            "latest-44-nixos-25.11": {"count": 155000},  # New stable
            "latest-44-nixos-25.05": {"count": 152000},  # Old stable
            "latest-43-nixos-25.05": {"count": 151000},  # Legacy
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in future_responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        # Test discovery
        available = channel_cache.get_available()
        assert "latest-44-nixos-unstable" in available
        assert "latest-44-nixos-25.11" in available

        # Test resolution - should pick 25.11 as new stable
        channels = channel_cache.get_resolved()
        assert channels["stable"] == "latest-44-nixos-25.11"
        assert channels["unstable"] == "latest-44-nixos-unstable"
        assert channels["25.11"] == "latest-44-nixos-25.11"
        assert channels["25.05"] == "latest-44-nixos-25.05"

    @patch("requests.post")
    def test_stable_detection_by_version_priority(self, mock_post):
        """Test stable detection prioritizes higher version numbers."""
        # Same generation, different versions
        responses = {
            "latest-43-nixos-24.11": {"count": 150000},
            "latest-43-nixos-25.05": {"count": 140000},  # Lower count but higher version
            "latest-43-nixos-unstable": {"count": 155000},
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        channels = channel_cache.get_resolved()
        # Should pick 25.05 despite lower count (higher version)
        assert channels["stable"] == "latest-43-nixos-25.05"

    @patch("requests.post")
    def test_stable_detection_by_count_when_same_version(self, mock_post):
        """Test stable detection uses count as tiebreaker."""
        responses = {
            "latest-43-nixos-25.05": {"count": 150000},
            "latest-44-nixos-25.05": {"count": 155000},  # Higher count, same version
            "latest-43-nixos-unstable": {"count": 160000},
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        channels = channel_cache.get_resolved()
        # Should pick higher count for same version
        assert channels["stable"] == "latest-44-nixos-25.05"

    @patch("requests.post")
    def test_channel_discovery_handles_no_channels(self, mock_post):
        """Test graceful handling when no channels are available."""
        mock_post.return_value = Mock(status_code=404)

        available = channel_cache.get_available()
        assert available == {}

        channels = channel_cache.get_resolved()
        assert channels == {}

    @patch("requests.post")
    def test_channel_discovery_partial_availability(self, mock_post):
        """Test handling when only some channels are available."""
        responses = {
            "latest-43-nixos-unstable": {"count": 150000},
            # No stable releases available
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        channels = channel_cache.get_resolved()
        assert channels["unstable"] == "latest-43-nixos-unstable"
        assert "stable" not in channels  # No stable release found

    @patch("mcp_nixos.server.channel_cache.get_resolved")
    def test_nixos_stats_with_dynamic_channels(self, mock_resolve):
        """Test nixos_stats works with dynamically resolved channels."""
        mock_resolve.return_value = {
            "stable": "latest-44-nixos-25.11",
            "unstable": "latest-44-nixos-unstable",
        }

        with patch("requests.post") as mock_post:
            # Mock successful response
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"count": 1000}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            # Should work with new stable
            result = nixos_stats("stable")
            # Should not error and should contain statistics
            assert "NixOS Statistics" in result
            assert "stable" in result
            # Should have made API calls
            assert mock_post.called

    @patch("mcp_nixos.server.channel_cache.get_resolved")
    def test_nixos_search_with_dynamic_channels(self, mock_resolve):
        """Test nixos_search works with dynamically resolved channels."""
        mock_resolve.return_value = {
            "stable": "latest-44-nixos-25.11",
            "unstable": "latest-44-nixos-unstable",
        }

        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = []

            result = nixos_search("test", channel="stable")
            assert "No packages found" in result

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_nixos_channels_tool_shows_current_stable(self, mock_discover):
        """Test nixos_channels tool clearly shows current stable version."""
        mock_discover.return_value = {
            "latest-44-nixos-25.11": "155,000 documents",
            "latest-44-nixos-unstable": "160,000 documents",
        }

        with patch("mcp_nixos.server.channel_cache.get_resolved") as mock_resolve:
            mock_resolve.return_value = {
                "stable": "latest-44-nixos-25.11",
                "25.11": "latest-44-nixos-25.11",
                "unstable": "latest-44-nixos-unstable",
            }

            result = nixos_channels()
            assert "stable (current: 25.11)" in result
            assert "latest-44-nixos-25.11" in result
            assert "dynamically discovered" in result

    def test_channel_suggestions_work_with_dynamic_channels(self):
        """Test channel suggestions work with dynamic resolution."""
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-44-nixos-25.11",
                "unstable": "latest-44-nixos-unstable",
                "25.11": "latest-44-nixos-25.11",
            }

            result = nixos_stats("invalid-channel")
            assert "Available channels:" in result
            assert any(ch in result for ch in ["stable", "unstable"])

    @patch("requests.post")
    def test_caching_behavior(self, mock_post):
        """Test that caching works correctly."""
        responses = {
            "latest-43-nixos-unstable": {"count": 150000},
            "latest-43-nixos-25.05": {"count": 145000},
        }

        call_count = 0

        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        # First call should hit API
        channels1 = get_channels()
        first_call_count = call_count

        # Second call should use cache
        channels2 = get_channels()
        second_call_count = call_count

        assert channels1 == channels2
        assert second_call_count == first_call_count  # No additional API calls

    @patch("requests.post")
    def test_malformed_version_handling(self, mock_post):
        """Test handling of malformed version numbers."""
        responses = {
            "latest-43-nixos-unstable": {"count": 150000},
            "latest-43-nixos-badversion": {"count": 145000},  # Invalid version
            "latest-43-nixos-25.05": {"count": 140000},  # Valid version
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        channels = channel_cache.get_resolved()
        # Should ignore malformed version and use valid one
        assert channels["stable"] == "latest-43-nixos-25.05"
        assert "badversion" not in channels

    @patch("requests.post")
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors during discovery."""
        mock_post.side_effect = requests.ConnectionError("Network error")

        available = channel_cache.get_available()
        assert available == {}

        channels = channel_cache.get_resolved()
        assert channels == {}

    @patch("requests.post")
    def test_zero_document_filtering(self, mock_post):
        """Test that channels with zero documents are filtered out."""
        responses = {
            "latest-43-nixos-unstable": {"count": 150000},
            "latest-43-nixos-25.05": {"count": 0},  # Empty index
            "latest-43-nixos-24.11": {"count": 140000},
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        available = channel_cache.get_available()
        assert "latest-43-nixos-unstable" in available
        assert "latest-43-nixos-25.05" not in available  # Filtered out
        assert "latest-43-nixos-24.11" in available

    @patch("requests.post")
    def test_version_comparison_edge_cases(self, mock_post):
        """Test version comparison with edge cases."""
        responses = {
            "latest-43-nixos-unstable": {"count": 150000},
            "latest-43-nixos-20.09": {"count": 100000},  # Old version
            "latest-43-nixos-25.05": {"count": 145000},  # Current
            "latest-43-nixos-30.05": {"count": 140000},  # Future
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        channels = channel_cache.get_resolved()
        # Should pick highest version (30.05)
        assert channels["stable"] == "latest-43-nixos-30.05"
        assert "20.09" in channels  # Old versions still mapped
        assert "25.05" in channels
        assert "30.05" in channels

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_beta_alias_behavior(self, mock_discover):
        """Test that beta is always an alias for stable."""
        mock_discover.return_value = {
            "latest-44-nixos-25.11": "155,000 documents",
            "latest-44-nixos-unstable": "160,000 documents",
        }

        channels = channel_cache.get_resolved()
        assert "beta" in channels
        assert channels["beta"] == channels["stable"]

    def test_integration_with_all_tools(self):
        """Test that all tools work with dynamic channels."""
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-44-nixos-25.11",
                "unstable": "latest-44-nixos-unstable",
            }

            with patch("mcp_nixos.server.es_query") as mock_es:
                mock_es.return_value = []

                with patch("requests.post") as mock_post:
                    # Mock successful response for nixos_stats
                    mock_resp = Mock()
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = {"count": 1000}
                    mock_resp.raise_for_status.return_value = None
                    mock_post.return_value = mock_resp

                    # Test all tools that use channels
                    tools_to_test = [
                        lambda: nixos_search("test", channel="stable"),
                        lambda: nixos_info("test", channel="stable"),
                        lambda: nixos_stats("stable"),
                    ]

                    for tool in tools_to_test:
                        result = tool()
                        # Should not error due to channel resolution
                        assert (
                            "Error" not in result
                            or "not found" in result
                            or "No packages found" in result
                            or "NixOS Statistics" in result
                        )
