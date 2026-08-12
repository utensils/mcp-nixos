"""NixOS packages and options source."""

import json
import re
from typing import Any

from ..utils import error
from .base import es_query, get_channel_suggestions, get_channels

# Field weights mirror the search.nixos.org frontend Elm source
# (nixos-search repo: frontend/src/Page/Packages.elm — defaultSearchFields).
# Verified against live ES index document keys — only fields that actually exist
# on the NixOS packages / options indices are referenced.
# Note: the frontend options query template also references option_name_query,
# service_package(s), flake_name — those are template fields for the
# home-manager / darwin / flakes indices and are silently ignored by ES against
# the NixOS options index, so we omit them here.
_PACKAGE_SEARCH_FIELDS = [
    "package_attr_name^9",
    "package_programs^9",
    "package_pname^6",
    "package_description^1.3",
    "package_longDescription^1",
]
_OPTION_SEARCH_FIELDS = [
    "option_name^6",
    "option_description^1",
]

# Query length cap: wildcard is a term-level scan, so an overlong query makes
# substring matching noticeably slower. 200 chars covers any realistic package
# name or option path (longest observed nixpkgs attr paths are well under 100)
# while blocking LLM-generated paragraphs.
_MAX_QUERY_LEN = 200


def _hyphen_variants(token: str) -> set[str]:
    """Return the token plus its `_ ↔ -` swap variants.

    The nix ecosystem mixes `_` and `-` (e.g. `steam_install` / `steam-runtime`),
    so search should treat them as interchangeable.
    """
    return {token, token.replace("_", "-"), token.replace("-", "_")}


def _wildcard_clauses(query: str, field: str) -> list[dict[str, Any]]:
    """Build case_insensitive wildcard clauses, mirroring the frontend Elm (Search.elm).

    1. The whole query string is a candidate (covers substring matches like
       `musicfree` hitting `musicfree-desktop`).
    2. Each whitespace-separated token gets its own wildcard clause (multi-word queries).
    3. `_ ↔ -` swap variants via `_hyphen_variants`.

    Precondition: `query` must already be normalized (trimmed) by the caller —
    `_search_nixos` calls `_normalize_query` before reaching here, which turns
    pure-whitespace input into an empty string. An empty `query` yields zero
    clauses, leaving the dis_max branch inactive.
    """
    lowered = query.lower()
    tokens = [lowered, *lowered.split()]
    candidates: set[str] = set()
    for token in tokens:
        candidates |= _hyphen_variants(token)
    candidates.discard("")
    return [{"wildcard": {field: {"value": f"*{w}*", "case_insensitive": True}}} for w in sorted(candidates)]


def _normalize_query(query: str) -> str:
    """Centralized input preprocessing at the `_search_nixos` entry: trim, truncate, escape.

    Escapes `*`, `?`, `\\` so they are treated as literals by ES wildcard semantics
    (prevents metacharacter injection). Length cap blocks LLM-generated paragraphs
    that would make wildcard substring scans expensive.
    """
    q = query.strip()
    if len(q) > _MAX_QUERY_LEN:
        q = q[:_MAX_QUERY_LEN]
    return q.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?")


def _build_search_query(query: str, fields: list[str], wildcard_field: str) -> dict[str, Any]:
    """Build the ES query body mirroring the search.nixos.org frontend semantics.

    `dis_max(multi_match + wildcard fallback)`:
    - `multi_match(cross_fields, whitespace analyzer, operator=and)` does the
      weighted cross-field match (tie_breaker / auto_generate_synonyms_phrase_query
      values come straight from the frontend Elm source).
    - The wildcard fallback (tokenized + `_ ↔ -` swapped + case_insensitive)
      covers substring and hyphen-variant matches the analyzer would otherwise miss.
    """
    return {
        "dis_max": {
            "tie_breaker": 0.7,
            "queries": [
                {
                    "multi_match": {
                        "type": "cross_fields",
                        "query": query,
                        "analyzer": "whitespace",
                        "auto_generate_synonyms_phrase_query": False,
                        "operator": "and",
                        "fields": fields,
                    }
                },
                *_wildcard_clauses(query, wildcard_field),
            ],
        }
    }


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

    # Centralized preprocessing: trim + length truncation + wildcard metachar escaping
    # (SSOT — downstream helpers assume normalized input).
    query = _normalize_query(query)

    try:
        if search_type == "options":
            type_term, fields, wildcard_field = "option", _OPTION_SEARCH_FIELDS, "option_name"
        else:
            # packages and programs share the same query (programs is a specialization):
            # `package_programs^9` in the multi_match already surfaces packages that
            # provide the binary; the result-rendering stage then filters by exact
            # program-name match — two layers together ensure correct program search.
            type_term, fields, wildcard_field = "package", _PACKAGE_SEARCH_FIELDS, "package_attr_name"
        q = {"bool": {"must": [{"term": {"type": type_term}}, _build_search_query(query, fields, wildcard_field)]}}

        hits = es_query(channels[channel], q, limit)
        if not hits:
            return f"No {search_type} found matching '{query}'"

        results = [f"Found {len(hits)} {search_type} matching '{query}':\n"]
        for hit in hits:
            src = hit.get("_source", {})
            if search_type == "packages":
                name = src.get("package_pname", "")
                attr_name = src.get("package_attr_name", "")
                version = src.get("package_pversion", "")
                desc = src.get("package_description", "")
                display_name = attr_name if attr_name and attr_name != name else name
                results.append(f"* {display_name} ({version})")
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
        if info_type == "package":
            # Priority 1: exact attribute path match — one attr maps to one package, so
            # this is deterministic. Handles dotted names (kdePackages.qt6ct) and
            # disambiguates between packages that share a pname (firefox, firefox-esr,
            # firefox-mobile all have pname="firefox"). See GH #146.
            attr_query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {"package_attr_name": name}}]}}
            hits = es_query(channels[channel], attr_query, 1)
            matched_via = "attribute" if hits else ""

            pname_candidates: list[dict[str, Any]] = []
            if not hits:
                # Priority 2: pname match. Fetch up to 5 so we can detect ambiguity
                # (multiple attrs sharing the same pname) and pick the canonical one.
                pname_query = {"bool": {"must": [{"term": {"type": "package"}}, {"term": {"package_pname": name}}]}}
                pname_candidates = es_query(channels[channel], pname_query, 5)
                if pname_candidates:
                    # Prefer the canonical entry (attr == pname). When none
                    # exists, sort by attribute path so the tie-break is
                    # deterministic across requests — ES does not guarantee
                    # a stable order for equal-score term matches.
                    canonical = [
                        h
                        for h in pname_candidates
                        if h.get("_source", {}).get("package_attr_name") == h.get("_source", {}).get("package_pname")
                    ]
                    if canonical:
                        chosen = canonical[0]
                    else:
                        chosen = sorted(
                            pname_candidates,
                            key=lambda h: (
                                h.get("_source", {}).get("package_attr_name", ""),
                                h.get("_source", {}).get("package_pname", ""),
                            ),
                        )[0]
                    hits = [chosen]
                    matched_via = "pname"
        else:
            query = {"bool": {"must": [{"term": {"type": "option"}}, {"term": {"option_name": name}}]}}
            hits = es_query(channels[channel], query, 1)
            matched_via = "exact" if hits else ""
            pname_candidates = []

        if not hits:
            return error(f"{info_type.capitalize()} '{name}' not found", "NOT_FOUND")

        src = hits[0].get("_source", {})
        if info_type == "package":
            attr_name = src.get("package_attr_name", "")
            pname = src.get("package_pname", "")
            info = [f"Package: {pname}"]
            if attr_name and attr_name != pname:
                info.append(f"Attribute: {attr_name}")
            info.append(f"Version: {src.get('package_pversion', '')}")
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
            if matched_via == "pname" and len(pname_candidates) > 1:
                # Flag ambiguity explicitly so callers don't silently act on the wrong
                # package. Name the alternatives so the caller can retry with the exact
                # attribute path.
                alternatives = sorted(
                    {
                        h.get("_source", {}).get("package_attr_name", "")
                        for h in pname_candidates
                        if h.get("_source", {}).get("package_attr_name")
                    }
                )
                chosen_attr = attr_name or pname
                others = [a for a in alternatives if a != chosen_attr]
                if others:
                    picked_canonical = any(
                        h.get("_source", {}).get("package_attr_name")
                        == h.get("_source", {}).get("package_pname")
                        == name
                        for h in pname_candidates
                    )
                    chosen_label = "the canonical entry" if picked_canonical else "a representative entry"
                    retry_call = json.dumps({"action": "info", "query": others[0], "channel": channel})
                    info.append("")
                    info.append(
                        f"Note: '{name}' is a pname shared by multiple packages. Returned "
                        f"{chosen_label} ({chosen_attr}). Other attributes with the same "
                        f"pname: {', '.join(others)}. Pass an exact attribute to "
                        f"disambiguate, e.g. {retry_call}."
                    )
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
