"""NixHub API source (binary cache, package metadata)."""

import asyncio
from datetime import datetime
from typing import Any

import requests

from .. import __version__
from ..config import CACHE_NIXOS_ORG, NIXHUB_API
from ..utils import NarInfo, _format_size, _parse_narinfo, error


def _check_system_cache(sys_info: dict[str, str]) -> list[str]:
    """Check binary cache status for a single system (runs in thread pool).

    Returns a list of formatted result lines for this system.
    """
    results: list[str] = []
    sys_name = sys_info.get("system", "unknown")
    store_path = sys_info.get("store_path", "")

    results.append(f"System: {sys_name}")

    if not store_path:
        results.append("  Store path: Not available")
        results.append("  Status: UNKNOWN")
        results.append("")
        return results

    results.append(f"  Store path: {store_path}")

    # Extract hash from store path: /nix/store/{hash}-{name}
    # The hash is the 32-character base32 string after /nix/store/
    try:
        path_parts = store_path.split("/")
        if len(path_parts) >= 4:
            store_hash = path_parts[3].split("-")[0]
        else:
            store_hash = ""
    except (IndexError, AttributeError):
        store_hash = ""

    if not store_hash or len(store_hash) != 32:
        results.append("  Status: UNKNOWN (invalid store path)")
        results.append("")
        return results

    # Check binary cache
    try:
        narinfo_url = f"{CACHE_NIXOS_ORG}/{store_hash}.narinfo"
        cache_resp = requests.head(narinfo_url, timeout=5)

        if cache_resp.status_code == 200:
            # Get full narinfo for size info
            cache_resp = requests.get(narinfo_url, timeout=5)
            if cache_resp.status_code == 200:
                narinfo: NarInfo = _parse_narinfo(cache_resp.text)
                results.append("  Status: CACHED")
                file_size = narinfo.get("file_size")
                if file_size is not None:
                    results.append(f"  Download size: {_format_size(file_size)}")
                nar_size = narinfo.get("nar_size")
                if nar_size is not None:
                    results.append(f"  Unpacked size: {_format_size(nar_size)}")
                compression = narinfo.get("compression")
                if compression:
                    results.append(f"  Compression: {compression}")
            else:
                results.append("  Status: CACHED")
        elif cache_resp.status_code == 404:
            results.append("  Status: NOT CACHED")
        else:
            results.append(f"  Status: UNKNOWN (HTTP {cache_resp.status_code})")
    except requests.RequestException:
        results.append("  Status: UNKNOWN (cache check failed)")

    results.append("")
    return results


def _fetch_nixhub_resolve(name: str, version: str, headers: dict[str, str]) -> tuple[str | None, dict[str, Any] | None]:
    """Fetch package resolution from NixHub API (runs in thread pool).

    Returns (error_message, data) tuple. If error_message is set, data is None.
    The v2/resolve API requires a version parameter (use "latest" as default).
    """
    try:
        url = f"{NIXHUB_API}/v2/resolve"
        # v2/resolve requires version parameter
        params: dict[str, str] = {"name": name, "version": version if version else "latest"}

        resp = requests.get(url, params=params, headers=headers, timeout=15)

        if resp.status_code in (400, 404):
            return error(f"Package '{name}' not found", "NOT_FOUND"), None
        if resp.status_code >= 500:
            return error("NixHub API temporarily unavailable", "SERVICE_ERROR"), None
        resp.raise_for_status()

        return None, resp.json()
    except requests.Timeout:
        return error("NixHub API timed out", "TIMEOUT"), None
    except requests.RequestException as e:
        return error(f"NixHub API error: {e}", "API_ERROR"), None
    except Exception as e:
        return error(str(e)), None


async def _check_binary_cache(name: str, version: str = "latest", system: str = "") -> str:
    """Check binary cache status for a package.

    Uses NixHub resolve API to get store paths, then checks cache.nixos.org.
    All blocking HTTP requests are executed in a thread pool to avoid blocking the event loop.
    Per-system cache checks run concurrently for better performance.
    """
    headers = {"Accept": "application/json", "User-Agent": f"mcp-nixos/{__version__}"}

    # Resolve package to get store paths via NixHub (in thread pool)
    err_msg, data = await asyncio.to_thread(_fetch_nixhub_resolve, name, version or "latest", headers)
    if err_msg is not None:
        return err_msg

    if data is None:
        return error("Invalid response from NixHub", "API_ERROR")

    # Extract package info
    pkg_name = data.get("name", name)
    pkg_version = data.get("version", version)
    systems_data = data.get("systems", {})

    # v2/resolve returns systems as a dict: {"x86_64-linux": {...}, ...}
    # Each system has "outputs" array with store paths
    if not isinstance(systems_data, dict):
        return error("Invalid systems data from NixHub", "API_ERROR")

    # Convert to list of dicts with system name and store_path for _check_system_cache
    systems: list[dict[str, str]] = []
    for sys_name, sys_info in systems_data.items():
        if not isinstance(sys_info, dict):
            continue
        # Get store path from outputs
        outputs = sys_info.get("outputs", [])
        store_path = ""
        if outputs and isinstance(outputs, list):
            # Find default output or use first
            default_output = next((o for o in outputs if o.get("default")), outputs[0] if outputs else None)
            if default_output and isinstance(default_output, dict):
                store_path = default_output.get("path", "")
        systems.append({"system": sys_name, "store_path": store_path})

    if not systems:
        return error(f"No systems found for {name}@{pkg_version}", "NOT_FOUND")

    # Filter by system if specified
    if system:
        systems = [s for s in systems if s.get("system") == system]
        if not systems:
            available = ", ".join(sorted(systems_data.keys()))
            return error(f"System '{system}' not available. Available: {available}", "NOT_FOUND")

    results = [f"Binary Cache Status: {pkg_name}@{pkg_version}", ""]

    # Check cache status for all systems concurrently
    cache_check_tasks = [asyncio.to_thread(_check_system_cache, sys_info) for sys_info in systems]
    system_results = await asyncio.gather(*cache_check_tasks)

    # Combine results in order
    for sys_result in system_results:
        results.extend(sys_result)

    return "\n".join(results).strip()


def _fetch_nixhub_search(query: str) -> tuple[str | None, dict[str, Any] | list[Any] | None]:
    """Fetch NixHub search results synchronously (for use with asyncio.to_thread).

    Returns (error_message, data) tuple. If error_message is set, data is None.
    """
    try:
        url = f"{NIXHUB_API}/v2/search"
        params = {"q": query}
        headers = {"Accept": "application/json", "User-Agent": f"mcp-nixos/{__version__}"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)

        if resp.status_code >= 500:
            return error("NixHub API temporarily unavailable", "SERVICE_ERROR"), None
        resp.raise_for_status()

        return None, resp.json()
    except requests.Timeout:
        return error("NixHub API timed out", "TIMEOUT"), None
    except requests.RequestException as e:
        return error(f"NixHub API error: {e}", "API_ERROR"), None
    except Exception as e:
        return error(str(e)), None


async def _search_nixhub(query: str, limit: int) -> str:
    """Search packages via NixHub API."""
    err, data = await asyncio.to_thread(_fetch_nixhub_search, query)
    if err:
        return err

    try:
        # v2/search returns {"query": "...", "total_results": N, "results": [...]}
        packages = data.get("results", []) if isinstance(data, dict) else data
        if not packages:
            return f"No packages found on NixHub matching '{query}'"

        # Limit results
        packages = packages[:limit]
        total_results = data.get("total_results", len(packages)) if isinstance(data, dict) else len(packages)

        results = [f"Found {len(packages)} of {total_results} packages on NixHub matching '{query}':\n"]
        for pkg in packages:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            summary = pkg.get("summary", "") or pkg.get("description", "")
            last_updated = pkg.get("last_updated", "")

            results.append(f"* {name}")
            if version:
                results.append(f"  Version: {version}")
            if summary:
                summary = summary[:200] + "..." if len(summary) > 200 else summary
                results.append(f"  {summary}")
            if last_updated:
                try:
                    dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    results.append(f"  Updated: {dt.strftime('%Y-%m-%d')}")
                except Exception:
                    pass  # Skip malformed timestamps; omit Updated line rather than failing
            results.append("")

        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _fetch_nixhub_pkg(name: str) -> tuple[str | None, list[Any] | None]:
    """Fetch package data from NixHub v1/pkg API synchronously (for use with asyncio.to_thread).

    Returns (error_message, data) tuple. If error_message is set, data is None.
    """
    try:
        url = f"{NIXHUB_API}/v1/pkg"
        headers = {"Accept": "application/json", "User-Agent": f"mcp-nixos/{__version__}"}
        resp = requests.get(url, params={"name": name}, headers=headers, timeout=15)

        if resp.status_code in (400, 404):
            return error(f"Package '{name}' not found", "NOT_FOUND"), None
        if resp.status_code >= 500:
            return error("NixHub API temporarily unavailable", "SERVICE_ERROR"), None
        resp.raise_for_status()

        return None, resp.json()
    except requests.Timeout:
        return error("NixHub API timed out", "TIMEOUT"), None
    except requests.RequestException as e:
        return error(f"NixHub API error: {e}", "API_ERROR"), None
    except Exception as e:
        return error(str(e)), None


def _fetch_nixhub_resolve_sync(name: str, version: str) -> dict[str, Any] | None:
    """Fetch resolve data from NixHub v2/resolve API synchronously (for use with asyncio.to_thread).

    Returns resolve data or None on error (silently fails).
    """
    try:
        url = f"{NIXHUB_API}/v2/resolve"
        headers = {"Accept": "application/json", "User-Agent": f"mcp-nixos/{__version__}"}
        resp = requests.get(url, params={"name": name, "version": version}, headers=headers, timeout=10)
        if resp.status_code == 200:
            result: dict[str, Any] = resp.json()
            return result
        return None
    except Exception:
        return None


async def _info_nixhub(name: str) -> str:
    """Get detailed package info from NixHub.

    Combines data from v1/pkg (rich metadata) and v2/resolve (flake ref, store paths).
    """
    # Fetch package data via thread pool to avoid blocking event loop
    err, pkg_array = await asyncio.to_thread(_fetch_nixhub_pkg, name)
    if err:
        return err

    try:
        if not pkg_array or not isinstance(pkg_array, list):
            return error(f"Package '{name}' not found", "NOT_FOUND")

        # First element is the latest version
        pkg_data: dict[str, Any] = pkg_array[0]

        # Get flake reference and store paths from v2/resolve
        # v2/resolve requires version parameter and returns systems as a dict
        flake_ref = ""
        store_paths: dict[str, str] = {}
        version: str = pkg_data.get("version", "latest")

        # Fetch resolve data via thread pool (silently fails)
        resolve_data = await asyncio.to_thread(_fetch_nixhub_resolve_sync, name, version)
        if resolve_data:
            # systems is a dict keyed by system name
            systems_data = resolve_data.get("systems", {})
            if isinstance(systems_data, dict):
                for sys_name, sys_info in systems_data.items():
                    # Get flake_installable from first system
                    if not flake_ref:
                        fi = sys_info.get("flake_installable", {})
                        if fi:
                            ref = fi.get("ref", {})
                            attr_path = fi.get("attr_path", "")
                            if ref.get("type") == "github":
                                owner = ref.get("owner", "")
                                repo = ref.get("repo", "")
                                rev = ref.get("rev", "")[:8] if ref.get("rev") else ""
                                if owner and repo:
                                    flake_ref = f"github:{owner}/{repo}/{rev}#{attr_path}"
                    # Get store path from outputs
                    outputs = sys_info.get("outputs", [])
                    if outputs and isinstance(outputs, list):
                        default_output = next((o for o in outputs if o.get("default")), outputs[0] if outputs else None)
                        if default_output:
                            path = default_output.get("path", "")
                            if path:
                                store_paths[sys_name] = path

        # Format output
        results = [f"Package: {pkg_data.get('name', name)}"]

        if version:
            results.append(f"Version: {version}")

        summary = pkg_data.get("summary", "")
        if summary:
            results.append(f"Summary: {summary}")

        description = pkg_data.get("description", "")
        if description and description != summary:
            if len(description) > 500:
                description = description[:500] + "..."
            results.append(f"Description: {description}")

        results.append("")

        # Additional metadata
        license_info = pkg_data.get("license", "")
        if license_info:
            results.append(f"License: {license_info}")

        homepage = pkg_data.get("homepage", "")
        if homepage:
            results.append(f"Homepage: {homepage}")

        # Programs from systems data (v1/pkg has systems dict with programs per system)
        programs: list[str] = []
        systems_dict = pkg_data.get("systems", {})
        if isinstance(systems_dict, dict):
            for sys_info in systems_dict.values():
                if isinstance(sys_info, dict):
                    sys_programs = sys_info.get("programs", [])
                    if sys_programs:
                        programs = sys_programs
                        break  # Programs are same across systems
        if programs:
            progs = programs[:10]  # Limit display
            prog_str = ", ".join(progs)
            if len(programs) > 10:
                prog_str += f" ... ({len(programs)} total)"
            results.append(f"Programs: {prog_str}")

        # Platforms from pkg_data
        platforms = pkg_data.get("platforms", [])
        if platforms:
            results.append(f"Platforms: {', '.join(sorted(platforms))}")

        if flake_ref:
            results.append("")
            results.append("Flake Reference:")
            results.append(f"  {flake_ref}")

        if store_paths:
            results.append("")
            results.append("Store Paths:")
            for sys_name, sys_path in sorted(store_paths.items()):
                results.append(f"  {sys_name}: {sys_path}")

        return "\n".join(results)
    except Exception as e:
        return error(str(e))
