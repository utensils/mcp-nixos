{ pkgs ? import <nixpkgs> { } }:

let
  pythonVersion = "312";
  python = pkgs."python${pythonVersion}";
  ps = pkgs."python${pythonVersion}Packages";
  
  pyproject = pkgs.lib.importTOML ./pyproject.toml;
in
ps.buildPythonApplication {
  pname = pyproject.project.name;
  inherit (pyproject.project) version;
  meta.mainProgram = pyproject.project.name;

  src = ./.;

  format = "pyproject";

  nativeBuildInputs = with ps; [
    hatchling
  ];

  propagatedBuildInputs = with ps; [
    fastmcp
    requests
    beautifulsoup4
  ];

  # Disable runtime dependency checks since the available versions in nixpkgs
  # may not match exactly what's specified in pyproject.toml
  pythonImportsCheck = [ ];
  doCheck = false;
  dontCheckRuntimeDeps = true;
}