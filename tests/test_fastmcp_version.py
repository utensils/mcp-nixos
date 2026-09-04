"""Guard the FastMCP / MCP SDK generation the server is built against.

The ``fastmcp>=4.0.0`` floor in pyproject.toml and the Nix packaging in
nix/fastmcp4.nix exist so the server speaks MCP protocol revision 2026-07-28.
The rest of the unit suite passes identically on FastMCP 3 and 4, so without
this check a packaging regression that silently resolved FastMCP 3 would go
unnoticed by ``nix build`` and ``nix flake check``.
"""

from importlib.metadata import version

import mcp.types
import pytest


@pytest.mark.unit
def test_fastmcp_major_version_is_at_least_4() -> None:
    major = int(version("fastmcp").split(".")[0])
    assert major >= 4, f"expected FastMCP >= 4, got {version('fastmcp')}"


@pytest.mark.unit
def test_mcp_sdk_speaks_protocol_2026_07_28() -> None:
    assert mcp.types.LATEST_PROTOCOL_VERSION >= "2026-07-28"
