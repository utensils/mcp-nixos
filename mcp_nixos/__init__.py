"""
MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, Home Manager configuration options, and nix-darwin macOS configuration options.
"""

try:
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("mcp-nixos")
    except PackageNotFoundError:
        # Package is not installed, use a default version
        __version__ = "0.5.1"
except ImportError:
    # Fallback for Python < 3.8
    try:
        import pkg_resources

        __version__ = pkg_resources.get_distribution("mcp-nixos").version
    except Exception:
        __version__ = "0.5.1"
