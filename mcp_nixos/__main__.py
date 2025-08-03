#!/usr/bin/env python
"""CLI entry point for MCP-NixOS server."""

import sys
from mcp_nixos.server import mcp


def main():
    """Run the MCP-NixOS server."""
    # Simply run the server - let FastMCP handle all the details
    mcp.run()


if __name__ == "__main__":
    main()
