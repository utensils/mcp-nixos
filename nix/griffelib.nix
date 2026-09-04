{
  lib,
  buildPythonPackage,
  fetchPypi,
}:

buildPythonPackage rec {
  pname = "griffelib";
  version = "2.2.0";
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-1xw7wrvtn5WEiGNP54i4Q6n3BdbSg4yjLNbCXutk38Q=";
  };

  pythonImportsCheck = [ "griffe" ];
  doCheck = false;

  meta = {
    description = "Signatures for entire Python programs";
    homepage = "https://github.com/mkdocstrings/griffe";
    license = lib.licenses.isc;
  };
}
