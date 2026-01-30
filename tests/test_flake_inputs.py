"""Tests for flake-inputs functionality."""

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_nixos.server import (
    _check_nix_available,
    _flake_inputs_list,
    _flake_inputs_ls,
    _flake_inputs_read,
    _flatten_inputs,
    _format_size,
    _get_flake_inputs,
    _is_binary_file,
    _run_nix_command,
    _validate_store_path,
    nix,
)

# Get underlying function from MCP tool wrapper
nix_fn = nix.fn


@pytest.mark.unit
class TestCheckNixAvailable:
    """Test _check_nix_available helper."""

    @patch("mcp_nixos.server.shutil.which")
    def test_nix_available(self, mock_which):
        mock_which.return_value = "/nix/var/nix/profiles/default/bin/nix"
        assert _check_nix_available() is True
        mock_which.assert_called_once_with("nix")

    @patch("mcp_nixos.server.shutil.which")
    def test_nix_not_available(self, mock_which):
        mock_which.return_value = None
        assert _check_nix_available() is False


@pytest.mark.unit
class TestFormatSize:
    """Test _format_size helper."""

    def test_bytes(self):
        assert _format_size(0) == "0 B"
        assert _format_size(512) == "512 B"
        assert _format_size(1023) == "1023 B"

    def test_kilobytes(self):
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1536) == "1.5 KB"
        assert _format_size(1024 * 1023) == "1023.0 KB"

    def test_megabytes(self):
        assert _format_size(1024 * 1024) == "1.0 MB"
        assert _format_size(int(1.5 * 1024 * 1024)) == "1.5 MB"

    def test_gigabytes(self):
        assert _format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert _format_size(int(2.5 * 1024 * 1024 * 1024)) == "2.5 GB"


@pytest.mark.unit
class TestFlattenInputs:
    """Test _flatten_inputs helper."""

    def test_empty_inputs(self):
        data = {"path": "/nix/store/xxx", "inputs": {}}
        result = _flatten_inputs(data)
        assert result == {}

    def test_simple_inputs(self):
        data = {
            "path": "/nix/store/xxx",
            "inputs": {
                "nixpkgs": {"path": "/nix/store/abc-nixpkgs", "inputs": {}},
                "flake-utils": {"path": "/nix/store/def-utils", "inputs": {}},
            },
        }
        result = _flatten_inputs(data)
        assert result == {
            "nixpkgs": "/nix/store/abc-nixpkgs",
            "flake-utils": "/nix/store/def-utils",
        }

    def test_nested_inputs(self):
        data = {
            "path": "/nix/store/xxx",
            "inputs": {
                "flake-parts": {
                    "path": "/nix/store/abc-parts",
                    "inputs": {
                        "nixpkgs-lib": {"path": "/nix/store/def-lib", "inputs": {}},
                    },
                },
            },
        }
        result = _flatten_inputs(data)
        assert result == {
            "flake-parts": "/nix/store/abc-parts",
            "flake-parts.nixpkgs-lib": "/nix/store/def-lib",
        }

    def test_deeply_nested_inputs(self):
        data = {
            "inputs": {
                "a": {
                    "path": "/nix/store/a",
                    "inputs": {
                        "b": {
                            "path": "/nix/store/b",
                            "inputs": {
                                "c": {"path": "/nix/store/c", "inputs": {}},
                            },
                        },
                    },
                },
            },
        }
        result = _flatten_inputs(data)
        assert result == {
            "a": "/nix/store/a",
            "a.b": "/nix/store/b",
            "a.b.c": "/nix/store/c",
        }


@pytest.mark.unit
class TestValidateStorePath:
    """Test _validate_store_path helper."""

    def test_valid_store_path(self):
        # These tests require /nix/store to exist, skip if not
        if not os.path.isdir("/nix/store"):
            pytest.skip("/nix/store not available")
        # Find an actual store path
        store_entries = os.listdir("/nix/store")
        if store_entries:
            path = f"/nix/store/{store_entries[0]}"
            assert _validate_store_path(path) is True

    def test_invalid_path_outside_store(self):
        assert _validate_store_path("/tmp/foo") is False
        assert _validate_store_path("/home/user/.config") is False
        assert _validate_store_path("/etc/passwd") is False

    def test_path_traversal_attempt(self):
        # Even if it starts with /nix/store, path traversal should be caught
        assert _validate_store_path("/nix/store/../etc/passwd") is False


@pytest.mark.unit
class TestIsBinaryFile:
    """Test _is_binary_file helper."""

    def test_text_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, this is a text file.\n")
            f.flush()
            assert _is_binary_file(f.name) is False
            os.unlink(f.name)

    def test_binary_file(self):
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"\x00\x01\x02\x03binary\x00content")
            f.flush()
            assert _is_binary_file(f.name) is True
            os.unlink(f.name)

    def test_nonexistent_file(self):
        # Should return True (assume binary) for files we can't read
        assert _is_binary_file("/nonexistent/file/path") is True


@pytest.mark.unit
class TestRunNixCommand:
    """Test _run_nix_command helper."""

    @pytest.mark.asyncio
    async def test_successful_command(self):
        with patch("mcp_nixos.server.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"output", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            success, stdout, stderr = await _run_nix_command(["--version"])
            assert success is True
            assert stdout == "output"
            assert stderr == ""

    @pytest.mark.asyncio
    async def test_failed_command(self):
        with patch("mcp_nixos.server.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"error message")
            mock_process.returncode = 1
            mock_exec.return_value = mock_process

            success, stdout, stderr = await _run_nix_command(["invalid"])
            assert success is False
            assert stderr == "error message"

    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("mcp_nixos.server.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = TimeoutError()
            mock_process.kill = MagicMock()  # kill() is sync, not async
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            success, stdout, stderr = await _run_nix_command(["flake", "archive"], timeout=1)
            assert success is False
            assert "timed out" in stderr.lower()

    @pytest.mark.asyncio
    async def test_nix_not_found(self):
        with patch("mcp_nixos.server.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError()

            success, stdout, stderr = await _run_nix_command(["--version"])
            assert success is False
            assert "not found" in stderr.lower()


@pytest.mark.unit
class TestGetFlakeInputs:
    """Test _get_flake_inputs helper."""

    @pytest.mark.asyncio
    async def test_not_a_flake_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            success, data, err_msg = await _get_flake_inputs(tmpdir)
            assert success is False
            assert "no flake.nix found" in err_msg.lower()

    @pytest.mark.asyncio
    async def test_successful_flake_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake flake.nix
            flake_path = os.path.join(tmpdir, "flake.nix")
            with open(flake_path, "w") as f:
                f.write("{ }")

            mock_output = json.dumps(
                {
                    "path": "/nix/store/xxx",
                    "inputs": {"nixpkgs": {"path": "/nix/store/abc-nixpkgs", "inputs": {}}},
                }
            )

            with patch("mcp_nixos.server._run_nix_command") as mock_run:
                mock_run.return_value = (True, mock_output, "")
                success, data, err_msg = await _get_flake_inputs(tmpdir)
                assert success is True
                assert data is not None
                assert "inputs" in data


@pytest.mark.unit
class TestFlakeInputsList:
    """Test _flake_inputs_list function."""

    @pytest.mark.asyncio
    async def test_nix_not_available(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=False):
            result = await _flake_inputs_list(".")
            assert "NIX_NOT_FOUND" in result

    @pytest.mark.asyncio
    async def test_not_a_flake(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            with tempfile.TemporaryDirectory() as tmpdir:
                result = await _flake_inputs_list(tmpdir)
                assert "FLAKE_ERROR" in result

    @pytest.mark.asyncio
    async def test_successful_list(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            mock_data = {
                "path": "/nix/store/xxx",
                "inputs": {
                    "nixpkgs": {"path": "/nix/store/abc-nixpkgs", "inputs": {}},
                    "flake-utils": {"path": "/nix/store/def-utils", "inputs": {}},
                },
            }
            with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                result = await _flake_inputs_list(".")
                assert "Flake inputs (2 found)" in result
                assert "nixpkgs" in result
                assert "flake-utils" in result
                assert "/nix/store/abc-nixpkgs" in result


@pytest.mark.unit
class TestFlakeInputsLs:
    """Test _flake_inputs_ls function."""

    @pytest.mark.asyncio
    async def test_nix_not_available(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=False):
            result = await _flake_inputs_ls(".", "nixpkgs")
            assert "NIX_NOT_FOUND" in result

    @pytest.mark.asyncio
    async def test_input_not_found(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            mock_data = {
                "path": "/nix/store/xxx",
                "inputs": {"nixpkgs": {"path": "/nix/store/abc", "inputs": {}}},
            }
            with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                result = await _flake_inputs_ls(".", "nonexistent")
                assert "NOT_FOUND" in result
                assert "nixpkgs" in result  # Should suggest available inputs


@pytest.mark.unit
class TestFlakeInputsRead:
    """Test _flake_inputs_read function."""

    @pytest.mark.asyncio
    async def test_nix_not_available(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=False):
            result = await _flake_inputs_read(".", "nixpkgs:flake.nix", 500)
            assert "NIX_NOT_FOUND" in result

    @pytest.mark.asyncio
    async def test_invalid_format_no_colon(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            result = await _flake_inputs_read(".", "nixpkgs", 500)
            assert "INVALID_FORMAT" in result
            assert "input:path" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_format_empty_path(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            result = await _flake_inputs_read(".", "nixpkgs:", 500)
            assert "INVALID_FORMAT" in result


@pytest.mark.unit
class TestNixToolFlakeInputsRouting:
    """Test nix tool routing for flake-inputs action."""

    @pytest.mark.asyncio
    async def test_invalid_type(self):
        result = await nix_fn(action="flake-inputs", type="invalid")
        assert "Error" in result
        assert "list|ls|read" in result

    @pytest.mark.asyncio
    async def test_ls_requires_query(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, {"inputs": {}}, "")):
                result = await nix_fn(action="flake-inputs", type="ls")
                assert "Error" in result
                assert "Query required" in result

    @pytest.mark.asyncio
    async def test_read_requires_query(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            result = await nix_fn(action="flake-inputs", type="read")
            assert "Error" in result
            assert "Query required" in result

    @pytest.mark.asyncio
    async def test_read_limit_validation(self):
        result = await nix_fn(action="flake-inputs", type="read", query="nixpkgs:file.nix", limit=3000)
        assert "Error" in result
        assert "INVALID_LIMIT" in result or "Limit" in result

    @pytest.mark.asyncio
    async def test_list_default_type(self):
        """Test that default type (packages) routes to list for flake-inputs."""
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            mock_data = {"path": "/nix/store/xxx", "inputs": {}}
            with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                result = await nix_fn(action="flake-inputs")
                assert "No inputs found" in result or "Flake inputs" in result

    @pytest.mark.asyncio
    async def test_source_as_flake_dir(self):
        """Test that non-known source is treated as flake directory."""
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            # When source is not a known source, it should be used as the flake directory
            result = await nix_fn(action="flake-inputs", source="/some/path", type="list")
            # Should fail because /some/path doesn't have flake.nix
            assert "FLAKE_ERROR" in result or "NIX_NOT_FOUND" in result


@pytest.mark.unit
class TestPlainTextOutput:
    """Verify flake-inputs outputs are plain text."""

    @pytest.mark.asyncio
    async def test_list_no_xml(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=True):
            mock_data = {
                "path": "/nix/store/xxx",
                "inputs": {"nixpkgs": {"path": "/nix/store/abc", "inputs": {}}},
            }
            with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                result = await _flake_inputs_list(".")
                assert not result.strip().startswith("<")
                assert "</result>" not in result

    @pytest.mark.asyncio
    async def test_error_no_xml(self):
        with patch("mcp_nixos.server._check_nix_available", return_value=False):
            result = await _flake_inputs_list(".")
            assert not result.strip().startswith("<")
            assert "</error>" not in result


@pytest.mark.unit
class TestBugFixes:
    """Tests for bug fixes identified in peer review."""

    @pytest.mark.asyncio
    async def test_flake_inputs_read_limit_above_100(self):
        """Bug #1: flake-inputs read should accept limits > 100 (up to 2000)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake flake.nix
            with open(os.path.join(tmpdir, "flake.nix"), "w") as f:
                f.write("{}")

            with patch("mcp_nixos.server._check_nix_available", return_value=True):
                mock_data = {
                    "path": "/nix/store/xxx",
                    "inputs": {"test-input": {"path": "/nix/store/abc-input", "inputs": {}}},
                }
                with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                    # Limit of 500 should NOT return "Limit must be 1-100" error
                    result = await nix_fn(
                        action="flake-inputs",
                        type="read",
                        query="test-input:file.txt",
                        source=tmpdir,
                        limit=500,
                    )
                    # Should NOT be rejected with limit error
                    assert "Limit must be 1-100" not in result

    @pytest.mark.asyncio
    async def test_flake_inputs_read_default_limit_is_500(self):
        """Bug #2: flake-inputs read with default limit should use 500, not 20."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake flake.nix
            with open(os.path.join(tmpdir, "flake.nix"), "w") as f:
                f.write("{}")

            with patch("mcp_nixos.server._check_nix_available", return_value=True):
                mock_data = {
                    "path": tmpdir,
                    "inputs": {"test-input": {"path": "/nix/store/abc-input", "inputs": {}}},
                }
                with patch("mcp_nixos.server._get_flake_inputs", return_value=(True, mock_data, "")):
                    with patch("mcp_nixos.server._flake_inputs_read") as mock_read:
                        mock_read.return_value = "file contents"
                        # Call with default limit (20 is the MCP default)
                        await nix_fn(
                            action="flake-inputs",
                            type="read",
                            query="test-input:test.txt",
                            source=tmpdir,
                            limit=20,  # This is the MCP default
                        )
                        # Verify _flake_inputs_read was called with 500 (DEFAULT_LINE_LIMIT)
                        # not 20 (the MCP parameter default)
                        mock_read.assert_called_once()
                        call_args = mock_read.call_args
                        # The third argument is the limit
                        actual_limit = call_args[0][2]
                        assert actual_limit == 500, f"Expected limit 500, got {actual_limit}"

    @pytest.mark.asyncio
    async def test_subprocess_killed_on_timeout(self):
        """Bug #3: subprocess should be killed when timeout occurs."""
        # We test this by verifying the timeout handling cleans up the process
        with patch("mcp_nixos.server.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(side_effect=TimeoutError())
            mock_process.kill = MagicMock()  # kill() is sync, not async
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            success, stdout, stderr = await _run_nix_command(["test"], timeout=1)

            assert success is False
            assert "timed out" in stderr.lower()
            # The process should have been killed
            mock_process.kill.assert_called_once()
            mock_process.wait.assert_called_once()
