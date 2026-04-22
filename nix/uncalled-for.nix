{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  hatch-vcs,
  hatchling,
}:

buildPythonPackage (finalAttrs: {
  pname = "uncalled-for";
  version = "0.3.1";
  pyproject = true;

  __structuredAttrs = true;

  src = fetchFromGitHub {
    owner = "chrisguidry";
    repo = "uncalled-for";
    tag = finalAttrs.version;
    hash = "sha256-+akXLsfto3FNbkpsPPwN1DQmvu3BpTafRbqLmLwtqek=";
  };

  build-system = [
    hatch-vcs
    hatchling
  ];

  pythonImportsCheck = [ "uncalled_for" ];
  doCheck = false;

  meta = {
    description = "Async dependency injection for Python functions";
    homepage = "https://github.com/chrisguidry/uncalled-for";
    license = lib.licenses.mit;
  };
})
