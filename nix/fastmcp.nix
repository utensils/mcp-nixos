{
  lib,
  buildPythonPackage,
  fetchPypi,
  fastmcp-slim,
}:

buildPythonPackage rec {
  pname = "fastmcp";
  version = "4.0.2";
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-kHXmSpRjStZglx7RQ3TIe+BvKhapIQKMqHmH5qovO/o=";
  };

  # fastmcp 4 is a thin shim over fastmcp-slim[client,server].
  dependencies = [ fastmcp-slim ] ++ fastmcp-slim.optional-dependencies.server;

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "fastmcp" ];
  doCheck = false;

  meta = {
    description = "Fast, Pythonic way to build MCP servers and clients";
    homepage = "https://github.com/PrefectHQ/fastmcp";
    changelog = "https://github.com/PrefectHQ/fastmcp/releases/tag/v${version}";
    license = lib.licenses.asl20;
  };
}
