"""Unit tests for the NixOS Elasticsearch query builder.

These cover the pure query-construction helpers in `mcp_nixos.sources.nixos`
without touching the network: the shape of the emitted ES body, the relevance
boosts that decide result ordering, and the input normalization applied before
any clause is built.
"""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos.sources.nixos import (
    _MAX_QUERY_LEN,
    _OPTION_SEARCH_FIELDS,
    _PACKAGE_POPULARITY,
    _PACKAGE_RESCORE,
    _PACKAGE_SEARCH_FIELDS,
    _build_search_query,
    _hyphen_variants,
    _normalize_query,
    _query_words,
    _search_nixos,
    _should_clauses,
    _weighted_fields,
    _wildcard_clauses,
)


def _wildcard_values(clauses, field):
    return [c["wildcard"][field]["value"] for c in clauses]


@pytest.mark.unit
class TestQueryNormalization:
    """`_normalize_query` produces the string echoed back to the user."""

    def test_trims_whitespace(self):
        assert _normalize_query("  firefox  ") == "firefox"

    def test_truncates_overlong_query(self):
        assert len(_normalize_query("x" * 500)) == _MAX_QUERY_LEN

    def test_preserves_metacharacters_for_display(self):
        # Escaping here would leak backslashes into the response text.
        assert _normalize_query("firefox*") == "firefox*"


@pytest.mark.unit
class TestQueryWords:
    """`_query_words` produces the clause-safe word list."""

    def test_lowercases(self):
        assert _query_words("MusicFree") == ["musicfree"]

    def test_splits_on_whitespace(self):
        assert _query_words("text editor") == ["text", "editor"]

    def test_strips_wildcard_metacharacters(self):
        # Stripped, not escaped: `firefox*` must still search for "firefox".
        assert _query_words("firefox*") == ["firefox"]
        assert _query_words("what?") == ["what"]
        assert _query_words("a\\b") == ["ab"]

    def test_metacharacter_only_query_is_empty(self):
        assert _query_words("*?") == []
        assert _query_words("   ") == []


@pytest.mark.unit
class TestHyphenVariants:
    def test_underscore_and_dash_are_interchangeable(self):
        assert _hyphen_variants("firefox_esr") == {"firefox_esr", "firefox-esr"}

    def test_plain_word_has_single_variant(self):
        assert _hyphen_variants("firefox") == {"firefox"}


@pytest.mark.unit
class TestWildcardClauses:
    def test_wraps_each_word_in_substring_wildcards(self):
        clauses = _wildcard_clauses(["musicfree"], "package_attr_name")
        assert _wildcard_values(clauses, "package_attr_name") == ["*musicfree*"]

    def test_emits_hyphen_variants(self):
        values = _wildcard_values(_wildcard_clauses(["firefox_esr"], "package_attr_name"), "package_attr_name")
        assert sorted(values) == ["*firefox-esr*", "*firefox_esr*"]

    def test_clauses_are_case_insensitive(self):
        clause = _wildcard_clauses(["vim"], "package_attr_name")[0]
        assert clause["wildcard"]["package_attr_name"]["case_insensitive"] is True

    def test_multi_word_query_yields_one_clause_per_word(self):
        values = _wildcard_values(_wildcard_clauses(["docker", "compose"], "package_attr_name"), "package_attr_name")
        assert sorted(values) == ["*compose*", "*docker*"]

    def test_empty_word_list_yields_no_clauses(self):
        assert _wildcard_clauses([], "package_attr_name") == []


@pytest.mark.unit
class TestWeightedFields:
    def test_expands_each_field_into_base_and_subfield(self):
        assert _weighted_fields([("package_pname", 6.0)]) == ["package_pname^6.0", "package_pname.*^3.6"]

    def test_subfield_weight_is_60_percent(self):
        expanded = _weighted_fields([("package_description", 1.3)])
        assert expanded[1] == "package_description.*^0.78"


@pytest.mark.unit
class TestShouldClauses:
    """The boosts that decide ordering — without them `firefox` loses to `firefox-esr-153-unwrapped`."""

    def test_exact_term_boost_dominates(self):
        clauses = _should_clauses(["firefox"], "package_attr_name", [], [])
        term = next(c for c in clauses if "term" in c)
        assert term["term"]["package_attr_name"] == {"value": "firefox", "boost": 100.0}

    def test_prefix_clause_is_case_insensitive(self):
        clauses = _should_clauses(["firefox"], "package_attr_name", [], [])
        prefix = next(c for c in clauses if "prefix" in c)
        assert prefix["prefix"]["package_attr_name"]["case_insensitive"] is True
        assert prefix["prefix"]["package_attr_name"]["boost"] == 20.0

    def test_multi_word_query_adds_phrase_clause(self):
        clauses = _should_clauses(["text", "editor"], "package_attr_name", ["package_description^3"], [])
        phrase = next(c for c in clauses if "constant_score" in c)
        assert phrase["constant_score"]["filter"]["multi_match"]["query"] == "text editor"
        assert phrase["constant_score"]["boost"] == 80.0

    def test_single_word_query_has_no_phrase_clause(self):
        clauses = _should_clauses(["firefox"], "package_attr_name", ["package_description^3"], [])
        assert not any("constant_score" in c for c in clauses)

    def test_words_are_joined_for_term_and_prefix(self):
        # Upstream concatenates the words with no separator.
        clauses = _should_clauses(["rust", "analyzer"], "package_attr_name", [], [])
        term = next(c for c in clauses if "term" in c)
        assert term["term"]["package_attr_name"]["value"] == "rustanalyzer"

    def test_popularity_signals_become_rank_features(self):
        clauses = _should_clauses(["firefox"], "package_attr_name", [], _PACKAGE_POPULARITY)
        features = [c["rank_feature"] for c in clauses if "rank_feature" in c]
        assert [f["field"] for f in features] == ["package_repology_repos", "package_dep_count"]
        assert features[0]["saturation"]["pivot"] == 20.0

    def test_empty_word_list_yields_only_popularity(self):
        assert _should_clauses([], "package_attr_name", [], []) == []


@pytest.mark.unit
class TestBuildSearchQuery:
    def test_type_filter_is_non_scoring(self):
        q = _build_search_query("firefox", "package", _PACKAGE_SEARCH_FIELDS, "package_attr_name", [], [])
        assert q["bool"]["filter"] == [{"term": {"type": "package"}}]

    def test_multi_match_is_lowercased(self):
        # The whitespace analyzer does not fold case, so the query must be lowered
        # before it reaches ES or `MusicFree` never matches.
        q = _build_search_query("MusicFree", "package", _PACKAGE_SEARCH_FIELDS, "package_attr_name", [], [])
        multi_match = q["bool"]["must"][0]["dis_max"]["queries"][0]["multi_match"]
        assert multi_match["query"] == "musicfree"
        assert multi_match["type"] == "cross_fields"
        assert multi_match["operator"] == "and"

    def test_dis_max_carries_wildcard_fallback(self):
        q = _build_search_query("musicfree", "package", _PACKAGE_SEARCH_FIELDS, "package_attr_name", [], [])
        queries = q["bool"]["must"][0]["dis_max"]["queries"]
        assert q["bool"]["must"][0]["dis_max"]["tie_breaker"] == 0.7
        assert any("wildcard" in clause for clause in queries)

    def test_dotted_name_is_sent_whole(self):
        q = _build_search_query(
            "python314Packages.matplotlib", "package", _PACKAGE_SEARCH_FIELDS, "package_attr_name", [], []
        )
        multi_match = q["bool"]["must"][0]["dis_max"]["queries"][0]["multi_match"]
        assert multi_match["query"] == "python314packages.matplotlib"

    def test_options_query_filters_on_option_type(self):
        q = _build_search_query("fontconfig", "option", _OPTION_SEARCH_FIELDS, "option_name", [], [])
        assert q["bool"]["filter"] == [{"term": {"type": "option"}}]
        assert "option_name^6.0" in q["bool"]["must"][0]["dis_max"]["queries"][0]["multi_match"]["fields"]


@pytest.mark.unit
class TestSearchWiring:
    """`_search_nixos` picks the right primary field and rescore per search type."""

    @staticmethod
    def _run(search_type, query="vim", hits=None):
        with (
            patch("mcp_nixos.sources.nixos.get_channels", return_value={"unstable": "latest-nixos-unstable"}),
            patch("mcp_nixos.sources.nixos.es_query", Mock(return_value=hits or [])) as mock_es,
        ):
            _search_nixos(query, search_type, 5, "unstable")
        return mock_es.call_args

    def test_packages_anchor_on_attr_name_and_rescore(self):
        args, kwargs = self._run("packages")
        should = args[1]["bool"]["should"]
        assert any("package_attr_name" in c.get("term", {}) for c in should)
        assert kwargs["rescore"] == _PACKAGE_RESCORE

    def test_programs_anchor_on_package_programs_without_rescore(self):
        # `rg` is provided by `ripgrep`: boosting package_attr_name would push the
        # real provider out of the result window.
        args, kwargs = self._run("programs", query="rg")
        should = args[1]["bool"]["should"]
        assert any("package_programs" in c.get("term", {}) for c in should)
        assert not any("package_attr_name" in c.get("term", {}) for c in should)
        assert kwargs["rescore"] is None

    def test_options_use_option_name_without_rescore(self):
        args, kwargs = self._run("options", query="fontconfig")
        should = args[1]["bool"]["should"]
        assert any("option_name" in c.get("term", {}) for c in should)
        assert kwargs["rescore"] is None

    def test_metacharacter_only_query_skips_the_request(self):
        with (
            patch("mcp_nixos.sources.nixos.get_channels", return_value={"unstable": "latest-nixos-unstable"}),
            patch("mcp_nixos.sources.nixos.es_query", Mock()) as mock_es,
        ):
            result = _search_nixos("*", "packages", 5, "unstable")
        mock_es.assert_not_called()
        assert result == "No packages found matching '*'"


@pytest.mark.unit
class TestResultCount:
    """The reported count must match the number of rendered entries."""

    @staticmethod
    def _program_hit(programs, pname):
        return {"_source": {"package_programs": programs, "package_pname": pname}}

    def _search_programs(self, hits, query="vim"):
        with (
            patch("mcp_nixos.sources.nixos.get_channels", return_value={"unstable": "latest-nixos-unstable"}),
            patch("mcp_nixos.sources.nixos.es_query", Mock(return_value=hits)),
        ):
            return _search_nixos(query, "programs", 5, "unstable")

    def test_count_excludes_hits_with_no_matching_program(self):
        # ES returns 3 packages, but only 1 actually provides a binary named `vim`.
        result = self._search_programs(
            [
                self._program_hit(["vim"], "vim"),
                self._program_hit(["nvim"], "neovim"),
                self._program_hit(["vimdiff"], "vim-full"),
            ]
        )
        assert result.startswith("Found 1 programs matching 'vim':")
        assert result.count("* ") == 1

    def test_no_matching_program_reports_nothing_found(self):
        result = self._search_programs([self._program_hit(["nvim"], "neovim")])
        assert result == "No programs found matching 'vim'"

    def test_package_count_matches_rendered_entries(self):
        hits = [
            {"_source": {"package_pname": "firefox", "package_attr_name": "firefox", "package_pversion": "1"}},
            {"_source": {"package_pname": "firefox", "package_attr_name": "firefox-esr", "package_pversion": "2"}},
        ]
        with (
            patch("mcp_nixos.sources.nixos.get_channels", return_value={"unstable": "latest-nixos-unstable"}),
            patch("mcp_nixos.sources.nixos.es_query", Mock(return_value=hits)),
        ):
            result = _search_nixos("firefox", "packages", 5, "unstable")
        assert result.startswith("Found 2 packages matching 'firefox':")
