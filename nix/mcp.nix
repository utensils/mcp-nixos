{
  lib,
  buildPythonPackage,
  fetchPypi,
  anyio,
  httpx2,
  jsonschema,
  mcp-types,
  opentelemetry-api,
  pydantic,
  pyjwt,
  python-multipart,
  sse-starlette,
  starlette,
  typing-extensions,
  typing-inspection,
  uvicorn,
}:

buildPythonPackage rec {
  pname = "mcp";
  # mcp pins mcp-types to the exact same version.
  inherit (mcp-types) version;
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-HGwxxdZHHFjbdq86+K9n9G0R0B8KWQd9CjCMvbPT6RU=";
  };

  dependencies = [
    anyio
    httpx2
    jsonschema
    mcp-types
    opentelemetry-api
    pydantic
    pyjwt
    python-multipart
    sse-starlette
    starlette
    typing-extensions
    typing-inspection
    uvicorn
  ]
  ++ pyjwt.optional-dependencies.crypto;

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "mcp" ];
  doCheck = false;

  meta = {
    description = "Official Python SDK for the Model Context Protocol (2.x, spec 2026-07-28)";
    homepage = "https://github.com/modelcontextprotocol/python-sdk";
    license = lib.licenses.mit;
  };
}
