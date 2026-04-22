{
  description = "MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
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

          devShells.default = pkgs.mkShell {
            inputsFrom = [ self.packages.${system}.mcp-nixos ];
            packages = with pkgs.python3Packages; [
              pkgs.python3
              hatchling
              build
              pytest
              pytest-asyncio
              pytest-cov
              pytest-rerunfailures
              pytest-xdist
              ruff
              mypy
              types-requests
              types-beautifulsoup4
              twine
            ];
          };
        };
    };
}
