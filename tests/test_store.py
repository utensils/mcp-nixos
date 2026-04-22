"""Tests for direct /nix/store path access (action=store)."""

import os
import tempfile

import pytest
from mcp_nixos.server import (
    _store_ls,
    _store_read,
    nix,
)

# Get underlying function from MCP tool wrapper (see tests/test_flake_inputs.py).
nix_fn = getattr(nix, "fn", nix)


def _pick_real_store_dir() -> str | None:
    """Return an existing /nix/store/<entry> directory, or None if not available."""
    if not os.path.isdir("/nix/store"):
        return None
    for entry in os.listdir("/nix/store"):
        candidate = f"/nix/store/{entry}"
        if os.path.isdir(candidate) and not os.path.islink(candidate):
            return candidate
    return None


def _find_text_file_in_dir(root: str, max_files: int = 200) -> str | None:
    """Find a small text file under `root`, or None if none found quickly."""
    count = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            count += 1
            if count > max_files:
                return None
            path = os.path.join(dirpath, name)
            try:
                if os.path.islink(path):
                    continue
                size = os.path.getsize(path)
                if size == 0 or size > 64 * 1024:
                    continue
                with open(path, "rb") as f:
                    chunk = f.read(4096)
                if b"\x00" in chunk:
                    continue
                # Ensure it decodes as UTF-8-ish
                chunk.decode("utf-8", errors="strict")
                return path
            except (OSError, UnicodeDecodeError):
                continue
    return None


def _find_binary_file_in_dir(root: str, max_files: int = 500) -> str | None:
    """Find a binary file under `root` below `MAX_FILE_SIZE`, or None if none found quickly.

    The size cap matters because `_store_read` rejects files over
    `MAX_FILE_SIZE` with `FILE_TOO_LARGE` before the binary check runs —
    and many /nix/store binaries (compiled libraries, CA bundles, etc.)
    exceed the 1 MB default. Picking one over the cap would short-circuit
    the test on an unrelated error.
    """
    from mcp_nixos.config import MAX_FILE_SIZE

    count = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            count += 1
            if count > max_files:
                return None
            path = os.path.join(dirpath, name)
            try:
                if os.path.islink(path):
                    continue
                size = os.path.getsize(path)
                if size == 0 or size >= MAX_FILE_SIZE:
                    continue
                with open(path, "rb") as f:
                    chunk = f.read(4096)
                if b"\x00" in chunk:
                    return path
            except OSError:
                continue
    return None


@pytest.mark.unit
class TestStoreLsPathValidation:
    """Reject non-store and path-traversal queries before touching the filesystem."""

    @pytest.mark.asyncio
    async def test_empty_query_rejected(self):
        """Empty query rejected."""
        result = await _store_ls("", 500)
        assert "Error" in result
        assert "store path required" in result.lower()

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self):
        """Relative path rejected."""
        result = await _store_ls("nix/store/foo", 500)
        assert "Error" in result
        assert "INVALID_PATH" in result

    @pytest.mark.asyncio
    async def test_non_store_path_rejected(self):
        """Non store path rejected."""
        result = await _store_ls("/tmp", 500)
        assert "Error" in result
        assert "INVALID_PATH" in result
        assert "/nix/store/" in result

    @pytest.mark.asyncio
    async def test_etc_passwd_rejected(self):
        """Etc passwd rejected."""
        result = await _store_ls("/etc/passwd", 500)
        assert "Error" in result
        assert "INVALID_PATH" in result

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self):
        """Path traversal rejected."""
        result = await _store_ls("/nix/store/../etc/passwd", 500)
        assert "Error" in result
        assert "INVALID_PATH" in result


@pytest.mark.unit
class TestStoreLsRealPath:
    """Exercise the happy path against a real /nix/store entry if available."""

    @pytest.mark.asyncio
    async def test_ls_real_store_dir(self):
        """Ls real store dir."""
        store_dir = _pick_real_store_dir()
        if store_dir is None:
            pytest.skip("/nix/store not available or empty")

        result = await _store_ls(store_dir, 500)
        assert "Error" not in result
        assert store_dir in result
        # `_pick_real_store_dir` may pick a valid but empty store output
        # (nixpkgs produces empty directories for some derivations). Accept
        # either the "Contents of ..." header or the empty-directory message.
        assert ("dirs" in result and "files" in result) or "is empty" in result

    @pytest.mark.asyncio
    async def test_ls_honours_limit(self):
        """limit=1 against a real store dir must not dump the full listing."""
        if not os.path.isdir("/nix/store"):
            pytest.skip("/nix/store not available")
        big_dir = None
        for entry in sorted(os.listdir("/nix/store"))[:50]:
            candidate = os.path.join("/nix/store", entry)
            if os.path.isdir(candidate):
                try:
                    if len(os.listdir(candidate)) >= 2:
                        big_dir = candidate
                        break
                except OSError:
                    continue
        if big_dir is None:
            pytest.skip("no /nix/store entry with 2+ children found")

        result = await _store_ls(big_dir, 1)
        assert "Error" not in result
        assert "showing 1 of" in result
        # Exactly one entry line (two-space indent) should follow the header/blank line.
        entry_lines = [ln for ln in result.splitlines() if ln.startswith("  ")]
        assert len(entry_lines) == 1, f"expected one entry line, got {entry_lines}"


@pytest.mark.unit
class TestStoreLsMissing:
    """NOT_FOUND for a validly shaped but non-existent store path."""

    @pytest.mark.asyncio
    async def test_nonexistent_path(self):
        """Nonexistent path."""
        if not os.path.isdir("/nix/store"):
            pytest.skip("/nix/store not available")

        bogus = "/nix/store/0000000000000000000000000000000000000000-does-not-exist"
        result = await _store_ls(bogus, 500)
        assert "Error" in result
        assert "NOT_FOUND" in result


@pytest.mark.unit
class TestStoreReadPathValidation:
    """Same guardrails as _store_ls but for read."""

    @pytest.mark.asyncio
    async def test_empty_query_rejected(self):
        """Empty query rejected."""
        result = await _store_read("", 20)
        assert "Error" in result
        assert "INVALID_PATH" in result

    @pytest.mark.asyncio
    async def test_non_store_path_rejected(self):
        """Non store path rejected."""
        result = await _store_read("/tmp/foo", 20)
        assert "Error" in result
        assert "INVALID_PATH" in result

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self):
        """Path traversal rejected."""
        result = await _store_read("/nix/store/../etc/passwd", 20)
        assert "Error" in result
        assert "INVALID_PATH" in result


@pytest.mark.unit
class TestStoreReadNotFound:
    """read on a missing file returns NOT_FOUND."""

    @pytest.mark.asyncio
    async def test_missing_file(self):
        """Missing file."""
        if not os.path.isdir("/nix/store"):
            pytest.skip("/nix/store not available")

        bogus = "/nix/store/0000000000000000000000000000000000000000-nope/bin/nope"
        result = await _store_read(bogus, 20)
        assert "Error" in result
        assert "NOT_FOUND" in result


@pytest.mark.unit
class TestStoreReadIsDirectory:
    """read on a directory returns IS_DIRECTORY with a helpful hint."""

    @pytest.mark.asyncio
    async def test_directory_target(self):
        """Directory target."""
        store_dir = _pick_real_store_dir()
        if store_dir is None:
            pytest.skip("/nix/store not available or empty")

        result = await _store_read(store_dir, 20)
        assert "Error" in result
        assert "IS_DIRECTORY" in result
        assert "type='ls'" in result


@pytest.mark.unit
class TestStoreReadTextFile:
    """Read a real text file out of /nix/store and confirm formatting + truncation."""

    @pytest.mark.asyncio
    async def test_read_text_file(self):
        """Read text file."""
        store_dir = _pick_real_store_dir()
        if store_dir is None:
            pytest.skip("/nix/store not available or empty")
        text_file = _find_text_file_in_dir(store_dir)
        if text_file is None:
            pytest.skip("no small text file found in first store entry")

        result = await _store_read(text_file, 2000)
        assert "Error" not in result
        assert f"File: {text_file}" in result
        assert "Size:" in result

    @pytest.mark.asyncio
    async def test_read_truncates_with_limit(self):
        # Use a tempfile mounted... no — _validate_store_path requires /nix/store/
        # So instead find a real multi-line text file in /nix/store.
        """Read truncates with limit."""
        store_dir = _pick_real_store_dir()
        if store_dir is None:
            pytest.skip("/nix/store not available or empty")

        # Find a file with at least a few lines
        candidate: str | None = None
        for dirpath, _dirnames, filenames in os.walk(store_dir):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    if os.path.islink(path):
                        continue
                    size = os.path.getsize(path)
                    if size == 0 or size > 64 * 1024:
                        continue
                    with open(path, "rb") as f:
                        chunk = f.read(4096)
                    if b"\x00" in chunk:
                        continue
                    # Needs at least 3 lines for a meaningful truncation test
                    if chunk.count(b"\n") >= 3:
                        candidate = path
                        break
                except OSError:
                    continue
            if candidate is not None:
                break

        if candidate is None:
            pytest.skip("no multi-line text file found in first store entry")

        result = await _store_read(candidate, 1)
        assert "Error" not in result
        assert "Showing 1 of" in result


@pytest.mark.unit
class TestStoreReadBinaryFile:
    """read on a binary file returns a BINARY_FILE error that includes the size."""

    @pytest.mark.asyncio
    async def test_read_binary_file(self):
        """Read binary file."""
        store_dir = _pick_real_store_dir()
        if store_dir is None:
            pytest.skip("/nix/store not available or empty")
        binary_file = _find_binary_file_in_dir(store_dir)
        if binary_file is None:
            pytest.skip("no binary file found in first store entry")

        result = await _store_read(binary_file, 20)
        assert "Error" in result
        assert "BINARY_FILE" in result
        assert binary_file in result
        # Size annotation should be present (bytes/KB/MB/GB)
        assert any(unit in result for unit in (" B)", " KB)", " MB)", " GB)"))


@pytest.mark.unit
class TestStoreRouting:
    """Routing of action=store through the top-level nix() tool."""

    @pytest.mark.asyncio
    async def test_invalid_type(self):
        """Invalid type."""
        result = await nix_fn(
            action="store",
            type="invalid",
            query="/nix/store/0000000000000000000000000000000000000000-x",
        )
        assert "Error" in result
        # Anchor on the specific wording so future error rewrites can't
        # silently satisfy a permissive substring match (e.g. "fails",
        # "thread" happen to contain "ls"/"read").
        assert "Type must be" in result
        assert "ls, read" in result or "ls or read" in result

    @pytest.mark.asyncio
    async def test_missing_query_for_ls(self):
        """Missing query for ls."""
        result = await nix_fn(action="store", type="ls")
        assert "Error" in result
        assert "Query required" in result
        assert "/nix/store/" in result

    @pytest.mark.asyncio
    async def test_missing_query_for_read(self):
        """Missing query for read."""
        result = await nix_fn(action="store", type="read")
        assert "Error" in result
        assert "Query required" in result

    @pytest.mark.asyncio
    async def test_read_limit_validation(self):
        """Read limit validation."""
        result = await nix_fn(
            action="store",
            type="read",
            query="/nix/store/0000000000000000000000000000000000000000-x/file",
            limit=3000,
        )
        assert "Error" in result
        assert "2000" in result

    @pytest.mark.asyncio
    async def test_non_store_path_rejected_through_tool(self):
        """Non store path rejected through tool."""
        result = await nix_fn(action="store", type="ls", query="/tmp")
        assert "Error" in result
        assert "INVALID_PATH" in result


@pytest.mark.unit
class TestStorePlainText:
    """Store output must remain plain text (no JSON/XML leakage)."""

    @pytest.mark.asyncio
    async def test_error_output_is_plain_text(self):
        """Error output is plain text."""
        result = await _store_ls("/tmp", 500)
        # No JSON braces or XML tags in error output
        assert not result.strip().startswith("{")
        assert not result.strip().startswith("<")

    @pytest.mark.asyncio
    async def test_read_error_is_plain_text(self):
        """Read error is plain text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await _store_read(tmpdir, 20)
            assert not result.strip().startswith("{")
            assert not result.strip().startswith("<")
