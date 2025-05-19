"""
MCP-NixOS Server - A MCP server for NixOS, Home Manager, and nix-darwin resources.

This implements a comprehensive FastMCP server that provides MCP resources and tools
for querying NixOS packages and options, Home Manager configuration options, and
nix-darwin macOS configuration options using the Model Context Protocol (MCP).
The server communicates via standard input/output streams using a JSON-based
message format, allowing seamless integration with MCP-compatible AI models.

This server provides information about:
- NixOS packages (name, version, description, programs) via Elasticsearch API
- NixOS options (configuration options for the system) via Elasticsearch API
- NixOS service configuration (like services.postgresql.*) via Elasticsearch API
- Home Manager options (user configuration options) via HTML documentation parsing
- nix-darwin options (macOS configuration options) via HTML documentation parsing

Elasticsearch Implementation Notes (NixOS):
-----------------------------------
The server connects to the NixOS search Elasticsearch API with these details:
  - URL: https://search.nixos.org/backend/{index}/_search
  - Credentials: Basic authentication (public credentials from NixOS search)
  - Index pattern: latest-43-nixos-{channel} (e.g., latest-43-nixos-unstable)
  - Both packages and options are in the same index, distinguished by a "type" field
  - Hierarchical paths use a special query format with wildcards

HTML Documentation Parsing (Home Manager and nix-darwin):
-----------------------------------
The server fetches and parses HTML documentation for Home Manager and nix-darwin:
  - Home Manager: Documentation from nix-community.github.io/home-manager/
  - nix-darwin: Documentation from nix-darwin.github.io/nix-darwin/manual/

Based on the official NixOS search implementation with additional parsing for
Home Manager and nix-darwin documentation.
"""

import asyncio
import os
import psutil
import signal
import sys
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_nixos.cache.simple_cache import SimpleCache  # noqa: F401
from mcp_nixos.clients.darwin.darwin_client import DarwinClient  # noqa: F401

# Compatibility imports for tests - these are used by tests
# but unused in the actual server code (suppressed from linting)
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient  # noqa: F401
from mcp_nixos.clients.home_manager_client import HomeManagerClient  # noqa: F401
from mcp_nixos.contexts.darwin.darwin_context import DarwinContext
from mcp_nixos.contexts.home_manager_context import HomeManagerContext
from mcp_nixos.contexts.nixos_context import NixOSContext

# Import our custom modules
from mcp_nixos.logging import setup_logging
from mcp_nixos.resources.darwin.darwin_resources import (  # noqa: F401
    get_darwin_option,
    get_darwin_statistics,
    get_darwin_status,
    register_darwin_resources,
    search_darwin_options,
)
from mcp_nixos.resources.home_manager_resources import (  # noqa: F401
    home_manager_option_resource,
    home_manager_search_options_resource,
    home_manager_stats_resource,
    home_manager_status_resource,
    register_home_manager_resources,
)
from mcp_nixos.resources.nixos_resources import (  # noqa: F401
    nixos_status_resource,
    option_resource,
    package_resource,
    package_stats_resource,
    register_nixos_resources,
    search_options_resource,
    search_packages_resource,
    search_programs_resource,
)
from mcp_nixos.tools.darwin.darwin_tools import register_darwin_tools
from mcp_nixos.tools.discovery_tools import register_discovery_tools
from mcp_nixos.tools.home_manager_tools import register_home_manager_tools
from mcp_nixos.tools.nixos_tools import register_nixos_tools
from mcp_nixos.utils.helpers import create_wildcard_query  # noqa: F401

# Load environment variables from .env file
load_dotenv()

# Import version to add to first log message
from mcp_nixos import __version__

# Initialize logging
logger = setup_logging()
logger.info(f"Starting MCP-NixOS v{__version__}")

# Ensure cache directory is properly initialized before any clients
from mcp_nixos.utils.cache_helpers import init_cache_storage

# Initialize the cache directory explicitly before creating clients
cache_config = init_cache_storage()
logger.info(
    f"Cache initialized with directory: {cache_config['cache_dir']} " f"(initialized: {cache_config['initialized']})"
)
if not cache_config["initialized"]:
    logger.warning(f"Using fallback cache directory due to error: {cache_config.get('error', 'Unknown error')}")

# Initialize the model contexts
nixos_context = NixOSContext()
home_manager_context = HomeManagerContext()
darwin_context = DarwinContext()


# Define a helper function for handling async timeouts
async def async_with_timeout(coro_func, timeout_seconds=5.0, operation_name="operation"):
    """Execute a coroutine with a timeout.

    Args:
        coro_func: A function that returns a coroutine when called
        timeout_seconds: Maximum time to wait (seconds)
        operation_name: Name of the operation for logging purposes

    Returns:
        The result of the coroutine, or None if it timed out
    """
    try:
        # Get the coroutine at execution time, not when passed to the function
        coro = coro_func()
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"{operation_name} timed out after {timeout_seconds}s")
        return None
    except Exception as e:
        logger.error(f"Error during {operation_name}: {e}")
        return None


async def run_precache_async():
    """Run all initialization and cache population, then exit.

    This function runs the same initialization steps as the server startup
    but waits for all caching operations to complete before returning.
    """
    logger.info("Starting pre-cache initialization")

    # Start loading Home Manager data
    logger.info("Loading Home Manager data...")
    home_manager_context.hm_client.load_in_background()

    # Start loading Darwin data
    logger.info("Loading Darwin data...")
    try:
        await async_with_timeout(
            lambda: darwin_context.startup(), timeout_seconds=30.0, operation_name="Darwin context startup"
        )
        logger.info(f"Darwin context status: {darwin_context.status}")
    except Exception as e:
        logger.error(f"Error starting Darwin context: {e}")

    # Wait for Home Manager client to complete loading
    # Use a polling approach since there's no explicit wait_for_loading method
    logger.info("Waiting for Home Manager data to complete loading...")
    max_wait_seconds = 120
    wait_interval = 2
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        with home_manager_context.hm_client.loading_lock:
            if hasattr(home_manager_context.hm_client, "is_loaded") and home_manager_context.hm_client.is_loaded:
                logger.info("Home Manager data finished loading")
                break
            if (
                hasattr(home_manager_context.hm_client, "loading_error")
                and home_manager_context.hm_client.loading_error
            ):
                logger.error(f"Home Manager loading failed: {home_manager_context.hm_client.loading_error}")
                break
        logger.debug(f"Home Manager data still loading, waiting {wait_interval}s...")
        await asyncio.sleep(wait_interval)
    else:
        logger.warning(f"Timed out after {max_wait_seconds}s waiting for Home Manager data to load")

    logger.info("All initialization completed successfully")
    return True


def run_precache():
    """Run all initialization and cache population synchronously, then exit."""
    try:
        return asyncio.run(run_precache_async())
    except KeyboardInterrupt:
        logger.info("Pre-cache operation interrupted")
        return False
    except Exception as e:
        logger.error(f"Error during pre-cache: {e}", exc_info=True)
        return False


# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing MCP-NixOS server components")

    # Import state persistence
    from mcp_nixos.utils.state_persistence import get_state_persistence

    # Create state tracking with initial value
    state_persistence = get_state_persistence()
    state_persistence.load_state()

    # Track connection count across reconnections
    connection_count = state_persistence.increment_counter("connection_count")
    logger.info(f"This is connection #{connection_count} since server installation")

    # Create synchronization for MCP protocol initialization
    protocol_initialized = asyncio.Event()
    app_ready = asyncio.Event()

    # Track initialization state in context
    lifespan_context = {
        "nixos_context": nixos_context,
        "home_manager_context": home_manager_context,
        "darwin_context": darwin_context,
        "is_ready": False,
        "initialization_time": time.time(),
        "connection_count": connection_count,
    }

    # Handle MCP protocol handshake
    # FastMCP doesn't expose a public API for modifying initialize behavior,
    # but it handles the initialize/initialized protocol automatically.
    # We'll use protocol_initialized.set() when we detect the first connection.

    # We'll mark the initialization as complete as soon as app is ready
    logger.info("Setting protocol initialization events")
    protocol_initialized.set()

    # This will trigger waiting for connection
    logger.info("App is ready for requests")
    lifespan_context["is_ready"] = True

    # Start loading Home Manager data in background thread
    # This way the server can start up immediately without blocking
    logger.info("Starting background loading of Home Manager data...")

    # Trigger the background loading process
    home_manager_context.hm_client.load_in_background()

    # Start loading Darwin data in the background
    logger.info("Starting background loading of Darwin data...")

    # Start the Darwin context with a timeout
    try:
        await async_with_timeout(
            lambda: darwin_context.startup(), timeout_seconds=10.0, operation_name="Darwin context startup"
        )
        logger.info(f"Darwin context status: {darwin_context.status}")
    except Exception as e:
        logger.error(f"Error starting Darwin context: {e}")

    # Don't wait for the data to be fully loaded
    logger.info("Server will continue startup while Home Manager and Darwin data loads in background")

    # Mark app as ready for requests
    logger.info("App is ready for requests, waiting for MCP protocol initialization")
    app_ready.set()

    # Wait for MCP protocol initialization (with timeout)
    try:
        await asyncio.wait_for(protocol_initialized.wait(), timeout=5.0)
        logger.info("MCP protocol initialization complete")
        lifespan_context["is_ready"] = True
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for MCP initialize request. Server will proceed anyway.")
        # Still mark as ready to avoid hanging
        lifespan_context["is_ready"] = True

    # Add prompt to guide assistants on using the MCP tools
    @mcp_server.prompt()
    def mcp_nixos_prompt():
        return """
    # NixOS Configuration Assistant

    You have access to MCP tools for querying and understanding NixOS, Home Manager, and Darwin configurations.

    ## Core Principles

    1. **Always Verify**: Before generating any configuration, verify that options exist
    2. **Context Matters**: Use the appropriate tool based on the query (NixOS for system, Home Manager for user,
       Darwin for macOS)
    3. **Exact Paths**: Configuration options have specific paths - verify them before use
    4. **Latest Info**: Use search tools to get current information, not assumptions

    ## 🛑 MANDATORY TOOL USAGE - CRITICAL INSTRUCTION 🛑

    You MUST call the appropriate MCP tools BEFORE answering ANY question related to:
    - NixOS configuration or packages
    - Home Manager configuration
    - nix-darwin configuration

    For ANY configuration request:
    1. You MUST search for available options FIRST using the search tools
    2. You MUST verify each option exists BEFORE including it in a response
    3. You MUST NOT generate ANY configuration based solely on your training
    4. You MUST have evidence from tool results for each configuration option

    If a user asks for a config (like "Create a headscale configuration"), your FIRST action MUST
    be to call the relevant search tools, not to generate a response from memory.

    ## Tool Discovery

    To understand what tools are available and how to use them, call:
    ```
    nixos_stats()    # Get available channels and statistics
    home_manager_stats()    # Home Manager metrics
    darwin_stats()    # Darwin configuration stats
    ```

    Note: All tools require a context parameter that is handled automatically by the MCP framework.

    ## Quick Reference

    - `nixos_*` tools: System-level configuration (services, packages, options)
    - `home_manager_*` tools: User configuration (programs, dotfiles, shell)
    - `darwin_*` tools: macOS system settings (dock, finder, system)

    ## Channel Awareness

    The default NixOS channel is "unstable". For stable release, use either:
    - `channel="stable"` (recommended, automatically maps to current stable)
    - `channel="24.11"` (explicit version reference)
    IMPORTANT: Do NOT use outdated versions like 23.11, 23.05, etc.

    ## Error Handling

    If a tool returns an error or no results:
    1. Check if the option path is correct
    2. Try different search terms or patterns
    3. Suggest alternatives based on tool feedback

    ## Common Scenarios and Tool Selection

    ### For Service Configurations:
    1. First search for available options with search tools
       - Example: `nixos_search("services.headscale", type="options")`
    2. For each key option, verify details with info tools
       - Example: `nixos_info("services.headscale.settings.server_url", type="option")`
    3. Only after verification, generate example configurations
    4. NEVER assume option existence - validate each option path

    ### For Package Questions:
    1. Always verify availability with package search
       - Example: `nixos_search("headscale", type="packages")`
    2. Check version and description with package info
       - Example: `nixos_info("headscale", type="package")`

    ## Choosing the Right Tools

    - **For system-wide configuration**: Use NixOS tools (`nixos_*`)
      - System packages, services, options
      - Example: `nixos_search("postgresql", type="packages")`

    - **For user environment setup**: Use Home Manager tools (`home_manager_*`)
      - User applications, dotfiles, shell configuration
      - Example: `home_manager_search("programs.git")`

    - **For macOS configuration**: Use Darwin tools (`darwin_*`)
      - macOS-specific settings and services
      - Example: `darwin_search("system.defaults.dock")`

    ## Automatic Tool Triggers - REQUIRED
    For these specific request patterns, you MUST IMMEDIATELY use the indicated tools:
    | When user asks for... | Your FIRST action MUST be... |
    |---|---|
    | "Create a [service] configuration" | `nixos_search("services.[service]", type="options")` |
    | "Configure [service] in NixOS" | `nixos_search("services.[service]", type="options")` |
    | "Is [package] available?" | `nixos_search("[package]", type="packages")` |
    | "Home Manager config for [program]" | `home_manager_search("programs.[program]")` |
    | "Darwin configuration for [service]" | `darwin_search("services.[service]")` |

    Use dynamic discovery to understand available capabilities rather than memorizing every API call.
    """

    try:
        # Save the final state before yielding control to server
        from mcp_nixos.utils.state_persistence import get_state_persistence

        state_persistence = get_state_persistence()
        state_persistence.set_state("last_startup_time", time.time())
        state_persistence.save_state()

        # We yield our contexts that will be accessible in all handlers
        yield lifespan_context
    except Exception as e:
        logger.error(f"Error in server lifespan: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down MCP-NixOS server")

        # Track start time for overall shutdown duration
        shutdown_start = time.time()

        # Save final state before shutdown
        try:
            from mcp_nixos.utils.state_persistence import get_state_persistence

            state_persistence = get_state_persistence()
            state_persistence.set_state("last_shutdown_time", time.time())
            state_persistence.set_state("shutdown_reason", "normal")

            # Calculate uptime if we have an initialization time
            if lifespan_context.get("initialization_time"):
                uptime = time.time() - lifespan_context["initialization_time"]
                state_persistence.set_state("last_uptime", uptime)
                logger.info(f"Server uptime: {uptime:.2f}s")

            # Save state to disk
            state_persistence.save_state()
        except Exception as e:
            logger.error(f"Error saving state during shutdown: {e}")

        # Create coroutines for shutdown operations
        shutdown_coroutines = []

        # Add Darwin context shutdown with timeout
        if hasattr(darwin_context, "shutdown") and callable(darwin_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: darwin_context.shutdown(), timeout_seconds=0.5, operation_name="Darwin context shutdown"
                )
            )

        # Add shutdown for home_manager_context if a shutdown method is available
        if hasattr(home_manager_context, "shutdown") and callable(home_manager_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: home_manager_context.shutdown(),
                    timeout_seconds=0.5,
                    operation_name="Home Manager context shutdown",
                )
            )

        # Add shutdown for nixos_context if a shutdown method is available
        if hasattr(nixos_context, "shutdown") and callable(nixos_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: nixos_context.shutdown(), timeout_seconds=0.5, operation_name="NixOS context shutdown"
                )
            )

        # Execute all shutdown operations truly concurrently
        try:
            # Create individual tasks for each coroutine to ensure they run concurrently
            shutdown_tasks = [asyncio.create_task(coro) for coro in shutdown_coroutines]

            # Wait for all tasks to complete with an overall timeout
            await asyncio.wait_for(
                asyncio.gather(*shutdown_tasks, return_exceptions=True),
                timeout=0.8,  # Overall timeout for all shutdown operations
            )
            logger.debug("All context shutdowns completed")
        except asyncio.TimeoutError:
            logger.warning("Some shutdown operations timed out and were terminated")
            # Record abnormal shutdown in state
            try:
                state_persistence = get_state_persistence()
                state_persistence.set_state("shutdown_reason", "timeout")
                state_persistence.save_state()
            except Exception:
                pass  # Avoid cascading errors
        except Exception as e:
            logger.error(f"Error during concurrent shutdown operations: {e}")
            # Record error in state
            try:
                state_persistence = get_state_persistence()
                state_persistence.set_state("shutdown_reason", f"error: {str(e)}")
                state_persistence.save_state()
            except Exception:
                pass  # Avoid cascading errors

        # Log shutdown duration
        shutdown_duration = time.time() - shutdown_start
        logger.info(f"Shutdown completed in {shutdown_duration:.2f}s")


# Create the MCP server with the lifespan handler
logger.info("Creating FastMCP server instance")
mcp = FastMCP(
    "MCP-NixOS",
    version=__version__,
    description="NixOS Model Context Protocol Server",
    lifespan=app_lifespan,
    capabilities=["resources", "tools"],
)


# Helper functions for context access
def get_nixos_context():
    return nixos_context


def get_home_manager_context():
    return home_manager_context


def get_darwin_context():
    return darwin_context


# Register all resources and tools
register_nixos_resources(mcp, get_nixos_context)
register_home_manager_resources(mcp, get_home_manager_context)
register_darwin_resources(darwin_context, mcp)
register_nixos_tools(mcp)
register_home_manager_tools(mcp)
register_darwin_tools(darwin_context, mcp)
register_discovery_tools(mcp)

# No need to manually add tools here - will be handled by the register_darwin_tools function


# Signal handling is now managed by FastMCP framework via app_lifespan


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        # Log server initialization with additional environment info
        logger.info("Initializing MCP-NixOS server")

        # Log process and environment information for debugging
        try:
            process = psutil.Process()
            # Log basic process info
            logger.info(f"Process info - PID: {process.pid}, Parent PID: {process.ppid()}")

            # Try to get parent process info
            try:
                parent = psutil.Process(process.ppid())
                logger.info(f"Parent process: {parent.name()} (PID: {parent.pid})")
                parent_cmdline = " ".join(parent.cmdline())
                logger.debug(f"Parent command line: {parent_cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.info("Unable to access parent process information")

            # Check if running under Windsurf or other MCP client
            windsurf_detected = False
            for env_var in os.environ:
                if "WINDSURF" in env_var.upper() or "WINDSURFER" in env_var.upper():
                    windsurf_detected = True
                    logger.info(f"Detected Windsurf environment: {env_var}={os.environ[env_var]}")

            if windsurf_detected:
                logger.info("Running under Windsurf - configuring for Windsurf compatibility")

                # Log available signals on this platform
                signal_names = []
                for sig_attr in dir(signal):
                    if sig_attr.startswith("SIG") and not sig_attr.startswith("SIG_"):
                        signal_names.append(sig_attr)
                logger.debug(f"Available signals on this platform: {', '.join(signal_names)}")

        except Exception as e:
            logger.error(f"Error getting process info during startup: {e}")

        logger.info("Starting MCP-NixOS server event loop")
        mcp.run()
    except KeyboardInterrupt:
        # This is normal when Ctrl+C is pressed
        logger.info("Server stopped by keyboard interrupt")
        # Exit cleanly
        sys.exit(0)
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error running server: {e}", exc_info=True)
        # Exit with error code
        sys.exit(1)
