"""Regression test for NixOS stats to ensure correct field names are used."""

from unittest.mock import patch, Mock

from mcp_nixos.server import nixos_stats


class TestNixOSStatsRegression:
    """Ensure NixOS stats uses correct field names in queries."""

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_uses_correct_query_fields(self, mock_post):
        """Test that stats uses 'type' field with term query, not 'package'/'option' with exists query."""
        # Mock responses
        pkg_resp = Mock()
        pkg_resp.json.return_value = {"count": 129865}

        opt_resp = Mock()
        opt_resp.json.return_value = {"count": 21933}

        mock_post.side_effect = [pkg_resp, opt_resp]

        # Call the function
        result = nixos_stats()

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

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_handles_zero_counts(self, mock_post):
        """Test that stats correctly handles zero counts."""
        # Mock responses with zero counts
        mock_resp = Mock()
        mock_resp.json.return_value = {"count": 0}
        mock_post.return_value = mock_resp

        result = nixos_stats()

        # Should return error when both counts are zero (our improved logic)
        assert "Error (ERROR): Failed to retrieve statistics" in result

    @patch("mcp_nixos.server.requests.post")
    def test_nixos_stats_all_channels(self, mock_post):
        """Test that stats works for all defined channels."""
        # Mock responses
        mock_resp = Mock()
        mock_resp.json.return_value = {"count": 12345}
        mock_post.return_value = mock_resp

        # Test with known channels
        for channel in ["stable", "unstable"]:
            result = nixos_stats(channel=channel)
            assert f"NixOS Statistics for {channel} channel:" in result
            assert "• Packages: 12,345" in result
            assert "• Options: 12,345" in result
