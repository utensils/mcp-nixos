# Python package-set extension that upgrades the MCP stack to FastMCP 4 and
# MCP SDK 2 (protocol revision 2026-07-28) when the consumer's nixpkgs still
# ships an older release. nixpkgs currently packages fastmcp 3.x on top of
# mcp 1.x and has neither mcp-types nor the httpx2/httpcore2 line that mcp 2
# depends on, so the whole stack is provided here from pure-Python wheels.
#
# Wheels are used deliberately: they need no build backend (fastmcp, mcp and
# httpx2 all use uv-dynamic-versioning, whose required version differs across
# nixpkgs channels) and so evaluate and build identically against old and new
# pins. Every package sets `pythonRelaxDeps` so minor version drift in the
# consumer's nixpkgs (starlette, uvicorn, anyio, ...) does not fail the
# runtime dependency check.
#
# The extension is a no-op once nixpkgs itself ships fastmcp >= 4, so it is
# safe to keep applied. See flake.nix for how it is used both scoped (for
# `nix build`) and as the exported `overlays.fastmcp4`.
{ lib }:
pyFinal: pyPrev:
let
  # Attribute *names* of an overlay must not depend on package contents or the
  # package-set fixpoint recurses, so every attribute below is always defined
  # and only its *value* is conditional.
  needsUpgrade = !(pyPrev ? fastmcp) || lib.versionOlder pyPrev.fastmcp.version "4";
  own = name: pyFinal.callPackage (./. + "/${name}.nix") { };
  # Use our definition when upgrading; otherwise keep the consumer's package
  # (falling back to ours if their set lacks it entirely).
  pick = name: if needsUpgrade then own name else (pyPrev.${name} or (own name));
in
{
  mcp-types = pick "mcp-types";
  httpcore2 = pick "httpcore2";
  httpx2 = pick "httpx2";
  mcp = pick "mcp";
  # fastmcp-slim[server] needs griffelib >= 2 and uncalled-for >= 0.4, which
  # stable nixpkgs channels do not carry yet (see issue #135).
  griffelib = pick "griffelib";
  uncalled-for = pick "uncalled-for";
  fastmcp-slim = pick "fastmcp-slim";
  fastmcp = pick "fastmcp";
}
