{
  lib,
  buildPythonPackage,
  fetchPypi,
  beartype,
  typing-extensions,
  # optional-dependencies
  aiofile,
  anyio,
  cachetools,
  keyring,
}:

buildPythonPackage rec {
  pname = "py-key-value-aio";
  version = "0.4.5";
  format = "wheel";

  src = fetchPypi {
    pname = "py_key_value_aio";
    inherit version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-q4Yq28uMclR9HFeCHyLLu3GrhlCQOclvNukU4DNsjdc=";
  };

  dependencies = [
    beartype
    typing-extensions
  ];

  # Only the extras fastmcp-slim[client] asks for.
  optional-dependencies = {
    filetree = [
      aiofile
      anyio
    ];
    keyring = [ keyring ];
    memory = [ cachetools ];
  };

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "key_value.aio" ];
  doCheck = false;

  meta = {
    description = "Async key-value store abstraction with pluggable backends";
    homepage = "https://github.com/strawgate/py-key-value";
    license = lib.licenses.asl20;
  };
}
