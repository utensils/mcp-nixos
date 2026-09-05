{
  lib,
  buildPythonPackage,
  fetchPypi,
  anyio,
  starlette,
}:

buildPythonPackage rec {
  pname = "sse-starlette";
  version = "3.2.0";
  format = "wheel";

  src = fetchPypi {
    pname = "sse_starlette";
    inherit version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-WHaVS9UZIPws1Ruu5HoIDriKN7W3hOYVq7Cyg/gBzb8=";
  };

  dependencies = [
    anyio
    starlette
  ];

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "sse_starlette" ];
  doCheck = false;

  meta = {
    description = "Server-Sent Events for Starlette and FastAPI";
    homepage = "https://github.com/sysid/sse-starlette";
    changelog = "https://github.com/sysid/sse-starlette/blob/v${version}/CHANGELOG.md";
    license = lib.licenses.bsd3;
  };
}
