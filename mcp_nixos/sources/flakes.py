"""NixOS flakes search via search.nixos.org."""

from typing import Any

import requests

from ..config import FLAKE_INDEX, NIXOS_API, NIXOS_AUTH
from ..utils import error


def _search_flakes(query: str, limit: int) -> str:
    """Search NixOS flakes by name or description."""
    try:
        flake_index = FLAKE_INDEX
        if query.strip() == "" or query == "*":
            q: dict[str, Any] = {"match_all": {}}
        else:
            q = {
                "bool": {
                    "should": [
                        {"match": {"flake_name": {"query": query, "boost": 3}}},
                        {"match": {"flake_description": {"query": query, "boost": 2}}},
                        {"match": {"package_pname": {"query": query, "boost": 1.5}}},
                        {"match": {"package_description": query}},
                        {"wildcard": {"flake_name": {"value": f"*{query}*", "boost": 2.5}}},
                        {"wildcard": {"package_pname": {"value": f"*{query}*", "boost": 1}}},
                        {"prefix": {"flake_name": {"value": query, "boost": 2}}},
                    ],
                    "minimum_should_match": 1,
                }
            }

        search_query = {"bool": {"filter": [{"term": {"type": "package"}}], "must": [q]}}
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_search",
                json={"query": search_query, "size": limit * 5, "track_total_hits": True},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)
        except requests.HTTPError as e:
            if e.response and e.response.status_code == 404:
                return error("Flake indices not found. Flake search may be temporarily unavailable.")
            raise

        if not hits:
            return f"No flakes found matching '{query}'"

        flakes: dict[str, dict[str, Any]] = {}
        for hit in hits:
            src = hit.get("_source", {})
            flake_name = src.get("flake_name", "").strip()
            package_pname = src.get("package_pname", "")
            resolved = src.get("flake_resolved", {})

            if not flake_name and not package_pname:
                continue

            if isinstance(resolved, dict) and (resolved.get("owner") or resolved.get("repo") or resolved.get("url")):
                owner = resolved.get("owner", "")
                repo = resolved.get("repo", "")
                url = resolved.get("url", "")
                if owner and repo:
                    flake_key = f"{owner}/{repo}"
                    display_name = flake_name or repo or package_pname
                elif url:
                    flake_key = url
                    display_name = flake_name or url.rstrip("/").split("/")[-1].replace(".git", "") or package_pname
                else:
                    flake_key = flake_name or package_pname
                    display_name = flake_key

                if flake_key not in flakes:
                    flakes[flake_key] = {
                        "name": display_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": owner,
                        "repo": repo,
                        "url": url,
                        "type": resolved.get("type", ""),
                        "packages": set(),
                    }
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_key]["packages"].add(attr_name)
            elif flake_name:
                if flake_name not in flakes:
                    flakes[flake_name] = {
                        "name": flake_name,
                        "description": src.get("flake_description") or src.get("package_description", ""),
                        "owner": "",
                        "repo": "",
                        "type": "",
                        "packages": set(),
                    }
                attr_name = src.get("package_attr_name", "")
                if attr_name:
                    flakes[flake_name]["packages"].add(attr_name)

        results = []
        if total > len(flakes):
            results.append(f"Found {total:,} matches ({len(flakes)} unique flakes) for '{query}':\n")
        else:
            results.append(f"Found {len(flakes)} flakes matching '{query}':\n")

        for flake in flakes.values():
            results.append(f"* {flake['name']}")
            if flake.get("owner") and flake.get("repo"):
                results.append(f"  Repository: {flake['owner']}/{flake['repo']}")
            elif flake.get("url"):
                results.append(f"  URL: {flake['url']}")
            if flake.get("description"):
                desc = flake["description"][:200] + "..." if len(flake["description"]) > 200 else flake["description"]
                results.append(f"  {desc}")
            if flake["packages"]:
                packages = sorted(flake["packages"])[:5]
                if len(flake["packages"]) > 5:
                    results.append(f"  Packages: {', '.join(packages)}, ... ({len(flake['packages'])} total)")
                else:
                    results.append(f"  Packages: {', '.join(packages)}")
            results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _stats_flakes() -> str:
    """Get flake ecosystem statistics."""
    try:
        flake_index = FLAKE_INDEX
        try:
            resp = requests.post(
                f"{NIXOS_API}/{flake_index}/_count",
                json={"query": {"term": {"type": "package"}}},
                auth=NIXOS_AUTH,
                timeout=10,
            )
            total_packages = resp.json().get("count", 0)
        except Exception:
            return error("Flake indices not found")

        return f"NixOS Flakes Statistics:\n* Available packages: {total_packages:,}"
    except Exception as e:
        return error(str(e))
