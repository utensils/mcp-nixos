{
  lib,
  buildPythonPackage,
  fetchPypi,
  # core
  mcp-types,
  platformdirs,
  pydantic,
  pydantic-settings,
  python-dotenv,
  rich,
  typing-extensions,
  # client / server extras (fastmcp always installs both)
  authlib,
  cyclopts,
  exceptiongroup,
  griffelib,
  httpx2,
  joserfc,
  jsonref,
  jsonschema-path,
  mcp,
  openapi-pydantic,
  opentelemetry-api,
  packaging,
  py-key-value-aio,
  pyperclip,
  python-multipart,
  pyyaml,
  starlette,
  uncalled-for,
  uvicorn,
  watchfiles,
  websockets,
}:

buildPythonPackage rec {
  pname = "fastmcp-slim";
  version = "4.0.2";
  format = "wheel";

  src = fetchPypi {
    pname = "fastmcp_slim";
    inherit version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-a9W1iFYo9zJj+iJH6h0m5KUUSZpuB57j40DNA6f+Xtg=";
  };

  dependencies = [
    mcp-types
    platformdirs
    pydantic
    pydantic-settings
    python-dotenv
    rich
    typing-extensions
  ]
  ++ pydantic.optional-dependencies.email;

  optional-dependencies =
    let
      mcpExtra = [
        exceptiongroup
        httpx2
        mcp
        opentelemetry-api
        starlette
      ];
      clientExtra = [
        authlib
        py-key-value-aio
      ]
      ++ mcpExtra
      ++ py-key-value-aio.optional-dependencies.filetree
      ++ py-key-value-aio.optional-dependencies.keyring
      ++ py-key-value-aio.optional-dependencies.memory;
    in
    {
      mcp = mcpExtra;
      client = clientExtra;
      server = [
        cyclopts
        griffelib
        joserfc
        jsonref
        jsonschema-path
        openapi-pydantic
        packaging
        pyperclip
        python-multipart
        pyyaml
        uncalled-for
        uvicorn
        watchfiles
        websockets
      ]
      ++ clientExtra;
    };

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "fastmcp" ];
  doCheck = false;

  meta = {
    description = "Dependency-slim FastMCP package";
    homepage = "https://github.com/PrefectHQ/fastmcp/tree/main/fastmcp_slim";
    license = lib.licenses.asl20;
  };
}
