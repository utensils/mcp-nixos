# Python package-set extension that provides the FastMCP 4 / MCP SDK 2 stack
# (protocol revision 2026-07-28) on nixpkgs revisions that do not ship it.
# As of September 2026 nixpkgs packages fastmcp 3.x on top of mcp 1.x and has
# no mcp-types at all; older pins (nixos-25.11, and unstable before mid-2026)
# also lack httpx2/httpcore2 and py-key-value-aio, ship a starlette older than
# the 1.0.1 security floor (CVE-2026-48710, replaced together with
# sse-starlette), and stable channels carry
# griffelib/uncalled-for versions below what fastmcp-slim[server] needs.
#
# Every package here is built from its pure-Python wheel. mcp-types,
# fastmcp-slim, httpx2 and httpcore2 build with uv-dynamic-versioning, and
# httpx2/httpcore2 2.12 need a release (>= 0.14) newer than any nixpkgs
# channel ships, so building from source would not evaluate uniformly across
# pins. Each package sets `pythonRelaxDeps` so minor version drift in the
# consumer's nixpkgs (uvicorn, anyio, pydantic, ...) does not fail the
# runtime dependency check; the floors that matter are enforced here instead,
# and tests/test_fastmcp_version.py re-checks them inside the build.
#
# The extension keeps the consumer's package whenever it already satisfies
# the bounds FastMCP 4 needs, so it only replaces what is missing, too old or
# too new, and becomes a no-op once nixpkgs itself ships fastmcp >= 4. See
# flake.nix for how it is used both scoped (for `nix build`) and as the
# exported `overlays.fastmcp4`.
{ lib }:
pyFinal: pyPrev:
let
  own = name: pyFinal.callPackage (./. + "/${name}.nix") { };
  # True when the consumer's set has `name` within [floor, ceiling). A null
  # ceiling means no upper bound. Bounds mirror the wheel METADATA of
  # fastmcp-slim 4.0.2 and mcp 2.1.1.
  satisfies =
    name: floor: ceiling:
    builtins.hasAttr name pyPrev
    && (
      let
        v = (builtins.getAttr name pyPrev).version;
      in
      lib.versionAtLeast v floor && (ceiling == null || lib.versionOlder v ceiling)
    );
  # Attribute *names* of an overlay must not depend on package contents or
  # the package-set fixpoint recurses, so every attribute below is always
  # defined and only its *value* is conditional.
  pick =
    name: floor: ceiling:
    if satisfies name floor ceiling then builtins.getAttr name pyPrev else own name;
  # Packages released in lockstep (mcp pins mcp-types to its exact version,
  # httpx2 and httpcore2 share one tag) are kept or replaced as a pair so a
  # vendored wheel is never combined with the consumer's copy of its twin.
  keepMcp = satisfies "mcp" "2.0.0" "3.0.0" && satisfies "mcp-types" "2.0.0" "3.0.0";
  keepHttpx2 = satisfies "httpx2" "2.5.0" null && satisfies "httpcore2" "2.5.0" null;
  pair = keep: name: if keep then builtins.getAttr name pyPrev else own name;
  # nixpkgs derives fastmcp-slim's version and source from `fastmcp` in the
  # *final* set, so its version cannot be inspected independently: decide
  # both from the consumer's fastmcp and replace them together.
  # starlette and sse-starlette are kept or replaced together, so both must
  # meet their floors (fastmcp-slim: starlette >= 1.0.1; mcp: sse-starlette
  # >= 3.0.0) for the consumer's pair to be kept.
  keepStarlette = satisfies "starlette" "1.0.1" null && satisfies "sse-starlette" "3.0.0" null;
  keepFastmcp = satisfies "fastmcp" "4.0.0" null;
in
{
  mcp-types = pair keepMcp "mcp-types";
  mcp = pair keepMcp "mcp";
  httpcore2 = pair keepHttpx2 "httpcore2";
  httpx2 = pair keepHttpx2 "httpx2";
  # fastmcp-slim[client,server] bounds. Stable channels either lack these
  # attributes entirely (issue #135) or carry versions outside the bounds.
  griffelib = pick "griffelib" "2.0.0" null;
  uncalled-for = pick "uncalled-for" "0.4.0" null;
  py-key-value-aio = pick "py-key-value-aio" "0.4.4" "0.5.0";
  # Security floor from fastmcp-slim (CVE-2026-48710); see nix/starlette.nix.
  # nixpkgs' sse-starlette lists fastapi among its build inputs, and fastapi's
  # test suite does not survive a starlette major bump, so whenever starlette
  # is replaced sse-starlette is vendored with it (mcp needs >= 3.0.0).
  starlette = pair keepStarlette "starlette";
  sse-starlette = pair keepStarlette "sse-starlette";
  fastmcp-slim =
    if keepFastmcp then (pyPrev.fastmcp-slim or (own "fastmcp-slim")) else own "fastmcp-slim";
  fastmcp = if keepFastmcp then pyPrev.fastmcp else own "fastmcp";
}
