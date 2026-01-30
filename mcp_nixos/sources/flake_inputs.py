"""Flake inputs functionality for MCP-NixOS server."""

import asyncio
import json
import os
import shutil
import stat
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from ..config import MAX_FILE_SIZE
from ..utils import (
    _format_size,
    _is_binary_file,
    _read_file_with_limit,
    _validate_store_path,
    error,
)

if TYPE_CHECKING:
    pass  # Used to avoid circular imports at runtime


def _check_nix_available() -> bool:
    """Check if nix command is available on the system."""
    return shutil.which("nix") is not None


def _get_check_nix_available() -> Callable[[], bool]:
    """Get the _check_nix_available function, allowing for test mocking via server module."""
    # This allows tests to mock at mcp_nixos.server._check_nix_available
    # pylint: disable=import-outside-toplevel
    from .. import server

    return server._check_nix_available


def _get_run_nix_command() -> Callable[..., Coroutine[Any, Any, tuple[bool, str, str]]]:
    """Get the _run_nix_command function, allowing for test mocking via server module."""
    # pylint: disable=import-outside-toplevel
    from .. import server

    return server._run_nix_command


def _get_get_flake_inputs() -> Callable[[str], Coroutine[Any, Any, tuple[bool, dict[str, Any] | None, str]]]:
    """Get the _get_flake_inputs function, allowing for test mocking via server module."""
    # pylint: disable=import-outside-toplevel
    from .. import server

    return server._get_flake_inputs


async def _run_nix_command(args: list[str], cwd: str | None = None, timeout: int = 60) -> tuple[bool, str, str]:
    """Run a nix command asynchronously with timeout.

    Returns (success, stdout, stderr).
    """
    process: asyncio.subprocess.Process | None = None
    try:
        # nix flake commands require experimental features
        full_args = ["nix", "--extra-experimental-features", "nix-command flakes"] + args
        process = await asyncio.create_subprocess_exec(
            *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        return process.returncode == 0, stdout_str, stderr_str
    except TimeoutError:
        # Kill the process and wait for it to terminate
        if process is not None:
            process.kill()
            await process.wait()
        return False, "", "Command timed out"
    except FileNotFoundError:
        return False, "", "nix command not found"
    except Exception as e:
        return False, "", str(e)


async def _get_flake_inputs(flake_dir: str) -> tuple[bool, dict[str, Any] | None, str]:
    """Get flake inputs by running nix flake archive --json.

    Returns (success, inputs_dict, error_message).
    """
    # Verify flake.nix exists
    flake_path = os.path.join(flake_dir, "flake.nix")
    if not os.path.isfile(flake_path):
        return False, None, f"Not a flake directory: {flake_dir} (no flake.nix found)"

    success, stdout, stderr = await _get_run_nix_command()(["flake", "archive", "--json"], cwd=flake_dir)
    if not success:
        # Check for common error patterns
        if "experimental feature" in stderr.lower():
            msg = "Flakes not enabled. Enable with: nix-command flakes experimental features"
            return False, None, msg
        if "does not provide attribute" in stderr:
            return False, None, f"Invalid flake: {stderr.strip()}"
        return False, None, f"Failed to get flake inputs: {stderr.strip()}"

    try:
        data = json.loads(stdout)
        return True, data, ""
    except json.JSONDecodeError as e:
        return False, None, f"Failed to parse flake archive output: {e}"


def _flatten_inputs(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten nested inputs from nix flake archive output.

    Returns dict mapping input names (e.g., 'nixpkgs', 'flake-parts.nixpkgs-lib')
    to their nix store paths.
    """
    result = {}
    inputs = data.get("inputs", {})

    for name, info in inputs.items():
        full_name = f"{prefix}.{name}" if prefix else name
        store_path = info.get("path", "")
        if store_path:
            result[full_name] = store_path
        # Recursively flatten nested inputs
        if "inputs" in info and info["inputs"]:
            nested = _flatten_inputs(info, full_name)
            result.update(nested)

    return result


# =============================================================================
# Flake inputs main implementation functions
# =============================================================================


async def _flake_inputs_list(flake_dir: str) -> str:
    """List all flake inputs with their store paths."""
    if not _get_check_nix_available()():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    success, data, err_msg = await _get_get_flake_inputs()(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)
    if not inputs:
        return "No inputs found for this flake."

    # Get the flake's own path
    flake_path = data.get("path", flake_dir)

    lines = [f"Flake inputs ({len(inputs)} found):", f"Flake path: {flake_path}", ""]

    for name, store_path in sorted(inputs.items()):
        lines.append(f"* {name}")
        lines.append(f"  {store_path}")
        lines.append("")

    return "\n".join(lines).strip()


async def _flake_inputs_ls(flake_dir: str, query: str) -> str:
    """List directory contents within a flake input.

    Query format: 'input_name' or 'input_name:subpath'
    """
    if not _get_check_nix_available()():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    # Parse query: input_name or input_name:path
    if ":" in query:
        input_name, subpath = query.split(":", 1)
        subpath = subpath.lstrip("/")
    else:
        input_name = query
        subpath = ""

    success, data, err_msg = await _get_get_flake_inputs()(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)

    if input_name not in inputs:
        available = ", ".join(sorted(inputs.keys())[:10])
        more = f" ... and {len(inputs) - 10} more" if len(inputs) > 10 else ""
        return error(f"Input '{input_name}' not found. Available: {available}{more}", "NOT_FOUND")

    store_path = inputs[input_name]
    target_path = os.path.join(store_path, subpath) if subpath else store_path

    # Security: validate path stays within /nix/store/
    if not _validate_store_path(target_path):
        return error("Invalid path: must stay within /nix/store/", "SECURITY_ERROR")

    if not os.path.exists(target_path):
        return error(f"Path not found: {subpath or '/'} in {input_name}", "NOT_FOUND")

    if not os.path.isdir(target_path):
        return error(f"Not a directory: {subpath or '/'} in {input_name}", "NOT_DIRECTORY")

    try:
        entries = os.listdir(target_path)
    except PermissionError:
        return error(f"Permission denied: {subpath or '/'}", "PERMISSION_ERROR")
    except OSError as e:
        return error(f"Cannot list directory: {e}", "OS_ERROR")

    if not entries:
        return f"Directory '{subpath or '/'}' in {input_name} is empty."

    # Sort and categorize entries
    dirs: list[str] = []
    files: list[tuple[str, int | None]] = []

    for entry in sorted(entries):
        entry_path = os.path.join(target_path, entry)
        try:
            st = os.stat(entry_path)
            if stat.S_ISDIR(st.st_mode):
                dirs.append(entry)
            else:
                files.append((entry, st.st_size))
        except OSError:
            files.append((entry, None))

    display_path = f"{input_name}:{subpath}" if subpath else input_name
    lines = [f"Contents of {display_path} ({len(dirs)} dirs, {len(files)} files):", ""]

    for name in dirs:
        lines.append(f"  {name}/")

    for name, size in files:
        size_str = f" ({_format_size(size)})" if size is not None else ""
        lines.append(f"  {name}{size_str}")

    return "\n".join(lines)


async def _flake_inputs_read(flake_dir: str, query: str, limit: int) -> str:
    """Read a file from a flake input.

    Query format: 'input_name:path/to/file'
    """
    if not _get_check_nix_available()():
        return error("Nix is not installed or not in PATH", "NIX_NOT_FOUND")

    # Parse query: input_name:path
    if ":" not in query:
        return error("Read requires 'input:path' format (e.g., 'nixpkgs:flake.nix')", "INVALID_FORMAT")

    input_name, file_path = query.split(":", 1)
    file_path = file_path.lstrip("/")

    if not file_path:
        return error("File path required (e.g., 'nixpkgs:flake.nix')", "INVALID_FORMAT")

    success, data, err_msg = await _get_get_flake_inputs()(flake_dir)
    if not success:
        return error(err_msg, "FLAKE_ERROR")

    if data is None:
        return error("No flake data returned", "FLAKE_ERROR")

    inputs = _flatten_inputs(data)

    if input_name not in inputs:
        available = ", ".join(sorted(inputs.keys())[:10])
        more = f" ... and {len(inputs) - 10} more" if len(inputs) > 10 else ""
        return error(f"Input '{input_name}' not found. Available: {available}{more}", "NOT_FOUND")

    store_path = inputs[input_name]
    target_path = os.path.join(store_path, file_path)

    # Security: validate path stays within /nix/store/
    if not _validate_store_path(target_path):
        return error("Invalid path: must stay within /nix/store/", "SECURITY_ERROR")

    if not os.path.exists(target_path):
        return error(f"File not found: {file_path} in {input_name}", "NOT_FOUND")

    if os.path.isdir(target_path):
        return error(f"'{file_path}' is a directory. Use type='ls' to list contents.", "IS_DIRECTORY")

    # Check file size
    try:
        file_size = os.path.getsize(target_path)
    except OSError as e:
        return error(f"Cannot access file: {e}", "OS_ERROR")

    if file_size > MAX_FILE_SIZE:
        return error(f"File too large: {_format_size(file_size)} (max {_format_size(MAX_FILE_SIZE)})", "FILE_TOO_LARGE")

    # Check for binary content (in thread pool to avoid blocking)
    is_binary = await asyncio.to_thread(_is_binary_file, target_path)
    if is_binary:
        return error(f"Binary file detected: {file_path} ({_format_size(file_size)})", "BINARY_FILE")

    # Read file with line limit (in thread pool to avoid blocking)
    try:
        lines, total_lines = await asyncio.to_thread(_read_file_with_limit, target_path, limit)

        header = [f"File: {input_name}:{file_path}", f"Size: {_format_size(file_size)}", ""]

        if total_lines > limit:
            header.append(f"(Showing {limit} of {total_lines} lines)")
            header.append("")

        return "\n".join(header + lines)

    except PermissionError:
        return error(f"Permission denied: {file_path}", "PERMISSION_ERROR")
    except OSError as e:
        return error(f"Cannot read file: {e}", "OS_ERROR")
