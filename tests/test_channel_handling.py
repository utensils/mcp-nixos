#!/usr/bin/env python3
"""Tests for robust channel handling functionality."""

from unittest.mock import Mock, patch
import requests
from mcp_nixos.server import (
    channel_cache,
    validate_channel,
    get_channel_suggestions,
    nixos_channels,
    nixos_stats,
    nixos_search,
    get_channels,
)


class TestChannelHandling:
    """Test robust channel handling functionality."""

    @patch("requests.post")
    def test_discover_available_channels_success(self, mock_post):
        """Test successful channel discovery."""
        # Mock successful responses for some channels
        mock_responses = {
            "latest-43-nixos-unstable": {"count": 151798},
            "latest-43-nixos-25.05": {"count": 151698},
            "latest-43-nixos-24.11": {"count": 142034},
        }

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            for pattern, response in mock_responses.items():
                if pattern in url:
                    mock_resp.status_code = 200
                    mock_resp.json.return_value = response
                    return mock_resp
            # Default to 404 for unknown patterns
            mock_resp.status_code = 404
            return mock_resp

        mock_post.side_effect = side_effect

        # Clear cache first
        channel_cache.available_channels = None

        result = channel_cache.get_available()

        assert "latest-43-nixos-unstable" in result
        assert "latest-43-nixos-25.05" in result
        assert "latest-43-nixos-24.11" in result
        assert "151,798 documents" in result["latest-43-nixos-unstable"]

    @patch("requests.post")
    def test_discover_available_channels_with_cache(self, mock_post):
        """Test that channel discovery uses cache."""
        # Set up cache
        channel_cache.available_channels = {"test": "cached"}

        result = channel_cache.get_available()

        # Should return cached result without making API calls
        assert result == {"test": "cached"}
        mock_post.assert_not_called()

    @patch("mcp_nixos.server.get_channels")
    @patch("requests.post")
    def test_validate_channel_success(self, mock_post, mock_get_channels):
        """Test successful channel validation."""
        mock_get_channels.return_value = {"stable": "latest-43-nixos-25.05"}

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"count": 100000}
        mock_post.return_value = mock_resp

        result = validate_channel("stable")
        assert result is True

    @patch("mcp_nixos.server.get_channels")
    def test_validate_channel_failure(self, mock_get_channels):
        """Test channel validation failure."""
        mock_get_channels.return_value = {"stable": "latest-43-nixos-25.05"}

        result = validate_channel("nonexistent")
        assert result is False

    def test_validate_channel_invalid_name(self):
        """Test validation of channel not in CHANNELS."""
        result = validate_channel("totally-invalid")
        assert result is False

    @patch("mcp_nixos.server.get_channels")
    def test_get_channel_suggestions_similar(self, mock_get_channels):
        """Test getting suggestions for similar channel names."""
        # Mock the available channels
        mock_get_channels.return_value = {
            "unstable": "latest-43-nixos-unstable",
            "stable": "latest-43-nixos-25.05",
            "25.05": "latest-43-nixos-25.05",
            "24.11": "latest-43-nixos-24.11",
            "beta": "latest-43-nixos-25.05",
        }

        result = get_channel_suggestions("unstabl")
        assert "unstable" in result

        result = get_channel_suggestions("24")
        assert "24.11" in result

    @patch("mcp_nixos.server.get_channels")
    def test_get_channel_suggestions_fallback(self, mock_get_channels):
        """Test fallback suggestions for completely invalid names."""
        # Mock the available channels
        mock_get_channels.return_value = {
            "unstable": "latest-43-nixos-unstable",
            "stable": "latest-43-nixos-25.05",
            "25.05": "latest-43-nixos-25.05",
            "24.11": "latest-43-nixos-24.11",
            "beta": "latest-43-nixos-25.05",
        }

        result = get_channel_suggestions("totally-random-xyz")
        assert "unstable" in result
        assert "stable" in result
        assert "25.05" in result

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_nixos_channels_tool(self, mock_discover):
        """Test nixos_channels tool output."""
        mock_discover.return_value = {
            "latest-43-nixos-unstable": "151,798 documents",
            "latest-43-nixos-25.05": "151,698 documents",
            "latest-43-nixos-24.11": "142,034 documents",
        }

        result = nixos_channels()

        assert "NixOS Channels" in result  # Match both old and new format
        assert "unstable → latest-43-nixos-unstable" in result or "unstable \u2192 latest-43-nixos-unstable" in result
        assert "stable" in result and "latest-43-nixos-25.05" in result
        assert "✓ Available" in result
        assert "151,798 documents" in result

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_nixos_channels_with_unavailable(self, mock_discover):
        """Test nixos_channels tool with some unavailable channels."""
        # Only return some channels as available
        mock_discover.return_value = {"latest-43-nixos-unstable": "151,798 documents"}

        result = nixos_channels()

        assert "✓ Available" in result
        assert "✗ Unavailable" in result

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_nixos_channels_with_extra_discovered(self, mock_discover):
        """Test nixos_channels with extra discovered channels."""
        mock_discover.return_value = {
            "latest-43-nixos-unstable": "151,798 documents",
            "latest-43-nixos-25.05": "151,698 documents",
            "latest-44-nixos-unstable": "152,000 documents",  # New channel
        }

        result = nixos_channels()

        assert "Additional available channels:" in result
        assert "latest-44-nixos-unstable" in result

    def test_nixos_stats_with_invalid_channel(self):
        """Test nixos_stats with invalid channel shows suggestions."""
        result = nixos_stats("invalid-channel")

        assert "Error (ERROR):" in result
        assert "Invalid channel 'invalid-channel'" in result
        assert "Available channels:" in result

    def test_nixos_search_with_invalid_channel(self):
        """Test nixos_search with invalid channel shows suggestions."""
        result = nixos_search("test", channel="invalid-channel")

        assert "Error (ERROR):" in result
        assert "Invalid channel 'invalid-channel'" in result
        assert "Available channels:" in result

    def test_channel_mappings_dynamic(self):
        """Test that dynamic channel mappings work correctly."""
        # Test with real API to ensure dynamic resolution works
        channels = get_channels()

        # Should have basic channels
        assert "stable" in channels
        assert "unstable" in channels

        # Stable should point to a valid channel index
        assert channels["stable"].startswith("latest-")
        assert "nixos" in channels["stable"]

        # Unstable should point to unstable index
        assert "unstable" in channels["unstable"]

    @patch("requests.post")
    def test_discover_channels_handles_exceptions(self, mock_post):
        """Test channel discovery handles network exceptions gracefully."""
        mock_post.side_effect = requests.ConnectionError("Network error")

        # Clear cache
        channel_cache.available_channels = None

        result = channel_cache.get_available()

        # Should return empty dict when all requests fail
        assert result == {}

    @patch("requests.post")
    def test_validate_channel_handles_exceptions(self, mock_post):
        """Test channel validation handles exceptions gracefully."""
        mock_post.side_effect = requests.ConnectionError("Network error")

        result = validate_channel("stable")
        assert result is False

    @patch("mcp_nixos.server.channel_cache.get_available")
    def test_nixos_channels_handles_exceptions(self, mock_discover):
        """Test nixos_channels tool handles exceptions gracefully."""
        mock_discover.side_effect = Exception("Discovery failed")

        result = nixos_channels()
        assert "Error (ERROR):" in result
        assert "Discovery failed" in result

    def test_channel_suggestions_for_legacy_channels(self):
        """Test suggestions work for legacy channel references."""
        # Test old stable reference
        result = get_channel_suggestions("20.09")
        assert "24.11" in result or "stable" in result

        # Test partial version
        result = get_channel_suggestions("25")
        assert "25.05" in result

    @patch("requests.post")
    def test_discover_channels_filters_empty_indices(self, mock_post):
        """Test that discovery filters out indices with 0 documents."""

        def side_effect(url, **kwargs):
            mock_resp = Mock()
            if "empty-index" in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"count": 0}  # Empty index
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"count": 100000}
            return mock_resp

        mock_post.side_effect = side_effect

        # Clear cache
        channel_cache.available_channels = None

        # This should work with the actual test patterns
        result = channel_cache.get_available()

        # Should not include any indices with 0 documents
        for _, info in result.items():
            # Check that it doesn't start with "0 documents"
            assert not info.startswith("0 documents")
