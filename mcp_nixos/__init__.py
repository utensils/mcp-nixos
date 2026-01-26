"""
MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, Home Manager configuration options, and nix-darwin macOS configuration options.
"""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("mcp-nixos")
except PackageNotFoundError:
    # Mirroring flake.nix logic: Use pyproject.toml as the source of truth when not installed
    # (e.g. during tests or local development via nix develop)
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
        __version__ = pyproject["project"]["version"]
