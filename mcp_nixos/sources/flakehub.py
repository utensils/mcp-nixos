"""FlakeHub API source (Determinate Systems registry)."""

from datetime import datetime

import requests

from ..config import FLAKEHUB_API, FLAKEHUB_USER_AGENT
from ..utils import error


def _search_flakehub(query: str, limit: int) -> str:
    """Search FlakeHub flakes by name or description."""
    try:
        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}
        resp = requests.get(f"{FLAKEHUB_API}/search", params={"q": query}, headers=headers, timeout=15)
        resp.raise_for_status()
        flakes = resp.json()

        if not flakes:
            return f"No flakes found on FlakeHub matching '{query}'"

        # Limit results
        flakes = flakes[:limit]

        results = [f"Found {len(flakes)} flakes on FlakeHub matching '{query}':\n"]
        for flake in flakes:
            org = flake.get("org", "")
            project = flake.get("project", "")
            desc = flake.get("description", "")
            labels = flake.get("labels", [])

            results.append(f"* {org}/{project}")
            if desc:
                desc = " ".join(desc.split())  # Normalize whitespace
                desc = desc[:200] + "..." if len(desc) > 200 else desc
                results.append(f"  {desc}")
            if labels:
                results.append(f"  Labels: {', '.join(labels[:5])}")
            results.append(f"  https://flakehub.com/flake/{org}/{project}")
            results.append("")

        return "\n".join(results).strip()
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _info_flakehub(name: str) -> str:
    """Get detailed info for a FlakeHub flake (org/project format)."""
    try:
        # Parse org/project format
        if "/" not in name:
            return error("FlakeHub flake name must be in 'org/project' format (e.g., 'NixOS/nixpkgs')")

        parts = name.split("/", 1)
        org, project = parts[0], parts[1]

        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}

        # Get latest version info
        resp = requests.get(f"{FLAKEHUB_API}/version/{org}/{project}/*", headers=headers, timeout=15)
        if resp.status_code == 404:
            return error(f"Flake '{name}' not found on FlakeHub", "NOT_FOUND")
        resp.raise_for_status()
        version_info = resp.json()

        results = [f"FlakeHub Flake: {org}/{project}"]

        desc = version_info.get("description", "")
        if desc:
            results.append(f"Description: {desc}")

        version = version_info.get("simplified_version") or version_info.get("version", "")
        if version:
            results.append(f"Latest Version: {version}")

        revision = version_info.get("revision", "")
        if revision:
            results.append(f"Revision: {revision}")

        commit_count = version_info.get("commit_count")
        if commit_count:
            results.append(f"Commits: {commit_count:,}")

        visibility = version_info.get("visibility", "")
        if visibility:
            results.append(f"Visibility: {visibility}")

        published = version_info.get("published_at", "")
        if published:
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                results.append(f"Published: {dt.strftime('%Y-%m-%d %H:%M UTC')}")
            except Exception:
                pass  # Skip malformed timestamps; omit Published line rather than failing

        mirrored = version_info.get("mirrored")
        if mirrored:
            results.append("Source: Mirrored from GitHub")

        download_url = version_info.get("pretty_download_url") or version_info.get("download_url", "")
        if download_url:
            results.append(f"Download: {download_url}")

        results.append(f"FlakeHub URL: https://flakehub.com/flake/{org}/{project}")

        return "\n".join(results)
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
            return error(f"Flake '{name}' not found on FlakeHub", "NOT_FOUND")
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))


def _stats_flakehub() -> str:
    """Get FlakeHub statistics."""
    try:
        headers = {"Accept": "application/json", "User-Agent": FLAKEHUB_USER_AGENT}

        # Get all flakes to count them
        resp = requests.get(f"{FLAKEHUB_API}/flakes", headers=headers, timeout=15)
        resp.raise_for_status()
        flakes = resp.json()

        total_flakes = len(flakes)

        # Count flakes by organization
        orgs: dict[str, int] = {}
        labels: dict[str, int] = {}
        for flake in flakes:
            org = flake.get("org", "unknown")
            orgs[org] = orgs.get(org, 0) + 1
            for label in flake.get("labels", []):
                labels[label] = labels.get(label, 0) + 1

        top_orgs = sorted(orgs.items(), key=lambda x: x[1], reverse=True)[:5]
        top_labels = sorted(labels.items(), key=lambda x: x[1], reverse=True)[:5]

        results = [
            "FlakeHub Statistics:",
            f"* Total flakes: {total_flakes:,}",
            f"* Organizations: {len(orgs):,}",
            "* Top organizations:",
        ]
        for org, count in top_orgs:
            results.append(f"  - {org}: {count:,} flakes")

        if top_labels:
            results.append("* Top labels:")
            for label, count in top_labels:
                results.append(f"  - {label}: {count:,} flakes")

        results.append("\nFlakeHub URL: https://flakehub.com/")
        return "\n".join(results)
    except requests.Timeout:
        return error("FlakeHub API timed out", "TIMEOUT")
    except requests.RequestException as e:
        return error(f"FlakeHub API error: {e}", "API_ERROR")
    except Exception as e:
        return error(str(e))
