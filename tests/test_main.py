"""Tests for the main entry point in server module."""

import os
from inspect import signature
from unittest.mock import patch

import pytest
from mcp_nixos.server import env_bool, main, mcp


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


@pytest.mark.unit
class TestEnvBool:
    """Test the env_bool helper function."""

    def test_default_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MCP_NIXOS_MISSING") is False

    def test_default_true_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MCP_NIXOS_MISSING", default=True) is True

    @pytest.mark.parametrize("value", ["1", "true", "True", "yes", "y", "on", " true "])
    def test_true_values(self, value):
        with patch.dict(os.environ, {"MCP_TEST": value}):
            assert env_bool("MCP_TEST") is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "n", "off", ""])
    def test_false_values(self, value):
        with patch.dict(os.environ, {"MCP_TEST": value}):
            assert env_bool("MCP_TEST") is False

    @pytest.mark.parametrize("value", ["treu", "2", "nah"])
    def test_invalid_value_raises(self, value):
        with patch.dict(os.environ, {"MCP_TEST": value}):
            with pytest.raises(ValueError, match="must be a boolean"):
                env_bool("MCP_TEST")


@pytest.mark.unit
class TestMainTransport:
    """Test transport selection in main()."""

    @patch("mcp_nixos.server.mcp")
    @patch.dict(os.environ, {}, clear=False)
    def test_stdio_default(self, mock_mcp):
        # Remove transport env var if present
        os.environ.pop("MCP_NIXOS_TRANSPORT", None)
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once_with()

    @patch("mcp_nixos.server.mcp")
    @patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "stdio"})
    def test_stdio_explicit(self, mock_mcp):
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once_with()

    @patch("mcp_nixos.server.mcp")
    @patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "http"})
    def test_http_defaults(self, mock_mcp):
        # Remove optional env vars
        os.environ.pop("MCP_NIXOS_HOST", None)
        os.environ.pop("MCP_NIXOS_PORT", None)
        os.environ.pop("MCP_NIXOS_PATH", None)
        os.environ.pop("MCP_NIXOS_STATELESS_HTTP", None)
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once_with(
            transport="http", host="127.0.0.1", port=8000, path="/mcp", stateless_http=False
        )

    @patch("mcp_nixos.server.mcp")
    @patch.dict(
        os.environ,
        {
            "MCP_NIXOS_TRANSPORT": "http",
            "MCP_NIXOS_HOST": "0.0.0.0",
            "MCP_NIXOS_PORT": "9090",
            "MCP_NIXOS_PATH": "/api/mcp",
        },
    )
    def test_http_custom(self, mock_mcp):
        os.environ.pop("MCP_NIXOS_STATELESS_HTTP", None)
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once_with(
            transport="http", host="0.0.0.0", port=9090, path="/api/mcp", stateless_http=False
        )

    @patch("mcp_nixos.server.mcp")
    @patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "http", "MCP_NIXOS_STATELESS_HTTP": "1"})
    def test_http_stateless(self, mock_mcp):
        os.environ.pop("MCP_NIXOS_HOST", None)
        os.environ.pop("MCP_NIXOS_PORT", None)
        os.environ.pop("MCP_NIXOS_PATH", None)
        mock_mcp.run.return_value = None
        main()
        mock_mcp.run.assert_called_once_with(
            transport="http", host="127.0.0.1", port=8000, path="/mcp", stateless_http=True
        )

    @patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "grpc"})
    def test_invalid_transport_exits(self):
        with pytest.raises(SystemExit, match="1"):
            main()

    @patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "http", "MCP_NIXOS_PORT": "abc"})
    def test_invalid_port_exits(self):
        with pytest.raises(SystemExit, match="1"):
            main()

    @pytest.mark.parametrize("port", ["0", "99999"])
    def test_port_out_of_range_exits(self, port):
        with patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "http", "MCP_NIXOS_PORT": port}):
            with pytest.raises(SystemExit, match="1"):
                main()

    @pytest.mark.parametrize("path", ["", "no-slash", "//double"])
    def test_invalid_path_exits(self, path):
        with patch.dict(os.environ, {"MCP_NIXOS_TRANSPORT": "http", "MCP_NIXOS_PATH": path}):
            with pytest.raises(SystemExit, match="1"):
                main()
