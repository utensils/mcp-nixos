"""
MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, Home Manager configuration options, and nix-darwin macOS configuration options.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-nixos")
except PackageNotFoundError:
    # Package is not installed, use a default version
    __version__ = "1.0.1"
