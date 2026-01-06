"""Tests for the main entry point in server module."""

from inspect import signature
from unittest.mock import patch

from mcp_nixos.server import main, mcp


class TestMainModule:
    """Test the main entry point."""

    @patch("mcp_nixos.server.mcp")
    def test_main_execution(self, mock_mcp):
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once()

    def test_mcp_exists(self):
        assert mcp is not None


class TestServerImport:
    """Test server module imports."""

    def test_required_attributes(self):
        from mcp_nixos import server

        # Core MCP components
        assert hasattr(server, "mcp")
        assert hasattr(server, "main")

        # MCP tools
        assert hasattr(server, "nix")
        assert hasattr(server, "nix_versions")

        # Helper functions
        assert hasattr(server, "error")
        assert hasattr(server, "es_query")
        assert hasattr(server, "parse_html_options")
        assert hasattr(server, "get_channels")

    def test_main_signature(self):
        sig = signature(main)
        assert len(sig.parameters) == 0
        assert callable(main)
