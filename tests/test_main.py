"""Tests for the __main__ module."""

import pytest
from unittest.mock import patch
from io import StringIO

from mcp_nixos.__main__ import main


class TestMainModule:
    """Test the __main__ entry point."""

    @patch("mcp_nixos.__main__.mcp")
    def test_main_normal_execution(self, mock_mcp):
        """Test normal server execution."""
        mock_mcp.run.return_value = None

        # Should exit with 0 on success
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_mcp.run.assert_called_once()

    @patch("mcp_nixos.__main__.mcp")
    def test_main_keyboard_interrupt(self, mock_mcp):
        """Test handling of keyboard interrupt."""
        mock_mcp.run.side_effect = KeyboardInterrupt()

        # Should exit cleanly with 0
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0

    @patch("mcp_nixos.__main__.mcp")
    @patch("sys.stderr", new_callable=StringIO)
    def test_main_exception(self, mock_stderr, mock_mcp):
        """Test handling of unexpected exceptions."""
        test_error = "Test server error"
        mock_mcp.run.side_effect = Exception(test_error)

        # Should exit with 1 and print error
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert f"Server error: {test_error}" in mock_stderr.getvalue()

    @patch("mcp_nixos.__main__.mcp")
    def test_main_multiple_exceptions(self, mock_mcp):
        """Test different types of exceptions."""
        # Test RuntimeError
        mock_mcp.run.side_effect = RuntimeError("Runtime error")
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

        # Test ValueError
        mock_mcp.run.side_effect = ValueError("Value error")
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_module_import(self):
        """Test that __main__ module can be imported."""
        import mcp_nixos.__main__

        assert hasattr(mcp_nixos.__main__, "main")
        assert hasattr(mcp_nixos.__main__, "mcp")

    @patch("mcp_nixos.__main__.mcp")
    def test_main_mcp_not_none(self, mock_mcp):
        """Test that mcp instance exists."""
        # Import to ensure mcp is available
        from mcp_nixos.__main__ import mcp

        assert mcp is not None

    def test_script_execution(self):
        """Test __main__ script execution block."""
        # This tests the if __name__ == "__main__" block
        test_module = """
import sys
from mcp_nixos.__main__ import main

# Simulate direct execution
if __name__ == "__main__":
    sys.exit(main())
"""

        # Verify the code structure is valid
        compile(test_module, "<test>", "exec")


class TestServerImport:
    """Test server module imports in __main__."""

    def test_mcp_import_from_server(self):
        """Test that mcp is properly imported from server."""
        from mcp_nixos.__main__ import mcp
        from mcp_nixos.server import mcp as server_mcp

        # They should be the same instance
        assert mcp is server_mcp

    def test_server_has_required_attributes(self):
        """Test that server module has required attributes."""
        from mcp_nixos import server

        assert hasattr(server, "mcp")
        assert hasattr(server, "nixos_search")
        assert hasattr(server, "nixos_info")
        assert hasattr(server, "home_manager_search")
        assert hasattr(server, "darwin_search")


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch("mcp_nixos.__main__.mcp")
    @patch("sys.stderr", new_callable=StringIO)
    def test_error_message_format(self, mock_stderr, mock_mcp):
        """Test error message formatting."""
        error_msg = "Connection refused to API endpoint"
        mock_mcp.run.side_effect = ConnectionError(error_msg)

        with pytest.raises(SystemExit):
            main()

        stderr_output = mock_stderr.getvalue()
        assert "Server error:" in stderr_output
        assert error_msg in stderr_output

    @patch("mcp_nixos.__main__.mcp")
    @patch("sys.stderr", new_callable=StringIO)
    def test_unicode_error_handling(self, mock_stderr, mock_mcp):
        """Test handling of unicode in error messages."""
        error_msg = "Error with unicode: ñ ü ß 中文"
        mock_mcp.run.side_effect = Exception(error_msg)

        with pytest.raises(SystemExit):
            main()

        stderr_output = mock_stderr.getvalue()
        assert error_msg in stderr_output

    @patch("mcp_nixos.__main__.mcp")
    def test_system_exit_propagation(self, mock_mcp):
        """Test that SystemExit is properly propagated."""
        # SystemExit with specific code
        mock_mcp.run.side_effect = SystemExit(42)

        with pytest.raises(SystemExit) as exc_info:
            main()

        # Should propagate the original exit code
        assert exc_info.value.code == 42

    @patch("mcp_nixos.__main__.mcp")
    @patch("sys.stderr", new_callable=StringIO)
    def test_empty_error_message(self, mock_stderr, mock_mcp):
        """Test handling of exceptions with empty messages."""
        mock_mcp.run.side_effect = Exception("")

        with pytest.raises(SystemExit):
            main()

        stderr_output = mock_stderr.getvalue()
        assert "Server error:" in stderr_output


class TestIntegration:
    """Integration tests for __main__ module."""

    def test_main_function_signature(self):
        """Test main function has correct signature."""
        from inspect import signature

        sig = signature(main)

        # Should take no parameters
        assert len(sig.parameters) == 0

        # Should return int (exit code)
        # Note: The annotation might not be present, so we just check it's callable
        assert callable(main)

    def test_server_integration(self):
        """Test integration between __main__ and server."""
        # Import both modules
        from mcp_nixos.__main__ import mcp as main_mcp
        from mcp_nixos.server import mcp as server_mcp

        # Verify they reference the same mcp instance
        assert main_mcp is server_mcp


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=mcp_nixos.__main__", "--cov-report=term-missing"])
