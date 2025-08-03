"""Tests for the main entry point in server module."""

from unittest.mock import patch

import pytest
from mcp_nixos.server import main


class TestMainModule:
    """Test the main entry point."""

    @patch("mcp_nixos.server.mcp")
    def test_main_normal_execution(self, mock_mcp):
        """Test normal server execution."""
        mock_mcp.run.return_value = None

        # Should not raise any exception
        main()
        mock_mcp.run.assert_called_once()

    @patch("mcp_nixos.server.mcp")
    def test_main_mcp_not_none(self, mock_mcp):
        """Test that mcp instance exists."""
        # Import to ensure mcp is available
        from mcp_nixos.server import mcp

        assert mcp is not None


class TestServerImport:
    """Test server module imports."""

    def test_mcp_import_from_server(self):
        """Test that mcp is properly available in server."""
        from mcp_nixos.server import mcp

        assert mcp is not None

    def test_server_has_required_attributes(self):
        """Test that server module has required attributes."""
        from mcp_nixos import server

        assert hasattr(server, "mcp")
        assert hasattr(server, "main")
        assert hasattr(server, "nixos_search")
        assert hasattr(server, "nixos_info")
        assert hasattr(server, "home_manager_search")
        assert hasattr(server, "darwin_search")


class TestIntegration:
    """Integration tests for main function."""

    def test_main_function_signature(self):
        """Test main function has correct signature."""
        from inspect import signature

        sig = signature(main)

        # Should take no parameters
        assert len(sig.parameters) == 0

        # Should be callable
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=mcp_nixos.server", "--cov-report=term-missing"])
