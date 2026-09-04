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
  version = "2.12.0";
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
    homepage = "https://github.com/encode/httpx";
    license = lib.licenses.bsd3;
  };
}
