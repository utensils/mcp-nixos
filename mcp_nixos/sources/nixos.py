"""NixOS packages and options source."""

import re

from ..utils import error
from .base import es_query, get_channel_suggestions, get_channels


def _search_nixos(query: str, search_type: str, limit: int, channel: str) -> str:
    """Search NixOS packages, options, or programs via Elasticsearch."""
    # Import here to avoid circular import
    from .flakes import _search_flakes

    if search_type == "flakes":
        # Delegate to flakes search
        return _search_flakes(query, limit)

    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
        if search_type == "packages":
            q = {
                "bool": {
                    "must": [{"term": {"type": "package"}}],
                    "should": [
                        {"match": {"package_pname": {"query": query, "boost": 3}}},
                        {"match": {"package_description": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        elif search_type == "options":
            q = {
                "bool": {
                    "must": [{"term": {"type": "option"}}],
                    "should": [
                        {"wildcard": {"option_name": f"*{query}*"}},
                        {"match": {"option_description": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        else:  # programs
            q = {
                "bool": {
                    "must": [{"term": {"type": "package"}}],
                    "should": [
                        {"match": {"package_programs": {"query": query, "boost": 2}}},
                        {"match": {"package_pname": query}},
                    ],
                    "minimum_should_match": 1,
                }
            }

        hits = es_query(channels[channel], q, limit)
        if not hits:
            return f"No {search_type} found matching '{query}'"

        results = [f"Found {len(hits)} {search_type} matching '{query}':\n"]
        for hit in hits:
            src = hit.get("_source", {})
            if search_type == "packages":
                name = src.get("package_pname", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")
                results.append(f"* {name} ({version})")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            elif search_type == "options":
                name = src.get("option_name", "")
                opt_type = src.get("option_type", "")
                desc = src.get("option_description", "")
                if desc and "<rendered-html>" in desc:
                    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                    desc = re.sub(r"<[^>]+>", "", desc).strip()
                results.append(f"* {name}")
                if opt_type:
                    results.append(f"  Type: {opt_type}")
                if desc:
                    results.append(f"  {desc}")
                results.append("")
            else:  # programs
                programs = src.get("package_programs", [])
                pkg_name = src.get("package_pname", "")
                query_lower = query.lower()
                matched_programs = [p for p in programs if p.lower() == query_lower]
                for prog in matched_programs:
                    results.append(f"* {prog} (provided by {pkg_name})")
                    results.append("")
        return "\n".join(results).strip()
    except Exception as e:
        return error(str(e))


def _info_nixos(name: str, info_type: str, channel: str) -> str:
    """Get detailed info for a NixOS package or option."""
    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
        field = "package_pname" if info_type == "package" else "option_name"
        query = {"bool": {"must": [{"term": {"type": info_type}}, {"term": {field: name}}]}}
        hits = es_query(channels[channel], query, 1)

        if not hits:
            return error(f"{info_type.capitalize()} '{name}' not found", "NOT_FOUND")

        src = hits[0].get("_source", {})
        if info_type == "package":
            info = [f"Package: {src.get('package_pname', '')}", f"Version: {src.get('package_pversion', '')}"]
            desc = src.get("package_description", "")
            if desc:
                info.append(f"Description: {desc}")
            homepage = src.get("package_homepage", [])
            if homepage:
                if isinstance(homepage, list):
                    homepage = homepage[0] if homepage else ""
                info.append(f"Homepage: {homepage}")
            licenses = src.get("package_license_set", [])
            if licenses:
                info.append(f"License: {', '.join(licenses)}")
            return "\n".join(info)
        else:
            info = [f"Option: {src.get('option_name', '')}"]
            opt_type = src.get("option_type", "")
            if opt_type:
                info.append(f"Type: {opt_type}")
            desc = src.get("option_description", "")
            if desc:
                if "<rendered-html>" in desc:
                    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")
                    desc = re.sub(r"<[^>]+>", "", desc).strip()
                info.append(f"Description: {desc}")
            default = src.get("option_default", "")
            if default:
                info.append(f"Default: {default}")
            example = src.get("option_example", "")
            if example:
                info.append(f"Example: {example}")
            return "\n".join(info)
    except Exception as e:
        return error(str(e))


def _stats_nixos(channel: str) -> str:
    """Get NixOS package and option counts for a channel."""
    import requests

    from ..config import NIXOS_API, NIXOS_AUTH

    channels = get_channels()
    if channel not in channels:
        return error(f"Invalid channel '{channel}'. {get_channel_suggestions(channel)}")

    try:
        index = channels[channel]
        url = f"{NIXOS_API}/{index}/_count"
        try:
            pkg_resp = requests.post(url, json={"query": {"term": {"type": "package"}}}, auth=NIXOS_AUTH, timeout=10)
            pkg_count = pkg_resp.json().get("count", 0)
        except Exception:
            pkg_count = 0
        try:
            opt_resp = requests.post(url, json={"query": {"term": {"type": "option"}}}, auth=NIXOS_AUTH, timeout=10)
            opt_count = opt_resp.json().get("count", 0)
        except Exception:
            opt_count = 0

        if pkg_count == 0 and opt_count == 0:
            return error("Failed to retrieve statistics")
        return f"NixOS Statistics ({channel}):\n* Packages: {pkg_count:,}\n* Options: {opt_count:,}"
    except Exception as e:
        return error(str(e))
