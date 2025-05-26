#!/usr/bin/env python
"""CLI entry point for MCP-NixOS server."""

import sys
from mcp_nixos.server import mcp


def main():
    """Run the MCP-NixOS server."""
    try:
        # Run the server (this is a blocking call)
        mcp.run()
        # If run() completes normally, exit with 0
        sys.exit(0)
    except KeyboardInterrupt:
        # Handle keyboard interrupt for cleaner exit
        sys.exit(0)
    except Exception as e:
        # Log unexpected errors and exit with error code
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
