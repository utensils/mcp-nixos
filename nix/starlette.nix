{
  lib,
  buildPythonPackage,
  fetchPypi,
  anyio,
  typing-extensions,
}:

buildPythonPackage rec {
  pname = "starlette";
  # fastmcp-slim 4 floors starlette at 1.0.1 for CVE-2026-48710 (GHSA-86qp-5c8j-p5mr,
  # malformed Host headers bypassing URL-based checks). nixpkgs pins older than
  # mid-2026 ship 0.4x/0.5x, so vendor the fixed release for them.
  version = "1.0.1";
  format = "wheel";

  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-fA5psu4chIvVRmnZCFABF6PuE95gOiFCflxvwa35jc0=";
  };

  dependencies = [
    anyio
    typing-extensions
  ];

  pythonRelaxDeps = true;
  pythonImportsCheck = [ "starlette" ];
  doCheck = false;

  meta = {
    description = "The little ASGI framework that shines";
    homepage = "https://github.com/Kludex/starlette";
    changelog = "https://github.com/Kludex/starlette/releases/tag/${version}";
    license = lib.licenses.bsd3;
  };
}
