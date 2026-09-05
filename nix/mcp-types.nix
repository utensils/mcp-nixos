{
  lib,
  buildPythonPackage,
  fetchPypi,
  pydantic,
  typing-extensions,
}:

buildPythonPackage rec {
  pname = "mcp-types";
  version = "2.1.1";
  format = "wheel";

  src = fetchPypi {
    pname = "mcp_types";
    inherit version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-Jvn38D8qVzBxeluY4qt+tkCsNS0FoAzcclwxGGR3gpU=";
  };

  dependencies = [
    pydantic
    typing-extensions
  ];

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "mcp_types" ];
  doCheck = false;

  meta = {
    description = "Pydantic models for the Model Context Protocol wire format";
    homepage = "https://github.com/modelcontextprotocol/python-sdk";
    license = lib.licenses.mit;
  };
}
