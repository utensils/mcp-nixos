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
  # httpx2 and httpcore2 are released together from one repo and one tag: keep
  # this in sync with nix/httpcore2.nix. Pinned here (rather than inherited) so
  # the hash below can never be paired with a different version.
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
    homepage = "https://github.com/pydantic/httpx2";
    changelog = "https://github.com/pydantic/httpx2/blob/v${version}/src/httpx2/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
}
