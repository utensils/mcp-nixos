{
  description = "MCP-NixOS - Model Context Protocol server for NixOS and Home Manager resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    devshell.url = "github:numtide/devshell";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      devshell,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ devshell.overlays.default ];
        };

        pythonVersion = "312";
        python = pkgs."python${pythonVersion}";
        ps = pkgs."python${pythonVersion}Packages";

        # Use a single Python instance with proper library support
        pythonWithLibs = python.buildEnv.override {
          extraLibs = [
            ps.cffi
            ps.wheel
            ps.setuptools
            ps.pip
          ];
          ignoreCollisions = true;
        };

        setupVenvScript = pkgs.writeShellScriptBin "setup-venv" ''
          set -e
          echo "--- Setting up Python virtual environment ---"

          # Check for pyproject.toml or setup.py
          if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ]; then
            echo "Error: Neither pyproject.toml nor setup.py found. Cannot install dependencies."
            exit 1
          fi

          if [ ! -d ".venv" ]; then
            echo "Creating Python virtual environment in ./.venv ..."
            ${pythonWithLibs}/bin/python -m venv .venv
          else
            echo "Virtual environment ./.venv already exists."
          fi

          source .venv/bin/activate

          echo "Upgrading pip, setuptools, wheel in venv..."
          if command -v uv >/dev/null 2>&1; then
            uv pip install --upgrade pip setuptools wheel
          else
            python -m pip install --upgrade pip setuptools wheel
          fi

          echo "Installing dependencies from pyproject.toml..."
          if command -v uv >/dev/null 2>&1; then
            echo "(Using uv)"
            # Install with all optional dependencies for development
            uv pip install ".[dev]"
          else
            echo "(Using pip)"
            python -m pip install ".[dev]"
          fi

          if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
            echo "Installing project in editable mode..."
            if command -v uv >/dev/null 2>&1; then
              uv pip install -e .
            else
              python -m pip install -e .
            fi
          else
             echo "No setup.py or pyproject.toml found, skipping editable install."
          fi

          # List installed packages for verification
          echo "Installed dependencies:"
          pip list | grep -E "requests|fastmcp|beautifulsoup4"

          echo "✓ Python environment setup complete in ./.venv"
          echo "---------------------------------------------"
        '';

        # Setup for Python package - using Python 3.12 which has fastmcp in nixpkgs
        pythonPackage =
          let
            pyproject = nixpkgs.lib.importTOML ./pyproject.toml;
          in
          pkgs.python312Packages.buildPythonApplication {
            pname = pyproject.project.name;
            inherit (pyproject.project) version;
            meta.mainProgram = pyproject.project.name;

            src = ./.;

            format = "pyproject";

            nativeBuildInputs = with pkgs.python312Packages; [
              hatchling
            ];

            propagatedBuildInputs = with pkgs.python312Packages; [
              # Use fastmcp from nixpkgs
              fastmcp
              requests
              beautifulsoup4
            ];

            # Disable runtime dependency checks since the available versions in nixpkgs
            # may not match exactly what's specified in pyproject.toml
            pythonImportsCheck = [ ];
            doCheck = false;
            dontCheckRuntimeDeps = true;
          };

      in
      {
        # Packages
        packages = {
          default = pythonPackage;
          mcp-nixos = pythonPackage;
        };

        # Add apps for direct execution with nix run
        apps = {
          default = flake-utils.lib.mkApp {
            drv = pythonPackage;
            name = "mcp-nixos";
          };
          mcp-nixos = flake-utils.lib.mkApp {
            drv = pythonPackage;
            name = "mcp-nixos";
          };
        };

        # Create a separate shell for website development
        devShells.web = pkgs.devshell.mkShell {
          name = "mcp-nixos-web";
          packages = with pkgs; [
            nodejs_20
          ];
          commands = [
            {
              name = "install";
              category = "website";
              help = "Install website dependencies";
              command = "cd website && npm install";
            }
            {
              name = "dev";
              category = "website";
              help = "Start the development server";
              command = "cd website && npm run dev";
            }
            {
              name = "build";
              category = "website";
              help = "Build the static website for production";
              command = "cd website && npm run build";
            }
            {
              name = "lint";
              category = "website";
              help = "Lint the website code";
              command = "cd website && npm run lint";
            }
          ];
          devshell.startup.initMessage.text = ''
            echo "Entering MCP-NixOS Website Dev Environment..."
            echo ""
            echo "Available commands:"
            echo "  install  - Install dependencies"
            echo "  dev      - Start development server"
            echo "  build    - Build for production"
            echo "  lint     - Lint code"
            echo ""
            menu
          '';
        };

        devShells.default = pkgs.devshell.mkShell {
          name = "mcp-nixos";
          motd = ''
            Entering MCP-NixOS Dev Environment...
            Python: ${python.version}
            Nix:    ${pkgs.nix}/bin/nix --version
          '';
          env = [
            {
              name = "PYTHONPATH";
              value = "$PWD";
            }
            {
              name = "MCP_NIXOS_ENV";
              value = "development";
            }
            {
              name = "LIBFFI_INCLUDE_DIR";
              value = "${pkgs.libffi.dev}/include";
            } # Add .dev
            # Make sure Python can find _ctypes with correct linking flags
            {
              name = "NIX_LDFLAGS";
              value = "-L${pkgs.libffi}/lib -L${pkgs.libffi.out}/lib";
            }
            {
              name = "NIX_CFLAGS_COMPILE";
              value = "-I${pkgs.libffi.dev}/include";
            }
            # For macOS specifically
            {
              name = "DYLD_LIBRARY_PATH";
              value = "${pkgs.libffi}/lib:${pkgs.libffi.out}/lib";
            }
            # Add SDK path for macOS if needed
            {
              name = "SDKROOT";
              value = "${pkgs.darwin.apple_sdk.frameworks.CoreServices}";
            }
          ];
          packages = with pkgs; [
            # Python with build dependencies
            pythonWithLibs
            uv # Faster pip alternative
            ps.build
            ps.twine
            # Required for building C extensions
            libffi
            pkg-config
            # Build tools needed for extension compilation
            binutils
            stdenv.cc.cc

            # Modern linting and formatting tools
            ps.ruff # Replaces black, flake8, isort, and more
            ps.mypy # Type checker
            # Type stubs for dependencies
            ps.types-requests
            ps.types-beautifulsoup4

            # Testing
            ps.pytest
            ps."pytest-cov"
            ps."pytest-asyncio"

            # Nix & Git
            nix
            nixos-option
            git

            # GitHub CLI for repository management
            gh

            # Remove Node.js from main dev shell to avoid conflicts
          ];
          commands = [
            {
              name = "setup";
              category = "environment";
              help = "Set up/update Python virtual environment (.venv) and install dependencies";
              command = "rm -rf .venv && ${setupVenvScript}/bin/setup-venv";
            }
            {
              name = "run";
              category = "server";
              help = "Run the MCP-NixOS server";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi
                if ! python -c "import mcp_nixos" &>/dev/null; then
                   echo "Editable install 'mcp_nixos' not found. Running setup..."
                   ${setupVenvScript}/bin/setup-venv
                   source .venv/bin/activate
                fi
                echo "Starting MCP-NixOS server with enhanced termination handling..."
                # Use the wrapper script for improved signal handling
                python -m mcp_nixos.run
              '';
            }
            {
              name = "run-tests";
              category = "testing";
              help = "Run tests with pytest [--unit|--integration]";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then
                  echo "Activating venv..."
                  source .venv/bin/activate
                fi

                # Verify key dependencies
                echo "Verifying dependencies before running tests..."
                if ! python -c "import requests" &>/dev/null; then
                  echo "ERROR: 'requests' package not found. Installing explicitly..."
                  if command -v uv >/dev/null 2>&1; then
                    uv pip install requests>=2.32.3
                  else
                    python -m pip install requests>=2.32.3
                  fi
                fi

                # Set up parameters based on arguments
                TEST_ARGS=""

                # Handle the unit/integration flags
                # These arguments get passed directly to pytest
                if [[ $# -gt 0 && "$1" == "--unit" ]]; then
                  echo "Running unit tests only..."
                  TEST_ARGS="--unit"
                  shift
                elif [[ $# -gt 0 && "$1" == "--integration" ]]; then
                  echo "Running integration tests only..."
                  TEST_ARGS="--integration"
                  shift
                else
                  echo "Running all tests..."
                  # Set environment variable to indicate all tests are running
                  # This helps certain tests that need to run in isolation skip when run in a full suite
                  export RUNNING_ALL_TESTS=1
                fi

                # Check if running in CI environment
                COVERAGE_ARGS=""
                JUNIT_ARGS=""
                if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
                  # In CI, use coverage and generate JUnit XML for Codecov Test Analytics
                  COVERAGE_ARGS="--cov=mcp_nixos --cov-report=term --cov-report=html --cov-report=xml"
                  JUNIT_ARGS="--junitxml=junit.xml -o junit_family=legacy"
                  echo "Using coverage and JUnit XML (CI environment)"
                fi

                # Run all tests
                if [ -n "$TEST_ARGS" ]; then
                  echo "Running: pytest tests/ -v $TEST_ARGS $COVERAGE_ARGS $JUNIT_ARGS $@"
                  eval "pytest tests/ -v $TEST_ARGS $COVERAGE_ARGS $JUNIT_ARGS $@"
                else
                  echo "Running: pytest tests/ -v $COVERAGE_ARGS $JUNIT_ARGS $@"
                  echo "Note: Running all tests including eval tests. In CI, eval tests are skipped for external contributors."
                  pytest tests/ -v $COVERAGE_ARGS $JUNIT_ARGS "$@"
                fi

                # Show coverage report message if applicable
                if [ -n "$COVERAGE_ARGS" ]; then
                  echo "✅ Coverage report generated. HTML report available in htmlcov/"
                fi
              '';
            }
            {
              name = "loc";
              category = "development";
              help = "Count lines of code in the project";
              command = ''
                echo "=== MCP-NixOS Lines of Code Statistics ==="
                SRC_LINES=$(find ./mcp_nixos -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                TEST_LINES=$(find ./tests -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                # Corrected path pruning for loc command
                CONFIG_LINES=$(find . -path './.venv' -prune -o -path './.mypy_cache' -prune -o -path './htmlcov' -prune -o -path './.direnv' -prune -o -path './result' -prune -o -path './.git' -prune -o -type f \( -name '*.json' -o -name '*.toml' -o -name '*.ini' -o -name '*.yml' -o -name '*.yaml' -o -name '*.nix' -o -name '*.lock' -o -name '*.md' -o -name '*.rules' -o -name '*.hints' -o -name '*.in' \) -print | xargs wc -l | tail -n 1 | awk '{print $1}')
                TOTAL_PYTHON=$((SRC_LINES + TEST_LINES))
                echo "Source code (mcp_nixos directory): $SRC_LINES lines"
                echo "Test code (tests directory): $TEST_LINES lines"
                echo "Configuration files: $CONFIG_LINES lines"
                echo "Total Python code: $TOTAL_PYTHON lines"
                if [ "$SRC_LINES" -gt 0 ]; then
                  RATIO=$(echo "scale=2; $TEST_LINES / $SRC_LINES" | bc)
                  echo "Test to code ratio: $RATIO:1"
                fi
              '';
            }
            {
              name = "lint";
              category = "development";
              help = "Lint code with ruff (checks only in CI)";
              command = ''
                # Check if running in CI environment
                if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
                  echo "--- CI detected: Checking with ruff ---"
                  ruff check mcp_nixos/ tests/
                else
                  echo "--- Linting code with ruff ---"
                  ruff check mcp_nixos/ tests/
                fi
              '';
            }
            {
              name = "typecheck";
              category = "development";
              help = "Run mypy type checker";
              command = ''
                echo "--- Running mypy type checker ---"
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi
                mypy mcp_nixos/
              '';
            }
            {
              name = "check-ruff";
              category = "development";
              help = "Run ruff linter with detailed output";
              command = ''
                echo "--- Running ruff check ---"
                ruff check mcp_nixos/ tests/ --show-fixes
                echo "✅ Ruff check complete"
              '';
            }
            {
              name = "format";
              category = "development";
              help = "Format code with ruff";
              command = ''
                echo "--- Formatting code with ruff ---"
                ruff format mcp_nixos/ tests/
                echo "✅ Code formatted"
              '';
            }
            {
              name = "build";
              category = "distribution";
              help = "Build package distributions (sdist and wheel)";
              command = ''
                 echo "--- Building package ---"
                rm -rf dist/ build/ *.egg-info
                python -m build
                echo "✅ Build complete in dist/"
              '';
            }
            {
              name = "publish";
              category = "distribution";
              help = "Upload package distribution to PyPI (requires ~/.pypirc)";
              command = ''
                 if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then echo "Run 'build' first."; exit 1; fi
                if [ ! -f "$HOME/.pypirc" ]; then echo "Warning: ~/.pypirc not found."; fi
                echo "--- Uploading to PyPI ---"
                twine upload dist/*
                echo "✅ Upload command executed."
              '';
            }
            {
              name = "web-dev";
              category = "website";
              help = "Launch Node.js shell for website development";
              command = ''
                echo "--- Launching Node.js shell for website development ---"
                nix develop .#web
              '';
            }
            {
              name = "complexity";
              category = "development";
              help = "Run wily to analyze code complexity (requires command argument: build|report|graph|rank|diff)";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi

                # Check if wily is installed
                if ! command -v wily >/dev/null 2>&1; then
                  echo "Installing wily..."
                  if command -v uv >/dev/null 2>&1; then
                    uv pip install wily
                  else
                    python -m pip install wily
                  fi
                fi

                # Check if argument is provided
                if [ $# -eq 0 ]; then
                  echo "=== Wily Code Complexity Analysis ==="
                  echo "Error: Missing required command argument"
                  echo ""
                  echo "Usage: complexity <command> [args]"
                  echo ""
                  echo "Commands:"
                  echo "  build         - Build the wily cache (run this first)"
                  echo "  report <file> <metric> - Show metrics for a file"
                  echo "  graph <file> <metric>  - Generate graph visualization"
                  echo "  rank [path] [metric]   - Rank files by complexity"
                  echo "  diff [git_ref]         - Show complexity changes (default: HEAD^1)"
                  echo "  list-metrics  - List available metrics"
                  echo ""
                  echo "Examples:"
                  echo "  complexity build"
                  echo "  complexity report mcp_nixos/server.py mi"
                  echo "  complexity diff origin/main"
                  exit 1
                fi

                # Subcommands
                case "$1" in
                  build)
                    echo "--- Building wily cache ---"
                    wily build mcp_nixos tests
                    ;;
                  report)
                    echo "--- Generating wily report ---"
                    if [ -z "$2" ]; then
                      echo "Usage: complexity report <file_path> <metric>"
                      echo "Available metrics: mi (maintainability index), raw.loc (lines of code), etc."
                      echo "Run 'wily list-metrics' for a complete list"
                      exit 1
                    fi
                    if [ -z "$3" ]; then
                      wily report "$2" "mi"
                    else
                      wily report "$2" "$3"
                    fi
                    ;;
                  graph)
                    echo "--- Generating wily graph ---"
                    if [ -z "$2" ]; then
                      echo "Usage: complexity graph <file_path> <metric>"
                      echo "Available metrics: mi (maintainability index), raw.loc (lines of code), etc."
                      echo "Run 'wily list-metrics' for a complete list"
                      exit 1
                    fi
                    if [ -z "$3" ]; then
                      wily graph "$2" "mi"
                    else
                      wily graph "$2" "$3"
                    fi
                    ;;
                  rank)
                    echo "--- Ranking files by complexity ---"
                    if [ -z "$2" ]; then
                      PATH_ARG="."
                    else
                      PATH_ARG="$2"
                    fi
                    
                    if [ -z "$3" ]; then
                      wily rank "$PATH_ARG" "mi"
                    else
                      wily rank "$PATH_ARG" "$3"
                    fi
                    ;;
                  diff)
                    echo "--- Comparing complexity changes ---"
                    if [ -z "$2" ]; then
                      wily diff mcp_nixos tests -r "HEAD^1"
                    else
                      wily diff mcp_nixos tests -r "$2"
                    fi
                    ;;
                  list-metrics)
                    wily list-metrics
                    ;;
                  *)
                    echo "=== Wily Code Complexity Analysis ==="
                    echo "Error: Missing required command argument"
                    echo ""
                    echo "Usage: complexity <command> [args]"
                    echo ""
                    echo "Commands:"
                    echo "  build         - Build the wily cache (run this first)"
                    echo "  report <file> <metric> - Show metrics for a file"
                    echo "  graph <file> <metric>  - Generate graph visualization"
                    echo "  rank [path] [metric]   - Rank files by complexity"
                    echo "  diff [git_ref]         - Show complexity changes (default: HEAD^1)"
                    echo "  list-metrics  - List available metrics"
                    echo ""
                    echo "Examples:"
                    echo "  complexity build"
                    echo "  complexity report mcp_nixos/server.py mi"
                    echo "  complexity diff origin/main"
                    exit 1
                    ;;
                esac
              '';
            }
          ];
          devshell.startup.venvActivate.text = ''
             echo "Ensuring Python virtual environment is set up..."
            ${setupVenvScript}/bin/setup-venv
            echo "Activating virtual environment..."
            source .venv/bin/activate
            echo ""
            echo "✅ MCP-NixOS Dev Environment Activated."
            echo "   Virtual env ./.venv is active."
            echo ""
            menu
          '';
        };
      }
    );
}
