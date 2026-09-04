{
  lib,
  buildPythonPackage,
  fetchPypi,
  anyio,
  httpcore2,
  idna,
  truststore,
  typing-extensions,
}:

buildPythonPackage rec {
  pname = "httpx2";
  # httpx2 pins httpcore2 to the exact same version (one repo, one tag).
  inherit (httpcore2) version;
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-zItu7LhmHBRrj4mmDpdFbuCG6Rp4TtMaxFDDqeYT3TY=";
  };

  dependencies = [
    anyio
    httpcore2
    idna
    truststore
    typing-extensions
  ];

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "httpx2" ];
  doCheck = false;

  meta = {
    description = "Next-generation HTTP client for Python (httpx 2.x line)";
    homepage = "https://github.com/pydantic/httpx2";
    changelog = "https://github.com/pydantic/httpx2/blob/v${version}/src/httpx2/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
}
