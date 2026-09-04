{
  lib,
  buildPythonPackage,
  fetchPypi,
  h11,
  truststore,
}:

buildPythonPackage rec {
  pname = "httpcore2";
  version = "2.12.0";
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-fgQljOAQE9fWFeW5EKOyf6yTfXqVA4In55ZStLo7TOs=";
  };

  dependencies = [
    h11
    truststore
  ];

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "httpcore2" ];
  doCheck = false;

  meta = {
    description = "Minimal HTTP client transport layer (httpcore 2.x line)";
    homepage = "https://github.com/pydantic/httpx2";
    changelog = "https://github.com/pydantic/httpx2/blob/v${version}/src/httpcore2/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
}
