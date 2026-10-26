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


@pytest.mark.unit
def test_elasticsearch_url_env_override():
    # A subprocess, not importlib.reload: reloading config would replace APIError for later tests.
    import subprocess
    import sys

    code = "from mcp_nixos.config import NIXOS_API; print(NIXOS_API)"
    env = {**os.environ, "ELASTICSEARCH_URL": "http://localhost:9200/"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "http://localhost:9200"


@pytest.mark.unit
def test_http_session_retries():
    from mcp_nixos.utils import HTTP

    retry = HTTP.get_adapter("https://x").max_retries
    assert retry.total == 2
    assert retry.read == 0
    assert retry.respect_retry_after_header is False


def _concurrent_first_load(cache_get, payload_response):
    """Call cache_get from two threads with a slow HTTP.get; return the mock."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    def slow_get(*args, **kwargs):
        time.sleep(0.1)
        return payload_response

    with patch("mcp_nixos.caches.HTTP.get", side_effect=slow_get) as get:
        with ThreadPoolExecutor(2) as pool:
            for f in [pool.submit(cache_get), pool.submit(cache_get)]:
                f.result()
    return get


@pytest.mark.unit
def test_nvf_cache_serializes_first_load():
    from unittest.mock import MagicMock

    from mcp_nixos.caches import NvfCache

    from tests.test_nvf import NVF_OPTIONS_HTML

    resp = MagicMock(content=NVF_OPTIONS_HTML.encode())
    assert _concurrent_first_load(NvfCache().get_options, resp).call_count == 1


@pytest.mark.unit
def test_nixdev_cache_serializes_first_load():
    from unittest.mock import MagicMock

    from mcp_nixos.caches import NixDevCache

    resp = MagicMock(text='Search.setIndex({"docnames": []})')
    assert _concurrent_first_load(NixDevCache().get_index, resp).call_count == 1


@pytest.mark.unit
def test_noogle_cache_serializes_first_load():
    from unittest.mock import MagicMock

    from mcp_nixos.caches import NoogleCache

    resp = MagicMock()
    resp.json.return_value = {"data": [], "builtinTypes": {}}
    assert _concurrent_first_load(NoogleCache().get_data, resp).call_count == 1


@pytest.mark.unit
def test_nixvim_cache_failure_cooldown():
    import requests
    from mcp_nixos.caches import APIError, NixvimCache  # caches' own binding survives config reloads

    cache = NixvimCache()
    with (
        patch("mcp_nixos.caches.time.monotonic", return_value=1000.0),
        patch("mcp_nixos.caches.HTTP.get", side_effect=requests.Timeout) as get,
    ):
        with pytest.raises(APIError):
            cache.get_options()
        with pytest.raises(APIError):
            cache.get_options()
        assert get.call_count == 1

    with (
        patch("mcp_nixos.caches.time.monotonic", return_value=1061.0),
        patch("mcp_nixos.caches.HTTP.get", side_effect=requests.Timeout) as get,
    ):
        with pytest.raises(APIError):
            cache.get_options()
        assert get.call_count == 1


@pytest.mark.unit
def test_stats_nixos_reports_failed_count_as_unavailable():
    from unittest.mock import MagicMock

    import requests
    from mcp_nixos.sources.nixos import _stats_nixos

    ok = MagicMock()
    ok.json.return_value = {"count": 1234}
    bad = MagicMock()
    bad.raise_for_status.side_effect = requests.HTTPError("500")
    with (
        patch("mcp_nixos.sources.nixos.get_channels", return_value={"unstable": "idx"}),
        patch("mcp_nixos.sources.nixos.HTTP.post", side_effect=[ok, bad]),
    ):
        result = _stats_nixos("unstable")
    assert "Packages: 1,234" in result
    assert "Options: unavailable" in result
