"""
MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, Home Manager configuration options, and nix-darwin macOS configuration options.
"""

import os
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# Sidestep an upstream crash: fastmcp's top-level import constructs a
# pydantic-settings `Settings()`, which eagerly reads `.env` from the caller's
# CWD via python-dotenv. A non-UTF-8 `.env` (git-crypt ciphertext, sops-
# encrypted dotenv, any binary blob) takes the whole server down with a
# UnicodeDecodeError *before* the MCP stdio handshake ever runs — the client
# just sees mcp-nixos fail to start. We don't read any FASTMCP_* settings from
# `.env`, so neutralising the lookup is safe. Respect an explicit override.
# See issue #144 and https://github.com/jlowin/fastmcp (fastmcp/__init__.py).
os.environ.setdefault("FASTMCP_ENV_FILE", os.devnull)

try:
    __version__ = version("mcp-nixos")
except PackageNotFoundError:
    # Mirroring flake.nix logic: Use pyproject.toml as the source of truth when not installed
    # (e.g. during tests or local development via nix develop)
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
        __version__ = pyproject["project"]["version"]
