"""
Regression tests for issue #144: mcp-nixos must start even when the CWD
contains a non-UTF-8 `.env`.

fastmcp's top-level import eagerly constructs a pydantic-settings `Settings()`
which runs python-dotenv on `.env` in the process CWD. A binary / git-crypt
/ sops-encrypted dotenv file used to take the whole server down with a
UnicodeDecodeError before the MCP handshake ever ran. `mcp_nixos/__init__.py`
sets `FASTMCP_ENV_FILE=os.devnull` as a default to sidestep that path.

These tests spawn fresh subprocesses so we're actually exercising import-time
behavior; importing mcp_nixos in the test runner's already-loaded process
doesn't exercise the crash.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_import_in(cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run `import mcp_nixos.server` in a fresh Python process rooted at `cwd`."""
    full_env = os.environ.copy()
    # Let the subprocess find the in-tree mcp_nixos without install.
    full_env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPO_ROOT), full_env.get("PYTHONPATH", "")]))
    # Strip any inherited FASTMCP_ENV_FILE so the regression tests exercise the
    # *default* path (mcp_nixos/__init__.py's setdefault). If the caller wants
    # to assert the explicit-override behavior, they pass it via `env`.
    full_env.pop("FASTMCP_ENV_FILE", None)
    if env:
        full_env.update(env)

    script = textwrap.dedent(
        """
        import mcp_nixos.server
        print("OK")
        """
    ).strip()

    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_startup_survives_non_utf8_dotenv(tmp_path: Path) -> None:
    """Non-UTF-8 bytes in ./.env must not crash import of mcp_nixos.server."""
    (tmp_path / ".env").write_bytes(b"\x9d\x9e\xff\x00binary garbage\xc3\x28")

    result = _run_import_in(tmp_path)

    assert result.returncode == 0, (
        "mcp_nixos.server failed to import with a non-UTF-8 .env in CWD. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "OK" in result.stdout
    assert "UnicodeDecodeError" not in result.stderr


def test_explicit_fastmcp_env_file_is_preserved(tmp_path: Path) -> None:
    """If the user sets FASTMCP_ENV_FILE explicitly, we must not clobber it."""
    valid_env = tmp_path / "custom.env"
    valid_env.write_text("SOME_FASTMCP_VAR=hello\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import mcp_nixos; print(os.environ['FASTMCP_ENV_FILE'])",
        ],
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT), "FASTMCP_ENV_FILE": str(valid_env)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert result.stdout.strip() == str(valid_env)


def test_default_fastmcp_env_file_points_to_devnull(tmp_path: Path) -> None:
    """Import mcp_nixos with no FASTMCP_ENV_FILE set; it should default to os.devnull."""
    env = {k: v for k, v in os.environ.items() if k != "FASTMCP_ENV_FILE"}
    env["PYTHONPATH"] = str(REPO_ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import mcp_nixos; print(os.environ['FASTMCP_ENV_FILE'])",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"stderr={result.stderr!r}"
    assert result.stdout.strip() == os.devnull
