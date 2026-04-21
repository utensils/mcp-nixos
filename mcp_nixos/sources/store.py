"""Direct /nix/store path inspection for MCP-NixOS server.

Exposes ls/read over an explicit absolute store path. Reuses the same safety
guarantees as `flake_inputs`: paths are resolved and must stay under
`/nix/store/`, and binary files are refused with a size-annotated error.
Unlike `flake_inputs`, no `nix` subprocess is required — files are read
directly from disk.
"""

import asyncio
import os
import stat

from ..config import MAX_FILE_SIZE
from ..utils import (
    _format_size,
    _is_binary_file,
    _read_file_with_limit,
    _validate_store_path,
    error,
)


def _validate_query(query: str) -> tuple[bool, str, str]:
    """Check a user-supplied store path for structural problems.

    The returned path is the stripped input — not canonicalised. Callers that
    need to cross filesystem boundaries safely should rely on
    `_validate_store_path` (which already rejects traversal attempts) rather
    than re-deriving from this value. Returns `(ok, path, error_message)`.
    """
    if not query or not query.strip():
        return False, "", "Store path required (e.g., '/nix/store/<hash>-<name>')"

    path = query.strip()

    if not path.startswith("/"):
        return False, "", f"Absolute store path required, got {query!r}"

    if not _validate_store_path(path):
        return False, "", f"Invalid store path: must stay within /nix/store/, got {query!r}"

    return True, path, ""


def _scan_directory(target_path: str) -> tuple[list[str], list[tuple[str, int | None]]]:
    """Collect (dirs, files-with-sizes) for a directory in one sync pass.

    Raises PermissionError / OSError on listdir failure so the caller can
    distinguish them. Per-entry stat failures fall back to `size=None`.
    """
    entries = os.listdir(target_path)
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
    return dirs, files


async def _store_ls(query: str) -> str:
    """List the contents of a directory inside /nix/store."""
    ok, target_path, err_msg = _validate_query(query)
    if not ok:
        return error(err_msg, "INVALID_PATH")

    if not os.path.exists(target_path):
        return error(f"Path not found: {target_path}", "NOT_FOUND")

    if not os.path.isdir(target_path):
        return error(f"Not a directory: {target_path}", "NOT_DIRECTORY")

    # Scan + per-entry stat run in a single worker thread so even large
    # /nix/store directories never block the event loop.
    try:
        dirs, files = await asyncio.to_thread(_scan_directory, target_path)
    except PermissionError:
        return error(f"Permission denied: {target_path}", "PERMISSION_ERROR")
    except OSError as exc:
        return error(f"Cannot list directory: {exc}", "OS_ERROR")

    if not dirs and not files:
        return f"Directory '{target_path}' is empty."

    lines = [f"Contents of {target_path} ({len(dirs)} dirs, {len(files)} files):", ""]

    for name in dirs:
        lines.append(f"  {name}/")

    for name, size in files:
        size_str = f" ({_format_size(size)})" if size is not None else ""
        lines.append(f"  {name}{size_str}")

    return "\n".join(lines)


async def _store_read(query: str, limit: int) -> str:
    """Read a text file inside /nix/store with a line limit."""
    ok, target_path, err_msg = _validate_query(query)
    if not ok:
        return error(err_msg, "INVALID_PATH")

    if not os.path.exists(target_path):
        return error(f"File not found: {target_path}", "NOT_FOUND")

    if os.path.isdir(target_path):
        return error(f"'{target_path}' is a directory. Use type='ls' to list contents.", "IS_DIRECTORY")

    # Catch PermissionError before the broad OSError so permission problems
    # surface cleanly instead of being flattened into OS_ERROR (and to match
    # what _is_binary_file does internally — without this check, an unreadable
    # file would be misreported as BINARY_FILE below).
    try:
        file_size = os.path.getsize(target_path)
    except PermissionError:
        return error(f"Permission denied: {target_path}", "PERMISSION_ERROR")
    except OSError as exc:
        return error(f"Cannot access file: {exc}", "OS_ERROR")

    if not os.access(target_path, os.R_OK):
        return error(f"Permission denied: {target_path}", "PERMISSION_ERROR")

    if file_size > MAX_FILE_SIZE:
        return error(
            f"File too large: {_format_size(file_size)} (max {_format_size(MAX_FILE_SIZE)})",
            "FILE_TOO_LARGE",
        )

    is_binary = await asyncio.to_thread(_is_binary_file, target_path)
    if is_binary:
        return error(
            f"Binary file detected: {target_path} ({_format_size(file_size)})",
            "BINARY_FILE",
        )

    try:
        lines, total_lines = await asyncio.to_thread(_read_file_with_limit, target_path, limit)
    except PermissionError:
        return error(f"Permission denied: {target_path}", "PERMISSION_ERROR")
    except OSError as exc:
        return error(f"Cannot read file: {exc}", "OS_ERROR")

    header = [f"File: {target_path}", f"Size: {_format_size(file_size)}", ""]

    if total_lines > limit:
        header.append(f"(Showing {limit} of {total_lines} lines)")
        header.append("")

    return "\n".join(header + lines)
