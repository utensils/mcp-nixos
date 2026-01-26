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
            overlays = [
              (final: prev: {
                # fastmcp in nixpkgs has overly strict mcp version bounds
                pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
                  (pyFinal: pyPrev: {
                    fastmcp = pyPrev.fastmcp.overridePythonAttrs (_: {
                      dontCheckRuntimeDeps = true;
                      doCheck = false;
                    });
                  })
                ];
              })
            ];
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
