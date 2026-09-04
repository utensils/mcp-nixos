# Python package-set extension that provides the FastMCP 4 / MCP SDK 2 stack
# (protocol revision 2026-07-28) on nixpkgs revisions that do not ship it.
# As of September 2026 nixpkgs packages fastmcp 3.x on top of mcp 1.x and has
# no mcp-types at all; older pins (nixos-25.11, and unstable before mid-2026)
# also lack httpx2/httpcore2 and py-key-value-aio, and stable channels carry
# griffelib/uncalled-for versions below what fastmcp-slim[server] needs.
#
# Every package here is built from its pure-Python wheel. mcp-types,
# fastmcp-slim, httpx2 and httpcore2 build with uv-dynamic-versioning, and
# httpx2/httpcore2 2.12 need a release (>= 0.14) newer than any nixpkgs
# channel ships, so building from source would not evaluate uniformly across
# pins. Each package sets `pythonRelaxDeps` so minor version drift in the
# consumer's nixpkgs (starlette, uvicorn, anyio, ...) does not fail the
# runtime dependency check.
#
# The extension keeps the consumer's package whenever it already satisfies
# the floor FastMCP 4 needs, so it only replaces what is missing or too old
# and becomes a no-op once nixpkgs itself ships fastmcp >= 4. See flake.nix
# for how it is used both scoped (for `nix build`) and as the exported
# `overlays.fastmcp4`.
{ lib }:
pyFinal: pyPrev:
let
  own = name: pyFinal.callPackage (./. + "/${name}.nix") { };
  # Attribute *names* of an overlay must not depend on package contents or
  # the package-set fixpoint recurses, so every attribute below is always
  # defined and only its *value* is conditional.
  pick =
    name: floor:
    if
      builtins.hasAttr name pyPrev && lib.versionAtLeast (builtins.getAttr name pyPrev).version floor
    then
      builtins.getAttr name pyPrev
    else
      own name;
  # nixpkgs derives fastmcp-slim's version and source from `fastmcp` in the
  # *final* set, so its version cannot be inspected independently: decide
  # both from the consumer's fastmcp and replace them together.
  keepFastmcp = (pyPrev ? fastmcp) && lib.versionAtLeast pyPrev.fastmcp.version "4.0.0";
in
{
  mcp-types = pick "mcp-types" "2.0.0";
  httpcore2 = pick "httpcore2" "2.5.0";
  httpx2 = pick "httpx2" "2.5.0";
  mcp = pick "mcp" "2.0.0";
  # fastmcp-slim[client,server] floors. Stable channels either lack these
  # attributes entirely (issue #135) or carry versions below the floor.
  griffelib = pick "griffelib" "2.0.0";
  uncalled-for = pick "uncalled-for" "0.4.0";
  py-key-value-aio = pick "py-key-value-aio" "0.4.4";
  fastmcp-slim =
    if keepFastmcp then (pyPrev.fastmcp-slim or (own "fastmcp-slim")) else own "fastmcp-slim";
  fastmcp = if keepFastmcp then pyPrev.fastmcp else own "fastmcp";
}
