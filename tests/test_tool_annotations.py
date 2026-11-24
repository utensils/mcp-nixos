"""Verify MCP tool annotations advertised by the server."""

import pytest
from fastmcp import Client
from mcp.types import Tool
from mcp_nixos.server import mcp


@pytest.fixture
async def tools() -> dict[str, Tool]:
    """Return the server's tools keyed by name."""
    async with Client(mcp) as client:
        return {tool.name: tool for tool in await client.list_tools()}


@pytest.mark.unit
@pytest.mark.parametrize("name", ["nix", "nix_versions"])
def test_tool_is_read_only(tools: dict[str, Tool], name: str) -> None:
    annotations = tools[name].annotations
    assert annotations is not None
    assert annotations.read_only_hint is True
