"""NixOS packages and options source."""

import json
import re
from typing import Any

from ..utils import error
from .base import es_query, get_channel_suggestions, get_channels

# Field weights mirror the search.nixos.org frontend Elm source
# (nixos-search repo: frontend/src/Search/Query.elm — packagesBody / optionsBody).
# Verified against live ES index document keys — only fields that actually exist
# on the NixOS packages / options indices are referenced.
# Note: the frontend options query template also references option_name_query,
# service_package(s), flake_name — those are template fields for the
# home-manager / darwin / flakes indices and are silently ignored by ES against
# the NixOS options index, so we omit them here.
_PACKAGE_SEARCH_FIELDS: list[tuple[str, float]] = [
    ("package_attr_name", 9.0),
    ("package_programs", 9.0),
    ("package_pname", 6.0),
    ("package_description", 1.3),
    ("package_longDescription", 1.0),
]
_OPTION_SEARCH_FIELDS: list[tuple[str, float]] = [
    ("option_name", 6.0),
    ("option_description", 1.0),
]

# Fields the phrase clause scores over for multi-word queries (upstream `phraseFields`).
_PACKAGE_PHRASE_FIELDS = ["package_description^3", "package_longDescription^1"]
_OPTION_PHRASE_FIELDS = ["option_description^3"]

# `rank_feature` popularity signals — packages only (upstream `popularityClauses`).
# Each entry is (field, saturation pivot).
_PACKAGE_POPULARITY: list[tuple[str, float]] = [
    ("package_repology_repos", 20.0),
    ("package_dep_count", 1000.0),
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


def _query_words(query: str) -> list[str]:
    """Lower-case the query and split it into clause-safe words.

    ES wildcard metacharacters (`*`, `?`, `\\`) are stripped rather than escaped.
    None of them can occur in a nix attribute path, option name or binary name,
    so a query like `firefox*` means "firefox" — escaping it instead would make
    every clause search for a literal asterisk and return nothing.
    """
    cleaned = query.lower().translate({ord(c): None for c in "*?\\"})
    return cleaned.split()


def _wildcard_clauses(words: list[str], field: str) -> list[dict[str, Any]]:
    """Build case_insensitive wildcard clauses, mirroring upstream `searchFields`.

    One clause per query word, plus its `_ ↔ -` swap variants, so `musicfree`
    hits `musicfree-desktop` and `firefox_esr` hits `firefox-esr` — matches the
    analyzer would otherwise miss. An empty word list yields zero clauses.
    """
    candidates: set[str] = set()
    for word in words:
        candidates |= _hyphen_variants(word)
    candidates.discard("")
    return [{"wildcard": {field: {"value": f"*{w}*", "case_insensitive": True}}} for w in sorted(candidates)]


def _normalize_query(query: str) -> str:
    """Trim and length-cap the raw query at the `_search_nixos` entry.

    The result is what the user sees echoed back in the response; clause-building
    goes through `_query_words`, which does the lower-casing and metacharacter
    stripping.
    """
    return query.strip()[:_MAX_QUERY_LEN]


def _weighted_fields(fields: list[tuple[str, float]]) -> list[str]:
    """Expand (field, weight) pairs into upstream's `field^w` + `field.*^(w*0.6)` list.

    The `.*` variant lets multi-field sub-fields (e.g. `package_attr_name.edge`)
    contribute at a lower weight, exactly as upstream `searchFields` does.
    """
    expanded: list[str] = []
    for name, weight in fields:
        expanded.append(f"{name}^{weight}")
        expanded.append(f"{name}.*^{round(weight * 0.6, 4)}")
    return expanded


def _should_clauses(
    words: list[str], main_field: str, phrase_fields: list[str], popularity: list[tuple[str, float]]
) -> list[dict[str, Any]]:
    """Relevance boosts that decide ordering (upstream `shouldClauses` + `popularityClauses`).

    Without these the dis_max alone ranks `firefox-esr-153-unwrapped` above
    `firefox` for the query `firefox`:
    - exact term on the primary field (boost 100) — an exact name always wins
    - case-insensitive prefix (boost 20)
    - phrase match over the description fields (boost 80, multi-word only)
    - `rank_feature` popularity saturation (packages only)
    """
    clauses: list[dict[str, Any]] = []
    if words:
        joined = "".join(words)
        clauses.append({"term": {main_field: {"value": joined, "boost": 100.0}}})
        clauses.append({"prefix": {main_field: {"value": joined, "boost": 20.0, "case_insensitive": True}}})
        if len(words) > 1:
            clauses.append(
                {
                    "constant_score": {
                        "filter": {
                            "multi_match": {"type": "phrase", "query": " ".join(words), "fields": phrase_fields}
                        },
                        "boost": 80.0,
                    }
                }
            )
    clauses.extend(
        {"rank_feature": {"field": field, "boost": 5.0, "saturation": {"pivot": pivot}}} for field, pivot in popularity
    )
    return clauses


def _build_search_query(
    query: str,
    type_term: str,
    fields: list[tuple[str, float]],
    main_field: str,
    phrase_fields: list[str],
    popularity: list[tuple[str, float]],
) -> dict[str, Any]:
    """Build the ES query body mirroring the search.nixos.org frontend semantics.

    `bool(filter=type, must=dis_max(multi_match + wildcards), should=boosts)`:
    - `multi_match(cross_fields, whitespace analyzer, operator=and)` does the
      weighted cross-field match. The query is lower-cased because the
      `whitespace` analyzer does not fold case, so `MusicFree` would otherwise
      never match the lower-cased index terms.
    - The wildcard fallback covers substring and `_ ↔ -` hyphen variants.
    - `should` carries the boosts that determine ordering (see `_should_clauses`).
    """
    words = _query_words(query)
    return {
        "bool": {
            "filter": [{"term": {"type": type_term}}],
            "must": [
                {
                    "dis_max": {
                        "tie_breaker": 0.7,
                        "queries": [
                            {
                                "multi_match": {
                                    "type": "cross_fields",
                                    "query": " ".join(words),
                                    "analyzer": "whitespace",
                                    "auto_generate_synonyms_phrase_query": False,
                                    "operator": "and",
                                    "fields": _weighted_fields(fields),
                                }
                            },
                            *_wildcard_clauses(words, main_field),
                        ],
                    }
                }
            ],
            "should": _should_clauses(words, main_field, phrase_fields, popularity),
        }
    }


# Upstream `rescoreQuery`: re-rank the top window by inverse attribute-name
# length so short, canonical names (`firefox`) outrank long derived ones
# (`firefox-esr-153-unwrapped`) at equal relevance. Packages only — the options
# index has no equivalent primary-name length signal upstream rescores on.
_PACKAGE_RESCORE: dict[str, Any] = {
    "window_size": 100,
    "query": {
        "rescore_query": {
            "function_score": {"script_score": {"script": {"source": "1.0 / doc['package_attr_name'].value.length()"}}}
        },
        "rescore_query_weight": 20.0,
    },
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

    # Centralized preprocessing: trim + length cap (SSOT — downstream helpers
    # assume normalized input). Wildcard metacharacters are escaped per-clause.
    query = _normalize_query(query)
    if not _query_words(query):
        # Nothing searchable left (empty or metacharacter-only query) — an empty
        # multi_match would just be a slow way to match nothing.
        return f"No {search_type} found matching '{query}'"

    try:
        if search_type == "options":
            q = _build_search_query(query, "option", _OPTION_SEARCH_FIELDS, "option_name", _OPTION_PHRASE_FIELDS, [])
            rescore = None
        elif search_type == "programs":
            # Programs search hits the same index as packages, but the primary
            # field is the binary name: `rg` is provided by `ripgrep`, whose attr
            # name shares nothing with the query. Boosting and wildcarding
            # package_attr_name here pushes the real providers out of the result
            # window, so programs anchors on package_programs instead — and skips
            # the attr-name-length rescore, which is meaningless for binaries.
            q = _build_search_query(
                query, "package", _PACKAGE_SEARCH_FIELDS, "package_programs", _PACKAGE_PHRASE_FIELDS, []
            )
            rescore = None
        else:
            q = _build_search_query(
                query,
                "package",
                _PACKAGE_SEARCH_FIELDS,
                "package_attr_name",
                _PACKAGE_PHRASE_FIELDS,
                _PACKAGE_POPULARITY,
            )
            rescore = _PACKAGE_RESCORE

        hits = es_query(channels[channel], q, limit, rescore=rescore)
        if not hits:
            return f"No {search_type} found matching '{query}'"

        # Count what is actually rendered, not what ES returned: the programs
        # branch drops hits whose program list has no exact match, so `len(hits)`
        # would overstate the result count.
        shown = 0
        results: list[str] = []
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
                shown += 1
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
                shown += 1
            else:  # programs
                programs = src.get("package_programs", [])
                pkg_name = src.get("package_pname", "")
                query_lower = query.lower()
                matched_programs = [p for p in programs if p.lower() == query_lower]
                for prog in matched_programs:
                    results.append(f"* {prog} (provided by {pkg_name})")
                    results.append("")
                    shown += 1
        if not shown:
            return f"No {search_type} found matching '{query}'"
        return "\n".join([f"Found {shown} {search_type} matching '{query}':\n", *results]).strip()
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
