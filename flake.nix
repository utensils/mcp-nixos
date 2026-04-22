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
      mkMcpNixos =
        {
          pkgs,
          python3Packages ? pkgs.python3Packages,
        }:
        let
          pyproject = pkgs.lib.importTOML ./pyproject.toml;
        in
        python3Packages.buildPythonApplication {
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

          build-system = [ python3Packages.hatchling ];
          dependencies = with python3Packages; [
            fastmcp
            requests
            beautifulsoup4
          ];

          pythonRelaxDeps = true;
          doCheck = true;
          nativeCheckInputs = with python3Packages; [
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
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      flake = {
        # Upgrade fastmcp to 3.2.4 ahead of nixpkgs.
        # Mirrors nixpkgs PR #510339 (PrefectHQ/fastmcp v3.2.4). Can be removed
        # once that PR merges and our flake input moves past it.
        overlays.fastmcp3 = final: prev: {
          pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
            (pyFinal: pyPrev: {
              fastmcp = pyPrev.fastmcp.overridePythonAttrs (old: rec {
                version = "3.2.4";
                src = prev.fetchFromGitHub {
                  owner = "PrefectHQ";
                  repo = "fastmcp";
                  tag = "v${version}";
                  hash = "sha256-rJpxPvqAaa6/vXhG1+R9dI32cY/54e6I+F/zyBVoqBM=";
                };
                # Drop pydocket (moved to optional-dependencies.tasks upstream in
                # nixpkgs PR #510339) and add fastmcp 3's new transitive deps.
                # pydocket's build pulls in lupa → luajit, which fails to link on
                # aarch64-linux (bundled libluajit.a is in the wrong format), and
                # we don't use fastmcp task features.
                #
                # griffelib and uncalled-for are recent additions to nixos-unstable
                # (March 2026) and absent from stable channels. Use upstream if the
                # consumer's nixpkgs has them; otherwise fall back to our inline
                # definitions so `inputs.nixpkgs.follows = "nixpkgs"` works against
                # older pins. See issue #135.
                dependencies = builtins.filter (d: (d.pname or "") != "pydocket") (old.dependencies or [ ]) ++ [
                  (pyFinal.griffelib or (pyFinal.callPackage ./nix/griffelib.nix { }))
                  pyFinal.opentelemetry-api
                  (pyFinal.uncalled-for or (pyFinal.callPackage ./nix/uncalled-for.nix { }))
                  pyFinal.watchfiles
                  pyFinal.pyyaml
                ];
                dontCheckRuntimeDeps = true;
                doCheck = false;
              });
            })
          ];
        };

        # Downstream consumers who apply `mcp-nixos.overlays.default` get both
        # mcp-nixos itself and the fastmcp 3 upgrade needed to satisfy our
        # fastmcp>=3.2.0 dependency against nixpkgs that still ships 2.x.
        overlays.default = nixpkgs.lib.composeExtensions self.overlays.fastmcp3 (
          final: _: {
            mcp-nixos = mkMcpNixos { pkgs = final; };
          }
        );

        lib.mkMcpNixos = mkMcpNixos;
      };

      perSystem =
        { system, ... }:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [ self.overlays.fastmcp3 ];
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
                command = "cd \"$PRJ_ROOT\" && python -m build \"$@\"";
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
