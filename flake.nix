{
  description = "MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    devshell = {
      url = "github:numtide/devshell";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      flake-parts,
      ...
    }:
    let
      # Python package-set extension that provides fastmcp 4 / mcp 2 on
      # nixpkgs revisions that still ship older releases (see nix/fastmcp4.nix).
      fastmcp4Extension = import ./nix/fastmcp4.nix { inherit (nixpkgs) lib; };

      mkMcpNixos =
        {
          pkgs,
          python3Packages ? pkgs.python3Packages,
        }:
        let
          pyproject = pkgs.lib.importTOML ./pyproject.toml;
          # Scope the fastmcp 4 upgrade to this package so consumers get a
          # working mcp-nixos without having to upgrade `mcp`/`fastmcp` in
          # their whole Python package set. The extension is a no-op when the
          # given set already carries fastmcp >= 4.
          pythonPackages = python3Packages.overrideScope fastmcp4Extension;
        in
        pythonPackages.buildPythonApplication {
          pname = pyproject.project.name;
          inherit (pyproject.project) version;
          pyproject = true;
          src = pkgs.lib.fileset.toSource {
            root = ./.;
            fileset = pkgs.lib.fileset.unions [
              ./pyproject.toml
              ./README.md
              ./LICENSE
              ./RELEASE_NOTES.md
              ./mcp_nixos
              ./tests
            ];
          };

          build-system = [ pythonPackages.hatchling ];
          dependencies = with pythonPackages; [
            fastmcp
            requests
            beautifulsoup4
          ];

          pythonRelaxDeps = true;
          doCheck = true;
          nativeCheckInputs = with pythonPackages; [
            pytest
            pytest-asyncio
            pytest-cov
            pytest-rerunfailures
          ];
          checkPhase = ''
            pytest tests/ -m unit
          '';
          dontCheckRuntimeDeps = true;
          pythonImportsCheck = [ "mcp_nixos" ];

          # Expose the scoped package set so consumers (and the flake's own
          # checks) can inspect the exact fastmcp/mcp the binary runs on.
          passthru = { inherit pythonPackages; };

          meta = {
            inherit (pyproject.project) description;
            homepage = "https://github.com/utensils/mcp-nixos";
            license = pkgs.lib.licenses.mit;
            mainProgram = "mcp-nixos";
          };
        };
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.devshell.flakeModule
      ];

      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];

      flake = {
        # Upgrade the whole Python package set to fastmcp 4 / mcp 2 when the
        # consumer's nixpkgs still ships an older release. Only needed if you
        # want `pkgs.python3Packages.fastmcp` itself to be 4.x; `mcp-nixos`
        # below already builds against a scoped copy of this upgrade. Note
        # that this also replaces `python3Packages.mcp` (1.x -> 2.x, a major
        # API break) set-wide, so other packages depending on `mcp` may break.
        overlays.fastmcp4 = _final: prev: {
          pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [ fastmcp4Extension ];
        };

        # Deprecated alias kept so existing `overlays.fastmcp3` references keep
        # evaluating. It now applies the fastmcp 4 upgrade above, with the
        # same set-wide `mcp` replacement, so warn loudly.
        overlays.fastmcp3 = nixpkgs.lib.warn ''
          mcp-nixos: overlays.fastmcp3 is deprecated. Use overlays.default for
          pkgs.mcp-nixos (self-contained), or overlays.fastmcp4 if you really
          want python3Packages.fastmcp and mcp upgraded set-wide.
        '' self.overlays.fastmcp4;

        # Downstream consumers who apply `mcp-nixos.overlays.default` get
        # `pkgs.mcp-nixos`. It carries its own fastmcp 4 stack, so nothing
        # else in the consumer's Python package set is touched.
        overlays.default = final: _: {
          mcp-nixos = mkMcpNixos { pkgs = final; };
        };

        lib.mkMcpNixos = mkMcpNixos;
      };

      perSystem =
        { system, ... }:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [ self.overlays.fastmcp4 ];
          };

          # One unified Python environment with app runtime deps, dev tools,
          # and type stubs all sharing a single site-packages. Without this,
          # each `python3Packages.*` is its own isolated env so `mypy` can't
          # see `types-requests` and `python -m build` fails with "No module
          # named build" — which is how the old mkShell + inputsFrom setup
          # silently passed: the propagated env leaked in. numtide/devshell
          # is stricter, so we build the env explicitly.
          pythonEnv = pkgs.python3.withPackages (
            ps: with ps; [
              # app runtime
              fastmcp
              requests
              beautifulsoup4
              # build
              hatchling
              build
              twine
              # lint / type-check
              ruff
              mypy
              types-requests
              types-beautifulsoup4
              # test
              pytest
              pytest-asyncio
              pytest-cov
              pytest-rerunfailures
              pytest-xdist
            ]
          );

          # Shared docs/website commands — available in both the default and
          # `web` devshells so you can pick the right weight class (full Python
          # + docs vs docs-only).
          docsCommands = [
            {
              category = "docs";
              name = "docs-install";
              help = "install VitePress + theme deps (first-time setup)";
              command = "cd \"$PRJ_ROOT/website\" && npm install \"$@\"";
            }
            {
              category = "docs";
              name = "docs-dev";
              help = "VitePress dev server with hot reload (auto-increments port if 5173 is taken)";
              command = ''
                cd "$PRJ_ROOT/website"
                [ -d node_modules ] || npm install
                npm run dev -- "$@"
              '';
            }
            {
              category = "docs";
              name = "docs-build";
              help = "build the documentation site into website/out/";
              command = ''
                cd "$PRJ_ROOT/website"
                [ -d node_modules ] || npm install
                npm run build
              '';
            }
            {
              category = "docs";
              name = "docs-preview";
              help = "serve the built docs site (auto-increments port if 4173 is taken)";
              command = "cd \"$PRJ_ROOT/website\" && npm run preview -- \"$@\"";
            }
            {
              category = "docs";
              name = "docs-check";
              help = "type-check Vue components with vue-tsc";
              command = "cd \"$PRJ_ROOT/website\" && npm run check -- \"$@\"";
            }
            {
              category = "docs";
              name = "docs-clean";
              help = "remove VitePress build + cache artifacts";
              command = "rm -rf \"$PRJ_ROOT/website/.vitepress/cache\" \"$PRJ_ROOT/website/.vitepress/dist\" \"$PRJ_ROOT/website/out\"";
            }
          ];
        in
        {
          # Guards nix/fastmcp4.nix: fail loudly if the package this flake builds,
          # the overlay-applied package set, or the consumer path (a vanilla
          # nixpkgs with only `overlays.default`) fell back to fastmcp < 4 or to a
          # starlette below the CVE-2026-48710 floor. The consumer path is what
          # downstream flakes get, and `packages.mcp-nixos` above cannot cover it
          # because `pkgs` there already carries `overlays.fastmcp4`.
          checks.fastmcp4-overlay =
            let
              inherit (pkgs) lib;
              scoped = self.packages.${system}.mcp-nixos.pythonPackages.fastmcp.version;
              global = pkgs.python3Packages.fastmcp.version;
              bare = import nixpkgs { inherit system; };
              vanilla = import nixpkgs {
                inherit system;
                overlays = [ self.overlays.default ];
              };
              consumer = vanilla.mcp-nixos;
              consumerFastmcp = consumer.pythonPackages.fastmcp.version;
              consumerStarlette = consumer.pythonPackages.starlette.version;
              ok = v: lib.versionAtLeast v "4";
            in
            assert lib.assertMsg (ok scoped) "mcp-nixos builds against fastmcp ${scoped}, expected >= 4";
            assert lib.assertMsg (ok global) "overlays.fastmcp4 yielded fastmcp ${global}, expected >= 4";
            assert lib.assertMsg (ok consumerFastmcp)
              "overlays.default builds mcp-nixos against fastmcp ${consumerFastmcp}, expected >= 4";
            assert lib.assertMsg (lib.versionAtLeast consumerStarlette "1.0.1")
              "overlays.default builds mcp-nixos against starlette ${consumerStarlette}, expected >= 1.0.1";
            assert lib.assertMsg (
              vanilla.python3Packages.fastmcp.drvPath == bare.python3Packages.fastmcp.drvPath
            ) "overlays.default must not replace python3Packages.fastmcp in the consumer's package set";
            pkgs.runCommand "fastmcp4-overlay-check" { inherit consumer; } ''
              echo "fastmcp ${scoped} (scoped), ${global} (overlay), ${consumerFastmcp} (consumer via $consumer)" > $out
              echo "starlette ${consumerStarlette} (consumer)" >> $out
            '';

          packages = rec {
            mcp-nixos = mkMcpNixos { inherit pkgs; };
            default = mcp-nixos;

            docker = pkgs.dockerTools.buildLayeredImage {
              name = "ghcr.io/utensils/mcp-nixos";
              tag = mcp-nixos.version;
              # Format: YYYYMMDDHHMMSS -> YYYY-MM-DDTHH:MM:SSZ
              created =
                let
                  d = self.lastModifiedDate;
                in
                "${builtins.substring 0 4 d}-${builtins.substring 4 2 d}-${builtins.substring 6 2 d}T${builtins.substring 8 2 d}:${builtins.substring 10 2 d}:${builtins.substring 12 2 d}Z";
              contents = [
                mcp-nixos
                pkgs.cacert
              ];
              config = {
                Entrypoint = [ (pkgs.lib.getExe mcp-nixos) ];
                Env = [
                  "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
                ];
              };
            };
          };

          apps = rec {
            mcp-nixos = {
              type = "app";
              program = pkgs.lib.getExe self.packages.${system}.mcp-nixos;
              meta.description = "MCP server for NixOS, Home Manager, and nix-darwin";
            };
            default = mcp-nixos;
          };

          formatter = pkgs.nixfmt-rfc-style;

          # Default dev shell — Python backend + docs tooling in one place.
          # Enter with: `nix develop`
          devshells.default = {
            name = "mcp-nixos";

            motd = ''
              {202}mcp-nixos{reset} — Model Context Protocol server for NixOS ({bold}${system}{reset})
              $(type menu &>/dev/null && menu)
            '';

            packages = [
              pythonEnv
              pkgs.nodejs_20
              pkgs.git
              pkgs.gh
              pkgs.jq
              pkgs.nixfmt-rfc-style
            ];

            commands = [
              # ── server / run ───────────────────────────────────────────────
              {
                category = "run";
                name = "run";
                help = "start the MCP server over STDIO";
                command = "mcp-nixos \"$@\"";
              }
              {
                category = "run";
                name = "run-http";
                help = "start the MCP server over HTTP (http://127.0.0.1:8000/mcp)";
                command = ''
                  MCP_NIXOS_TRANSPORT=http \
                    MCP_NIXOS_HOST="''${MCP_NIXOS_HOST:-127.0.0.1}" \
                    MCP_NIXOS_PORT="''${MCP_NIXOS_PORT:-8000}" \
                    mcp-nixos "$@"
                '';
              }

              # ── checks / tests ─────────────────────────────────────────────
              {
                category = "check";
                name = "run-tests";
                help = "pytest tests/ -n auto (matches CI)";
                command = "cd \"$PRJ_ROOT\" && pytest tests/ -v -n auto --cov=mcp_nixos \"$@\"";
              }
              {
                category = "check";
                name = "test-unit";
                help = "run unit tests only (fast, offline)";
                command = "cd \"$PRJ_ROOT\" && pytest tests/ -m unit \"$@\"";
              }
              {
                category = "check";
                name = "test-integration";
                help = "run integration tests (hits real APIs)";
                command = "cd \"$PRJ_ROOT\" && pytest tests/ -m integration \"$@\"";
              }
              {
                category = "check";
                name = "lint";
                help = "ruff check + format check (matches CI)";
                command = ''
                  cd "$PRJ_ROOT"
                  ruff check mcp_nixos/ tests/
                  ruff format --check mcp_nixos/ tests/
                '';
              }
              {
                category = "check";
                name = "format";
                help = "ruff format mcp_nixos/ tests/";
                command = "cd \"$PRJ_ROOT\" && ruff format mcp_nixos/ tests/";
              }
              {
                category = "check";
                name = "typecheck";
                help = "mypy mcp_nixos/";
                command = "cd \"$PRJ_ROOT\" && mypy mcp_nixos/";
              }
              {
                category = "check";
                name = "ci-local";
                help = "run the same sequence CI runs: lint, typecheck, tests";
                command = ''
                  set -euo pipefail
                  cd "$PRJ_ROOT"
                  ruff check mcp_nixos/ tests/
                  ruff format --check mcp_nixos/ tests/
                  mypy mcp_nixos/
                  pytest tests/ -v -n auto --cov=mcp_nixos
                '';
              }

              # ── build / release ────────────────────────────────────────────
              {
                category = "build";
                name = "build";
                help = "build the Python wheel + sdist into dist/";
                # --no-isolation: use the hatchling pinned by this flake instead of
                # letting `build` fetch the newest one from PyPI. Recent hatchling
                # releases emit Metadata-Version 2.5, which `twine check` — and
                # PyPI's upload API — still reject.
                command = "cd \"$PRJ_ROOT\" && python -m build --no-isolation \"$@\"";
              }
              {
                category = "build";
                name = "build-check";
                help = "twine check — validate package metadata";
                command = "cd \"$PRJ_ROOT\" && twine check dist/*";
              }
              {
                category = "build";
                name = "build-nix";
                help = "nix build — full flake build (matches CI)";
                command = "cd \"$PRJ_ROOT\" && nix build \"$@\"";
              }
              {
                category = "build";
                name = "build-docker";
                help = "nix build .#docker — build the multi-arch Docker image";
                command = "cd \"$PRJ_ROOT\" && nix build .#docker \"$@\"";
              }
            ]
            ++ docsCommands;
          };

          # Lightweight docs-only dev shell — just Node + VitePress helpers.
          # Enter with: `nix develop .#web`
          devshells.web = {
            name = "mcp-nixos-website";

            motd = ''
              {202}mcp-nixos-website{reset} — VitePress docs ({bold}${system}{reset})
              $(type menu &>/dev/null && menu)
            '';

            packages = with pkgs; [
              nodejs_20
              git
              jq
            ];

            commands = docsCommands;
          };
        };
    };
}
