{
  lib,
  buildPythonPackage,
  fetchPypi,
}:

buildPythonPackage rec {
  pname = "uncalled-for";
  version = "0.4.0";
  format = "wheel";

  src = fetchPypi {
    pname = "uncalled_for";
    inherit version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-FsS7MzdTLkvVVprcGSKFl2861TBUAiVtNMZ6ErXJaL0=";
  };

  pythonImportsCheck = [ "uncalled_for" ];
  doCheck = false;

  meta = {
    description = "Async dependency injection for Python functions";
    homepage = "https://github.com/chrisguidry/uncalled-for";
    license = lib.licenses.mit;
  };
}
