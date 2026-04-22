{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  hatchling,
  pdm-backend,
  uv-dynamic-versioning,
}:

buildPythonPackage (finalAttrs: {
  pname = "griffelib";
  version = "2.0.2";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "mkdocstrings";
    repo = "griffe";
    tag = finalAttrs.version;
    hash = "sha256-Fxa9lrBVQ/enVLiU7hUc0d5x9ItI19EGnbxa7MX6Plc=";
  };

  sourceRoot = "${finalAttrs.src.name}/packages/griffelib";

  build-system = [
    hatchling
    pdm-backend
    uv-dynamic-versioning
  ];

  pythonImportsCheck = [ "griffe" ];
  doCheck = false;

  meta = {
    description = "Signatures for entire Python programs";
    homepage = "https://github.com/mkdocstrings/griffe";
    license = lib.licenses.isc;
  };
})
