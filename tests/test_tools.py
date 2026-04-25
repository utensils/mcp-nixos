"""Tests for the nix and nix_versions MCP tools.

IMPORTANT: This test file should ONLY test the MCP tools directly.
- Do NOT run bash commands or shell operations
- Do NOT interact with the filesystem beyond what the tools do internally
- Do NOT spawn subprocesses or external commands
- ONLY call the nix_fn and nix_versions_fn functions to test tool behavior

These tests verify:
- Input validation and error handling
- Correct response formatting (plain text, no XML/JSON leakage)
- API interaction through the tool interfaces
- Edge cases and boundary conditions
"""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos.server import nix, nix_versions

# Get underlying functions from MCP tool wrappers.
# FastMCP 2.x wraps @mcp.tool() functions as FunctionTool (with .fn); FastMCP 3.x
# returns the plain async function. Support both.
nix_fn = getattr(nix, "fn", nix)
nix_versions_fn = getattr(nix_versions, "fn", nix_versions)


@pytest.mark.unit
class TestNixToolValidation:
    """Test input validation for the nix tool."""

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        result = await nix_fn(action="invalid")
        assert "Error" in result
        assert "search" in result and "browse" in result

    @pytest.mark.asyncio
    async def test_search_requires_query(self):
        result = await nix_fn(action="search", query="")
        assert "Error" in result
        assert "Query required" in result

    @pytest.mark.asyncio
    async def test_info_requires_query(self):
        result = await nix_fn(action="info", query="")
        assert "Error" in result
        assert "Name required" in result

    @pytest.mark.asyncio
    async def test_invalid_source(self):
        result = await nix_fn(action="search", query="test", source="invalid")
        assert "Error" in result
        assert "nixos" in result and "home-manager" in result

    @pytest.mark.asyncio
    async def test_info_flakes_redirects_to_search(self):
        """action=info with source=flakes should point at action=search with a JSON example."""
        result = await nix_fn(action="info", source="flakes", query="test")
        assert "Error" in result
        assert '"action": "search"' in result
        assert '"source": "flakes"' in result

    @pytest.mark.asyncio
    async def test_info_unknown_source_uses_prose_not_pipes(self):
        """Unknown sources for action=info keep the allowlist error but use commas, not pipes."""
        result = await nix_fn(action="info", source="bogus", query="test")
        assert "Error" in result
        assert "Unknown source" in result
        assert "|" not in result
        assert "nixos, home-manager" in result

    @pytest.mark.asyncio
    async def test_browse_nixos_redirects_to_search(self):
        """action=browse with source=nixos should redirect to the correct search/info form (#125)."""
        result = await nix_fn(action="browse", source="nixos")
        assert "Error" in result
        assert '"action": "search"' in result
        assert '"type": "options"' in result

    @pytest.mark.asyncio
    async def test_options_alias_nixos_redirects_to_search(self):
        """Legacy action=options alias should behave like browse and redirect for source=nixos."""
        result = await nix_fn(action="options", source="nixos")
        assert "Error" in result
        assert '"action": "search"' in result
        assert '"type": "options"' in result

    @pytest.mark.asyncio
    async def test_browse_only_for_hm_darwin_nixvim_noogle(self):
        result = await nix_fn(action="browse", source="flakes")
        assert "Error" in result
        assert "home-manager" in result and "darwin" in result
        assert "nixvim" in result and "noogle" in result

    @pytest.mark.asyncio
    async def test_limit_too_low(self):
        result = await nix_fn(action="search", query="test", limit=0)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_negative(self):
        result = await nix_fn(action="search", query="test", limit=-1)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_too_high(self):
        result = await nix_fn(action="search", query="test", limit=101)
        assert "Error" in result
        assert "1-100" in result

    @pytest.mark.asyncio
    async def test_limit_at_minimum_boundary(self):
        """Verify limit=1 is valid (doesn't return error)."""
        # This will fail at the search step (no mock), but should NOT fail limit validation
        result = await nix_fn(action="search", query="", limit=1)
        assert "1-100" not in result  # Should not be a limit error

    @pytest.mark.asyncio
    async def test_limit_at_maximum_boundary(self):
        """Verify limit=100 is valid (doesn't return error)."""
        # This will fail at the search step (no mock), but should NOT fail limit validation
        result = await nix_fn(action="search", query="", limit=100)
        assert "1-100" not in result  # Should not be a limit error


class TestNixToolSearch:
    """Test nix tool search action."""

    @patch("mcp_nixos.server._search_nixos")
    @pytest.mark.asyncio
    async def test_search_nixos_packages(self, mock_search):
        mock_search.return_value = "Found 3 packages"
        result = await nix_fn(action="search", query="firefox", source="nixos", type="packages")
        assert result == "Found 3 packages"
        mock_search.assert_called_once_with("firefox", "packages", 20, "unstable")

    @patch("mcp_nixos.server._search_nixos")
    @pytest.mark.asyncio
    async def test_search_nixos_options(self, mock_search):
        mock_search.return_value = "Found 2 options"
        result = await nix_fn(action="search", query="nginx", source="nixos", type="options")
        assert result == "Found 2 options"

    @patch("mcp_nixos.server._search_home_manager")
    @pytest.mark.asyncio
    async def test_search_home_manager(self, mock_search):
        mock_search.return_value = "Found git options"
        result = await nix_fn(action="search", query="git", source="home-manager")
        assert result == "Found git options"
        mock_search.assert_called_once_with("git", 20)

    @patch("mcp_nixos.server._search_darwin")
    @pytest.mark.asyncio
    async def test_search_darwin(self, mock_search):
        mock_search.return_value = "Found darwin options"
        result = await nix_fn(action="search", query="dock", source="darwin")
        assert result == "Found darwin options"
        mock_search.assert_called_once_with("dock", 20)

    @patch("mcp_nixos.server._search_flakes")
    @pytest.mark.asyncio
    async def test_search_flakes(self, mock_search):
        mock_search.return_value = "Found flakes"
        result = await nix_fn(action="search", query="neovim", source="flakes")
        assert result == "Found flakes"
        mock_search.assert_called_once_with("neovim", 20)

    @patch("mcp_nixos.server._search_flakehub")
    @pytest.mark.asyncio
    async def test_search_flakehub(self, mock_search):
        mock_search.return_value = "Found FlakeHub flakes"
        result = await nix_fn(action="search", query="nixpkgs", source="flakehub")
        assert result == "Found FlakeHub flakes"
        mock_search.assert_called_once_with("nixpkgs", 20)


class TestNixToolInfo:
    """Test nix tool info action."""

    @patch("mcp_nixos.server._info_nixos")
    @pytest.mark.asyncio
    async def test_info_nixos_package(self, mock_info):
        mock_info.return_value = "Package: firefox"
        result = await nix_fn(action="info", query="firefox", source="nixos", type="package")
        assert result == "Package: firefox"
        mock_info.assert_called_once_with("firefox", "package", "unstable")

    @patch("mcp_nixos.server._info_nixos")
    @pytest.mark.asyncio
    async def test_info_nixos_option(self, mock_info):
        mock_info.return_value = "Option: services.nginx.enable"
        result = await nix_fn(
            action="info",
            query="services.nginx.enable",
            source="nixos",
            type="option",
        )
        assert result == "Option: services.nginx.enable"
        mock_info.assert_called_once_with("services.nginx.enable", "option", "unstable")

    @patch("mcp_nixos.server._info_home_manager")
    @pytest.mark.asyncio
    async def test_info_home_manager(self, mock_info):
        mock_info.return_value = "Option: programs.git.enable"
        result = await nix_fn(action="info", query="programs.git.enable", source="home-manager")
        assert result == "Option: programs.git.enable"
        mock_info.assert_called_once_with("programs.git.enable")

    @patch("mcp_nixos.server._info_darwin")
    @pytest.mark.asyncio
    async def test_info_darwin(self, mock_info):
        mock_info.return_value = "Option: system.defaults.dock.autohide"
        result = await nix_fn(action="info", query="system.defaults.dock.autohide", source="darwin")
        assert result == "Option: system.defaults.dock.autohide"
        mock_info.assert_called_once_with("system.defaults.dock.autohide")

    @patch("mcp_nixos.server._info_flakehub")
    @pytest.mark.asyncio
    async def test_info_flakehub(self, mock_info):
        mock_info.return_value = "FlakeHub Flake: NixOS/nixpkgs"
        result = await nix_fn(action="info", query="NixOS/nixpkgs", source="flakehub")
        assert result == "FlakeHub Flake: NixOS/nixpkgs"
        mock_info.assert_called_once_with("NixOS/nixpkgs")


class TestNixToolStats:
    """Test nix tool stats action."""

    @patch("mcp_nixos.server._stats_nixos")
    @pytest.mark.asyncio
    async def test_stats_nixos(self, mock_stats):
        mock_stats.return_value = "NixOS Statistics"
        result = await nix_fn(action="stats", source="nixos")
        assert result == "NixOS Statistics"
        mock_stats.assert_called_once_with("unstable")

    @patch("mcp_nixos.server._stats_home_manager")
    @pytest.mark.asyncio
    async def test_stats_home_manager(self, mock_stats):
        mock_stats.return_value = "Home Manager Statistics"
        result = await nix_fn(action="stats", source="home-manager")
        assert result == "Home Manager Statistics"

    @patch("mcp_nixos.server._stats_darwin")
    @pytest.mark.asyncio
    async def test_stats_darwin(self, mock_stats):
        mock_stats.return_value = "Darwin Statistics"
        result = await nix_fn(action="stats", source="darwin")
        assert result == "Darwin Statistics"

    @patch("mcp_nixos.server._stats_flakes")
    @pytest.mark.asyncio
    async def test_stats_flakes(self, mock_stats):
        mock_stats.return_value = "Flakes Statistics"
        result = await nix_fn(action="stats", source="flakes")
        assert result == "Flakes Statistics"

    @patch("mcp_nixos.server._stats_flakehub")
    @pytest.mark.asyncio
    async def test_stats_flakehub(self, mock_stats):
        mock_stats.return_value = "FlakeHub Statistics"
        result = await nix_fn(action="stats", source="flakehub")
        assert result == "FlakeHub Statistics"


class TestNixToolOptions:
    """Test nix tool options action."""

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_home_manager(self, mock_browse):
        mock_browse.return_value = "Home Manager categories"
        result = await nix_fn(action="options", source="home-manager", query="")
        assert result == "Home Manager categories"
        mock_browse.assert_called_once_with("home-manager", "")

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_darwin(self, mock_browse):
        mock_browse.return_value = "Darwin categories"
        result = await nix_fn(action="options", source="darwin", query="")
        assert result == "Darwin categories"
        mock_browse.assert_called_once_with("darwin", "")

    @patch("mcp_nixos.server._browse_options")
    @pytest.mark.asyncio
    async def test_browse_with_prefix(self, mock_browse):
        mock_browse.return_value = "Options with prefix"
        result = await nix_fn(action="options", source="home-manager", query="programs.git")
        assert result == "Options with prefix"
        mock_browse.assert_called_once_with("home-manager", "programs.git")


class TestDottedPackageNameSearch:
    """Test that dotted/namespaced package names (e.g. kdePackages.qt6ct) are searchable.

    Regression tests for GitHub issue #118.
    """

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_search_queries_package_attr_name(self, mock_channels, mock_es):
        """Verify that the ES query includes package_attr_name in the should clause."""
        from mcp_nixos.sources.nixos import _search_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.return_value = []

        _search_nixos("kdePackages.qt6ct", "packages", 5, "unstable")

        # Inspect the query passed to es_query
        call_args = mock_es.call_args
        query = call_args[0][1]  # second positional arg is the query dict
        should_clauses = query["bool"]["should"]

        # There should be a clause matching package_attr_name
        attr_name_clauses = [c for c in should_clauses if "package_attr_name" in str(c)]
        assert len(attr_name_clauses) > 0, (
            "ES query should include package_attr_name in should clauses to support dotted package name searches"
        )

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_search_results_include_attr_name(self, mock_channels, mock_es):
        """Verify that search results display the attribute name (package set)."""
        from mcp_nixos.sources.nixos import _search_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "qt6ct",
                    "package_attr_name": "kdePackages.qt6ct",
                    "package_pversion": "0.11",
                    "package_description": "Qt6 Configuration Tool",
                }
            }
        ]

        result = _search_nixos("qt6ct", "packages", 5, "unstable")
        # Check that the attr path appears in the package listing lines, not just the header
        lines = result.split("\n")
        package_lines = [line for line in lines if line.startswith("* ")]
        attr_in_listing = any("kdePackages.qt6ct" in line for line in package_lines)
        assert attr_in_listing, (
            "Search results should display the full attribute path in the package listing "
            f"so users can see which package set a package belongs to. Got lines: {package_lines}"
        )

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_search_dotted_name_extracts_pname(self, mock_channels, mock_es):
        """Verify that dotted names also search the last component as pname."""
        from mcp_nixos.sources.nixos import _search_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.return_value = []

        _search_nixos("python314Packages.matplotlib", "packages", 5, "unstable")

        call_args = mock_es.call_args
        query = call_args[0][1]
        should_clauses = query["bool"]["should"]

        # The pname clause should search for "matplotlib" (the last component),
        # not the full dotted string
        pname_clauses = [c for c in should_clauses if "match" in c and "package_pname" in c.get("match", {})]
        assert len(pname_clauses) > 0, "Should have a package_pname match clause"
        pname_query = pname_clauses[0]["match"]["package_pname"]
        if isinstance(pname_query, dict):
            pname_value = pname_query["query"]
        else:
            pname_value = pname_query
        assert pname_value == "matplotlib", (
            f"package_pname should search for 'matplotlib' (last component), got '{pname_value}'"
        )

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_finds_package_by_attr_name(self, mock_channels, mock_es):
        """Verify that info lookup can find packages by their full attribute path."""
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        # First call (pname lookup) returns nothing, second call (attr_name) returns the package
        mock_es.side_effect = [
            [],  # pname lookup fails
            [
                {
                    "_source": {
                        "package_pname": "qt6ct",
                        "package_attr_name": "kdePackages.qt6ct",
                        "package_pversion": "0.11",
                        "package_description": "Qt6 Configuration Tool",
                    }
                }
            ],
        ]

        result = _info_nixos("kdePackages.qt6ct", "package", "unstable")
        assert "NOT_FOUND" not in result, "Info should find packages by attribute path when pname lookup fails"
        assert "qt6ct" in result

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_result_shows_attr_name(self, mock_channels, mock_es):
        """Verify that info results display the attribute path."""
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "qt6ct",
                    "package_attr_name": "kdePackages.qt6ct",
                    "package_pversion": "0.11",
                    "package_description": "Qt6 Configuration Tool",
                    "package_homepage": ["https://example.com"],
                    "package_license_set": ["BSD"],
                }
            }
        ]

        result = _info_nixos("qt6ct", "package", "unstable")
        assert "kdePackages.qt6ct" in result, "Info output should include the full attribute path"


class TestNixToolChannels:
    """Test nix tool channels action."""

    @patch("mcp_nixos.server._list_channels")
    @pytest.mark.asyncio
    async def test_list_channels(self, mock_list):
        mock_list.return_value = "Available channels"
        result = await nix_fn(action="channels")
        assert result == "Available channels"
        mock_list.assert_called_once()


@pytest.mark.unit
class TestInfoMatchPriority:
    """Regression tests for GitHub #146.

    action=info must prefer exact attribute match over pname match, and must
    explicitly signal pname-based disambiguation when a query resolves to one
    of several packages sharing a pname.
    """

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_prefers_attr_match_over_pname(self, mock_channels, mock_es):
        """Exact attr=firefox must win over the first pname=firefox candidate.

        Before #146, pname matched first with size:1, which meant ES could
        arbitrarily return firefox-esr for `info firefox`. Attr-first makes
        the canonical package deterministic.
        """
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "firefox",
                    "package_attr_name": "firefox",
                    "package_pversion": "149.0.2",
                    "package_description": "Web browser",
                }
            }
        ]

        result = _info_nixos("firefox", "package", "unstable")

        first_query = mock_es.call_args_list[0][0][1]
        must_terms = [c for c in first_query["bool"]["must"] if "term" in c]
        assert any("package_attr_name" in c["term"] for c in must_terms), (
            "First ES call must be an attribute-path lookup, not a pname lookup"
        )
        assert "firefox-esr" not in result
        assert "Package: firefox" in result

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_signals_pname_ambiguity(self, mock_channels, mock_es):
        """When only a pname match is possible and multiple attrs share it, flag it."""
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.side_effect = [
            [],  # attr lookup: miss
            [
                {
                    "_source": {
                        "package_pname": "chicken-srfi",
                        "package_attr_name": "chickenPackages_5.chickenEggs.srfi-1",
                        "package_pversion": "1",
                    }
                },
                {
                    "_source": {
                        "package_pname": "chicken-srfi",
                        "package_attr_name": "chickenPackages_5.chickenEggs.srfi-2",
                        "package_pversion": "2",
                    }
                },
            ],
        ]

        result = _info_nixos("chicken-srfi", "package", "unstable")

        assert "pname shared by multiple packages" in result
        assert "chickenPackages_5.chickenEggs.srfi-1" in result
        assert "chickenPackages_5.chickenEggs.srfi-2" in result
        assert "disambiguate" in result
        # The retry hint must be a copy-pasteable JSON object, not a pseudo-call.
        # The hint picks one of the "other" attrs (not the chosen one) to disambiguate to.
        assert '"action": "info"' in result
        assert '"query": "chickenPackages_5.chickenEggs.srfi-2"' in result

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_ambiguity_tiebreak_is_deterministic(self, mock_channels, mock_es):
        """When no canonical exists, the chosen attr must be deterministic across ES orderings."""
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}

        def candidates(order: list[str]) -> list[dict]:
            return [
                {"_source": {"package_pname": "chicken-srfi", "package_attr_name": a, "package_pversion": "1"}}
                for a in order
            ]

        # ES returns the hits in one order the first time, reversed the second.
        # The tie-break must select the same attribute regardless.
        mock_es.side_effect = [
            [],
            candidates(["chickenPackages_5.chickenEggs.srfi-2", "chickenPackages_5.chickenEggs.srfi-1"]),
            [],
            candidates(["chickenPackages_5.chickenEggs.srfi-1", "chickenPackages_5.chickenEggs.srfi-2"]),
        ]
        r1 = _info_nixos("chicken-srfi", "package", "unstable")
        r2 = _info_nixos("chicken-srfi", "package", "unstable")
        # Both calls must agree on the chosen attribute (alphabetically first).
        assert "Attribute: chickenPackages_5.chickenEggs.srfi-1" in r1
        assert "Attribute: chickenPackages_5.chickenEggs.srfi-1" in r2

    @patch("mcp_nixos.sources.nixos.es_query")
    @patch("mcp_nixos.sources.nixos.get_channels")
    @pytest.mark.asyncio
    async def test_info_no_ambiguity_note_for_single_pname_hit(self, mock_channels, mock_es):
        """A single pname hit with no attr match must not emit the disambiguation note."""
        from mcp_nixos.sources.nixos import _info_nixos

        mock_channels.return_value = {"unstable": "nixos-unstable"}
        mock_es.side_effect = [
            [],
            [
                {
                    "_source": {
                        "package_pname": "qt6ct",
                        "package_attr_name": "kdePackages.qt6ct",
                        "package_pversion": "0.11",
                    }
                }
            ],
        ]

        result = _info_nixos("qt6ct", "package", "unstable")
        assert "pname shared by multiple packages" not in result
        assert "kdePackages.qt6ct" in result


@pytest.mark.unit
class TestChannelRevisions:
    """GitHub #146: action=channels surfaces nixpkgs HEAD commit per channel."""

    def test_commit_extracted_from_unstable_index_name(self):
        """When the ES index name embeds a 40-char hex commit, it is reported as indexed."""
        from mcp_nixos.sources.base import _channel_revision

        rev, source = _channel_revision(
            "unstable",
            "nixos-46-unstable-b12141ef619e0a9c1c84dc8c684040326f27cdcc",
            {"unstable": "nixos-46-unstable-b12141ef619e0a9c1c84dc8c684040326f27cdcc"},
        )
        assert rev == "b12141ef619e0a9c1c84dc8c684040326f27cdcc"
        assert source == "indexed"

    def test_list_channels_labels_indexed_revision(self):
        """When the SHA is embedded in the index, label it as 'Revision (indexed)'."""
        from unittest.mock import patch

        from mcp_nixos.sources.base import _list_channels

        fake_channels = {
            "unstable": "nixos-46-unstable-b12141ef619e0a9c1c84dc8c684040326f27cdcc",
        }
        with (
            patch("mcp_nixos.sources.base.get_channels", return_value=fake_channels),
            patch("mcp_nixos.sources.base.channel_cache") as mock_cache,
        ):
            mock_cache.using_fallback = False
            mock_cache.get_available.return_value = {
                "nixos-46-unstable-b12141ef619e0a9c1c84dc8c684040326f27cdcc": "1,000 documents"
            }
            result = _list_channels()

        channels_block = result.split("Note:", 1)[0]
        assert "Revision (indexed): b12141ef619e0a9c1c84dc8c684040326f27cdcc" in channels_block
        assert "Branch: nixos-unstable" in channels_block
        # Must NOT mislabel an indexed commit as a branch HEAD in the channel entry.
        assert "Branch HEAD" not in channels_block

    def test_list_channels_labels_branch_head_when_not_indexed(self):
        """For release channels we can only look up branch HEAD — label it honestly."""
        import time
        from unittest.mock import patch

        from mcp_nixos.sources.base import _BRANCH_REVS, _list_channels

        _BRANCH_REVS.clear()
        _BRANCH_REVS["nixos-25.11"] = ("abc1234abc1234abc1234abc1234abc1234abcd", time.monotonic())
        fake_channels = {"25.11": "latest-46-nixos-25.11"}
        try:
            with (
                patch("mcp_nixos.sources.base.get_channels", return_value=fake_channels),
                patch("mcp_nixos.sources.base.channel_cache") as mock_cache,
            ):
                mock_cache.using_fallback = False
                mock_cache.get_available.return_value = {"latest-46-nixos-25.11": "100,000 documents"}
                result = _list_channels()
        finally:
            _BRANCH_REVS.clear()

        channels_block = result.split("Note:", 1)[0]
        assert "Branch: nixos-25.11" in channels_block
        assert "Branch HEAD: abc1234abc1234abc1234abc1234abc1234abcd" in channels_block
        assert "may be ahead of indexed data" in channels_block
        # Must NOT imply this is the indexed commit in the channel entry.
        assert "Revision (indexed)" not in channels_block

    def test_branch_rev_cache_respects_ttl(self):
        """A stale entry past the TTL must trigger a re-fetch (CodeRabbit/Copilot review)."""
        import time
        from unittest.mock import MagicMock, patch

        from mcp_nixos.sources import base as base_mod

        base_mod._BRANCH_REVS.clear()
        # Seed a stale entry: timestamp is well past the TTL relative to now.
        # Using a large negative offset rather than 0.0 so the test works in
        # fresh processes where time.monotonic() starts near zero.
        stale_ts = time.monotonic() - (base_mod._BRANCH_REV_TTL * 10)
        base_mod._BRANCH_REVS["nixos-25.11"] = ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", stale_ts)
        try:
            fake_response = MagicMock()
            fake_response.status_code = 200
            fake_response.json.return_value = {"sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
            with patch("mcp_nixos.sources.base.requests.get", return_value=fake_response) as mock_get:
                rev, source = base_mod._channel_revision(
                    "25.11", "latest-46-nixos-25.11", {"25.11": "latest-46-nixos-25.11"}
                )
            assert rev == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            assert source == "branch_head"
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["headers"]["User-Agent"].startswith("mcp-nixos/")
        finally:
            base_mod._BRANCH_REVS.clear()

    def test_branch_rev_invalid_json_response_falls_back(self):
        """A 200 with a non-JSON body must be treated as a miss, not crash the listing."""
        import time
        from unittest.mock import MagicMock, patch

        from mcp_nixos.sources import base as base_mod

        base_mod._BRANCH_REVS.clear()
        # Prior stale cache entry — we should return it on the fallback path.
        base_mod._BRANCH_REVS["nixos-25.11"] = (
            "ddddddddddddddddddddddddddddddddddddddd0",
            time.monotonic() - (base_mod._BRANCH_REV_TTL * 10),
        )
        try:
            fake_response = MagicMock()
            fake_response.status_code = 200
            fake_response.json.side_effect = ValueError("not json")
            with patch("mcp_nixos.sources.base.requests.get", return_value=fake_response):
                rev, source = base_mod._channel_revision(
                    "25.11", "latest-46-nixos-25.11", {"25.11": "latest-46-nixos-25.11"}
                )
            # Must not raise; falls back to stale cached value.
            assert rev == "ddddddddddddddddddddddddddddddddddddddd0"
            assert source == "branch_head"
        finally:
            base_mod._BRANCH_REVS.clear()

    def test_branch_rev_cache_serves_within_ttl(self):
        """A fresh cached entry must NOT trigger a network call."""
        import time
        from unittest.mock import patch

        from mcp_nixos.sources import base as base_mod

        base_mod._BRANCH_REVS.clear()
        base_mod._BRANCH_REVS["nixos-25.11"] = ("cccccccccccccccccccccccccccccccccccccccc", time.monotonic())
        try:
            with patch("mcp_nixos.sources.base.requests.get") as mock_get:
                rev, source = base_mod._channel_revision(
                    "25.11", "latest-46-nixos-25.11", {"25.11": "latest-46-nixos-25.11"}
                )
            assert rev == "cccccccccccccccccccccccccccccccccccccccc"
            assert source == "branch_head"
            mock_get.assert_not_called()
        finally:
            base_mod._BRANCH_REVS.clear()


@pytest.mark.unit
class TestServerInstructions:
    """GitHub #146: the MCP server must surface instructions prose to clients."""

    def test_server_has_instructions(self):
        from mcp_nixos.server import mcp

        instructions = getattr(mcp, "instructions", "") or ""
        assert "nixpkgs" in instructions.lower()
        assert "nix_versions" in instructions

    def test_server_instructions_use_json_call_shapes(self):
        """Recipe examples must match the JSON-object shape models actually send."""
        from mcp_nixos.server import mcp

        instructions = getattr(mcp, "instructions", "") or ""
        # The quoted JSON object form is what hosts serialize — the bare
        # `nix(action=...)` pseudo-call form would teach models a syntax that
        # does not work over MCP.
        assert '{"action":"info","query":"X","channel":"Y"}' in instructions
        assert '{"action":"channels"}' in instructions
        assert "action=" not in instructions.replace('"action":', "")


class TestNixVersionsValidation:
    """Test input validation for nix_versions tool."""

    @pytest.mark.asyncio
    async def test_empty_package(self):
        result = await nix_versions_fn(package="")
        assert "Error" in result
        assert "Package name required" in result

    @pytest.mark.asyncio
    async def test_whitespace_package(self):
        result = await nix_versions_fn(package="   ")
        assert "Error" in result
        assert "Package name required" in result

    @pytest.mark.asyncio
    async def test_invalid_package_name(self):
        result = await nix_versions_fn(package="invalid<>package")
        assert "Error" in result
        assert "Invalid package name" in result

    @pytest.mark.asyncio
    async def test_limit_too_low(self):
        result = await nix_versions_fn(package="python", limit=0)
        assert "Error" in result
        assert "1-50" in result

    @pytest.mark.asyncio
    async def test_limit_too_high(self):
        result = await nix_versions_fn(package="python", limit=100)
        assert "Error" in result
        assert "1-50" in result


class TestNixVersionsAPI:
    """Test nix_versions API interactions."""

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns array of version records
        mock_resp.json.return_value = [
            {
                "name": "python",
                "version": "3.12.0",
                "commit_hash": "abc123def456abc123def456abc123def456abcd",
                "platforms": ["x86_64-linux"],
                "last_updated": 1705320000,
                "systems": {"x86_64-linux": {"attr_paths": ["python312"]}},
            },
            {
                "name": "python",
                "version": "3.11.0",
                "commit_hash": "def456abc123def456abc123def456abc123defg",
                "platforms": ["x86_64-linux"],
                "last_updated": 1705200000,
                "systems": {},
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        assert "Package: python" in result
        assert "3.12.0" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_find_specific_version(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns array
        mock_resp.json.return_value = [
            {
                "name": "python",
                "version": "3.12.0",
                "commit_hash": "a" * 40,
                "platforms": ["x86_64-linux"],
                "last_updated": 1705320000,
                "systems": {"x86_64-linux": {"attr_paths": ["python312"]}},
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python", version="3.12.0")
        assert "Found python version 3.12.0" in result
        assert "commit" in result.lower()

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_version_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns array
        mock_resp.json.return_value = [
            {
                "name": "python",
                "version": "3.12.0",
                "platforms": ["x86_64-linux"],
                "last_updated": 1705320000,
                "systems": {},
            }
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python", version="2.7.0")
        assert "not found" in result.lower()
        assert "3.12.0" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_package_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="nonexistent-package-xyz")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_service_error(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "SERVICE_ERROR" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_timeout(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout()

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_network_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        result = await nix_versions_fn(package="python")
        assert "Error" in result
        assert "API_ERROR" in result  # Uses shared helper which returns API_ERROR

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_no_releases(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns empty array for no versions
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="python")
        # Empty array means package not found in new format
        assert "Error" in result or "not found" in result.lower()


class TestNixvimSearch:
    """Test nix tool search action for Nixvim source."""

    @patch("mcp_nixos.server._search_nixvim")
    @pytest.mark.asyncio
    async def test_search_nixvim(self, mock_search):
        mock_search.return_value = "Found telescope options"
        result = await nix_fn(action="search", query="telescope", source="nixvim")
        assert result == "Found telescope options"
        mock_search.assert_called_once_with("telescope", 20)

    @patch("mcp_nixos.server._search_nixvim")
    @pytest.mark.asyncio
    async def test_search_nixvim_with_limit(self, mock_search):
        mock_search.return_value = "Found 5 options"
        result = await nix_fn(action="search", query="lsp", source="nixvim", limit=5)
        assert result == "Found 5 options"
        mock_search.assert_called_once_with("lsp", 5)


class TestNixvimInfo:
    """Test nix tool info action for Nixvim source."""

    @patch("mcp_nixos.server._info_nixvim")
    @pytest.mark.asyncio
    async def test_info_nixvim(self, mock_info):
        mock_info.return_value = "Nixvim Option: plugins.telescope.enable"
        result = await nix_fn(action="info", query="plugins.telescope.enable", source="nixvim")
        assert result == "Nixvim Option: plugins.telescope.enable"
        mock_info.assert_called_once_with("plugins.telescope.enable")


class TestNixvimStats:
    """Test nix tool stats action for Nixvim source."""

    @patch("mcp_nixos.server._stats_nixvim")
    @pytest.mark.asyncio
    async def test_stats_nixvim(self, mock_stats):
        mock_stats.return_value = "Nixvim Statistics:\n* Total options: 5,000"
        result = await nix_fn(action="stats", source="nixvim")
        assert result == "Nixvim Statistics:\n* Total options: 5,000"
        mock_stats.assert_called_once()


class TestNixvimOptions:
    """Test nix tool options action for Nixvim source."""

    @patch("mcp_nixos.server._browse_nixvim_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_categories(self, mock_browse):
        mock_browse.return_value = "Nixvim option categories"
        result = await nix_fn(action="options", source="nixvim", query="")
        assert result == "Nixvim option categories"
        mock_browse.assert_called_once_with("")

    @patch("mcp_nixos.server._browse_nixvim_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_with_prefix(self, mock_browse):
        mock_browse.return_value = "Nixvim options with prefix 'plugins'"
        result = await nix_fn(action="options", source="nixvim", query="plugins")
        assert result == "Nixvim options with prefix 'plugins'"
        mock_browse.assert_called_once_with("plugins")


@pytest.mark.unit
class TestNixvimInternalFunctions:
    """Test Nixvim internal functions with mocked data."""

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_search_nixvim_finds_matches(self, mock_get_options):
        from mcp_nixos.server import _search_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": "Telescope settings"},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": "Enable LSP"},
        ]
        result = _search_nixvim("telescope", 10)
        assert "Found 2 Nixvim options" in result
        assert "plugins.telescope.enable" in result
        assert "plugins.telescope.settings" in result
        assert "plugins.lsp.enable" not in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_search_nixvim_no_matches(self, mock_get_options):
        from mcp_nixos.server import _search_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
        ]
        result = _search_nixvim("nonexistent", 10)
        assert "No Nixvim options found" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_info_nixvim_exact_match(self, mock_get_options):
        from mcp_nixos.server import _info_nixvim

        mock_get_options.return_value = [
            {
                "name": "plugins.telescope.enable",
                "type": "boolean",
                "description": "<p>Enable telescope</p>",
                "default": "<code>false</code>",
                "declarations": ["https://github.com/nix-community/nixvim/blob/main/plugins/telescope.nix"],
            },
        ]
        result = _info_nixvim("plugins.telescope.enable")
        assert "Nixvim Option: plugins.telescope.enable" in result
        assert "Type: boolean" in result
        assert "Enable telescope" in result
        assert "Default: false" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_info_nixvim_not_found(self, mock_get_options):
        from mcp_nixos.server import _info_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
        ]
        result = _info_nixvim("nonexistent.option")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_stats_nixvim(self, mock_get_options):
        from mcp_nixos.server import _stats_nixvim

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": ""},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": ""},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": ""},
            {"name": "colorschemes.catppuccin.enable", "type": "boolean", "description": ""},
        ]
        result = _stats_nixvim()
        assert "Nixvim Statistics:" in result
        assert "Total options: 4" in result
        assert "Categories: 2" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_categories(self, mock_get_options):
        from mcp_nixos.server import _browse_nixvim_options

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": ""},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": ""},
            {"name": "colorschemes.catppuccin.enable", "type": "boolean", "description": ""},
        ]
        result = _browse_nixvim_options("")
        assert "Nixvim option categories" in result
        assert "plugins (2 options)" in result
        assert "colorschemes (1 options)" in result

    @patch("mcp_nixos.server.nixvim_cache.get_options")
    @pytest.mark.asyncio
    async def test_browse_nixvim_with_prefix(self, mock_get_options):
        from mcp_nixos.server import _browse_nixvim_options

        mock_get_options.return_value = [
            {"name": "plugins.telescope.enable", "type": "boolean", "description": "Enable telescope"},
            {"name": "plugins.telescope.settings", "type": "attrs", "description": "Settings"},
            {"name": "plugins.lsp.enable", "type": "boolean", "description": "Enable LSP"},
        ]
        result = _browse_nixvim_options("plugins.telescope")
        assert "Nixvim options with prefix 'plugins.telescope'" in result
        assert "plugins.telescope.enable" in result
        assert "plugins.telescope.settings" in result
        assert "plugins.lsp.enable" not in result


@pytest.mark.unit
class TestFlakeHubInternalFunctions:
    """Test FlakeHub internal functions with mocked API responses."""

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_search_flakehub_success(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {
                "org": "NixOS",
                "project": "nixpkgs",
                "description": "A collection of packages",
                "labels": ["nixpkgs", "nix"],
            },
            {
                "org": "nix-community",
                "project": "home-manager",
                "description": "Manage user environment",
                "labels": ["home-manager"],
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("nix", 10)
        assert "Found 2 flakes on FlakeHub" in result
        assert "NixOS/nixpkgs" in result
        assert "nix-community/home-manager" in result
        assert "flakehub.com/flake/NixOS/nixpkgs" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_search_flakehub_no_results(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("nonexistent", 10)
        assert "No flakes found on FlakeHub" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_search_flakehub_normalizes_whitespace(self, mock_get):
        from mcp_nixos.server import _search_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {
                "org": "test",
                "project": "flake",
                "description": "  Description\n\twith\n  whitespace  ",
                "labels": [],
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_flakehub("test", 10)
        assert "Description with whitespace" in result
        assert "\n\t" not in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_search_flakehub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _search_flakehub

        mock_get.side_effect = requests.Timeout()

        result = _search_flakehub("test", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_info_flakehub_success(self, mock_get):
        from mcp_nixos.server import _info_flakehub

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "description": "A collection of packages",
            "simplified_version": "0.2511.123456",
            "revision": "abc123def456",
            "commit_count": 900000,
            "visibility": "public",
            "published_at": "2025-01-01T12:00:00Z",
            "mirrored": True,
            "pretty_download_url": "https://flakehub.com/f/NixOS/nixpkgs/0.2511.123456.tar.gz",
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_flakehub("NixOS/nixpkgs")
        assert "FlakeHub Flake: NixOS/nixpkgs" in result
        assert "A collection of packages" in result
        assert "0.2511.123456" in result
        assert "public" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_info_flakehub_not_found(self, mock_get):
        from mcp_nixos.server import _info_flakehub

        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = _info_flakehub("nonexistent/flake")
        assert "Error" in result
        assert "NOT_FOUND" in result

    def test_info_flakehub_invalid_format(self):
        from mcp_nixos.server import _info_flakehub

        result = _info_flakehub("invalid-no-slash")
        assert "Error" in result
        assert "org/project" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_stats_flakehub_success(self, mock_get):
        from mcp_nixos.server import _stats_flakehub

        mock_resp = Mock()
        mock_resp.json.return_value = [
            {"org": "NixOS", "project": "nixpkgs", "labels": ["nix", "nixos"]},
            {"org": "NixOS", "project": "nix", "labels": ["nix"]},
            {"org": "nix-community", "project": "home-manager", "labels": ["nix"]},
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _stats_flakehub()
        assert "FlakeHub Statistics:" in result
        assert "Total flakes: 3" in result
        assert "Organizations: 2" in result
        assert "NixOS" in result

    @patch("mcp_nixos.sources.flakehub.requests.get")
    def test_stats_flakehub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _stats_flakehub

        mock_get.side_effect = requests.Timeout()

        result = _stats_flakehub()
        assert "Error" in result
        assert "TIMEOUT" in result


@pytest.mark.unit
class TestNixToolWikiSource:
    """Test nix tool search/info for wiki source."""

    @patch("mcp_nixos.server._search_wiki")
    @pytest.mark.asyncio
    async def test_search_wiki(self, mock_search):
        """Test wiki search delegates correctly."""
        mock_search.return_value = "Found 5 wiki articles matching 'nvidia':\n\n* Nvidia\n..."
        result = await nix_fn(action="search", query="nvidia", source="wiki", limit=5)
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("nvidia", 5)

    @patch("mcp_nixos.server._search_wiki")
    @pytest.mark.asyncio
    async def test_search_wiki_default_limit(self, mock_search):
        """Test wiki search uses default limit."""
        mock_search.return_value = "Found results"
        result = await nix_fn(action="search", query="flakes", source="wiki")
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("flakes", 20)

    @patch("mcp_nixos.server._info_wiki")
    @pytest.mark.asyncio
    async def test_info_wiki(self, mock_info):
        """Test wiki info delegates correctly."""
        mock_info.return_value = "Wiki: Flakes\nURL: https://wiki.nixos.org/wiki/Flakes\n..."
        result = await nix_fn(action="info", query="Flakes", source="wiki")
        assert result == mock_info.return_value
        mock_info.assert_called_once_with("Flakes")


@pytest.mark.unit
class TestNixToolNixDevSource:
    """Test nix tool search for nix-dev source."""

    @patch("mcp_nixos.server._search_nixdev")
    @pytest.mark.asyncio
    async def test_search_nixdev(self, mock_search):
        """Test nix-dev search delegates correctly."""
        mock_search.return_value = "Found 3 nix.dev docs matching 'flakes':\n..."
        result = await nix_fn(action="search", query="flakes", source="nix-dev", limit=10)
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("flakes", 10)

    @patch("mcp_nixos.server._search_nixdev")
    @pytest.mark.asyncio
    async def test_search_nixdev_default_limit(self, mock_search):
        """Test nix-dev search uses default limit."""
        mock_search.return_value = "Found docs"
        result = await nix_fn(action="search", query="packaging", source="nix-dev")
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("packaging", 20)

    @patch("mcp_nixos.server._info_nixdev")
    @pytest.mark.asyncio
    async def test_info_nixdev_delegates(self, mock_info):
        """Test nix-dev info delegates to _info_nixdev with the docname."""
        mock_info.return_value = "Title: Flakes\nSource: https://nix.dev/concepts/flakes.html\n\n# Flakes\n"
        result = await nix_fn(action="info", query="concepts/flakes", source="nix-dev")
        assert result == mock_info.return_value
        mock_info.assert_called_once_with("concepts/flakes")

    @pytest.mark.asyncio
    async def test_stats_wiki_not_supported(self):
        """Test wiki stats returns helpful message."""
        result = await nix_fn(action="stats", source="wiki")
        assert "Error" in result
        assert "not available" in result.lower()

    @pytest.mark.asyncio
    async def test_stats_nixdev_not_supported(self):
        """Test nix-dev stats returns helpful message."""
        result = await nix_fn(action="stats", source="nix-dev")
        assert "Error" in result
        assert "not available" in result.lower()


@pytest.mark.unit
class TestInfoNixDev:
    """Unit tests for _info_nixdev: verifies URL shape, normalization, and guards.

    We mock requests.get so no real network is hit. Integration tests live in
    tests/test_integration.py.
    """

    _SAMPLE_MD = (
        "(reading-nix-language)=\n\n"
        "# Nix language basics\n\n"
        "The Nix language is designed for conveniently creating derivations.\n"
    )

    @staticmethod
    def _mock_response(status_code: int, body: str) -> Mock:
        """Build a streaming-aware mock of `requests.Response`.

        `_info_nixdev` uses `stream=True` + `iter_content(chunk_size=...)`,
        not `.text`. Provide an iter_content that yields the body as 8 KB
        byte chunks so the size-cap path in the implementation runs as it
        would against a real response.
        """
        body_bytes = body.encode("utf-8")
        resp = Mock()
        resp.status_code = status_code
        resp.raise_for_status = Mock()
        resp.close = Mock()

        def iter_content(chunk_size: int = 8192):
            for i in range(0, len(body_bytes), chunk_size):
                yield body_bytes[i : i + chunk_size]

        resp.iter_content = iter_content
        return resp

    @patch("mcp_nixos.sources.nixdev.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixdev_docname(self, mock_get):
        """Happy path: docname input returns markdown with title header."""
        mock_get.return_value = self._mock_response(200, self._SAMPLE_MD)

        result = await nix_fn(action="info", query="tutorials/nix-language", source="nix-dev")

        # Verify the URL shape we hit
        call_url = mock_get.call_args[0][0]
        assert call_url == "https://nix.dev/_sources/tutorials/nix-language.md"

        assert "Title: Nix language basics" in result
        assert "Source: https://nix.dev/tutorials/nix-language.html" in result
        assert "Docname: tutorials/nix-language" in result
        assert "# Nix language basics" in result

    @patch("mcp_nixos.sources.nixdev.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixdev_full_html_url(self, mock_get):
        """Full .html URL is normalized to the docname before fetching."""
        mock_get.return_value = self._mock_response(200, self._SAMPLE_MD)

        result = await nix_fn(
            action="info",
            query="https://nix.dev/tutorials/nix-language.html",
            source="nix-dev",
        )

        call_url = mock_get.call_args[0][0]
        assert call_url == "https://nix.dev/_sources/tutorials/nix-language.md"
        assert "Docname: tutorials/nix-language" in result

    @patch("mcp_nixos.sources.nixdev.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixdev_404(self, mock_get):
        """404 returns NOT_FOUND with the normalized docname."""
        mock_get.return_value = self._mock_response(404, "<html>not found</html>")

        result = await nix_fn(action="info", query="does/not/exist", source="nix-dev")
        assert "NOT_FOUND" in result
        assert "does/not/exist" in result

    @pytest.mark.asyncio
    async def test_info_nixdev_path_traversal_rejected(self):
        """Path traversal attempts are rejected before any network call."""
        with patch("mcp_nixos.sources.nixdev.requests.get") as mock_get:
            result = await nix_fn(action="info", query="../../etc/passwd", source="nix-dev")
            assert "Error" in result
            assert "traversal" in result.lower()
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_info_nixdev_percent_encoded_traversal_rejected(self):
        """Percent-encoded traversal (%2e%2e/%2e%2e/...) must also be rejected."""
        with patch("mcp_nixos.sources.nixdev.requests.get") as mock_get:
            result = await nix_fn(
                action="info",
                query="%2e%2e/%2e%2e/etc/passwd",
                source="nix-dev",
            )
            assert "Error" in result
            assert "traversal" in result.lower()
            mock_get.assert_not_called()

    @patch("mcp_nixos.sources.nixdev.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixdev_truncation(self, mock_get):
        """Responses above the size cap are truncated with a marker.

        Also verifies the streaming path: the mock yields bytes via
        `iter_content`, never `.text`, so the implementation must be
        reading from the stream rather than materializing the whole
        response.
        """
        big_body = "# Big Doc\n\n" + ("x" * (250 * 1024))
        resp = self._mock_response(200, big_body)
        mock_get.return_value = resp

        result = await nix_fn(action="info", query="big/doc", source="nix-dev")
        assert "[truncated]" in result
        assert len(result.encode("utf-8")) < len(big_body.encode("utf-8"))
        # Confirm we used the streaming API, not `.text`.
        _, kwargs = mock_get.call_args
        assert kwargs.get("stream") is True

    @patch("mcp_nixos.sources.nixdev.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixdev_network_error(self, mock_get):
        """Network errors degrade gracefully to a plain-text error."""
        import requests as _requests

        mock_get.side_effect = _requests.ConnectionError("boom")

        result = await nix_fn(action="info", query="tutorials/nix-language", source="nix-dev")
        assert "Error" in result
        assert "API_ERROR" in result

    @pytest.mark.asyncio
    async def test_info_nixdev_empty_query(self):
        """Empty query is rejected by the outer nix tool (before the source dispatch)."""
        result = await nix_fn(action="info", query="", source="nix-dev")
        assert "Error" in result


@pytest.mark.unit
class TestNixToolNoogleSource:
    """Test nix tool search/info/stats/options for noogle source."""

    @patch("mcp_nixos.server._search_noogle")
    @pytest.mark.asyncio
    async def test_search_noogle(self, mock_search):
        """Test noogle search delegates correctly."""
        mock_search.return_value = "Found 5 Noogle functions matching 'mapAttrs':\n..."
        result = await nix_fn(action="search", query="mapAttrs", source="noogle", limit=5)
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("mapAttrs", 5)

    @patch("mcp_nixos.server._info_noogle")
    @pytest.mark.asyncio
    async def test_info_noogle(self, mock_info):
        """Test noogle info delegates correctly."""
        mock_info.return_value = "Noogle Function: lib.attrsets.mapAttrs\nType: ..."
        result = await nix_fn(action="info", query="lib.attrsets.mapAttrs", source="noogle")
        assert result == mock_info.return_value
        mock_info.assert_called_once_with("lib.attrsets.mapAttrs")

    @patch("mcp_nixos.server._stats_noogle")
    @pytest.mark.asyncio
    async def test_stats_noogle(self, mock_stats):
        """Test noogle stats delegates correctly."""
        mock_stats.return_value = "Noogle Statistics:\n- Total functions: 2000\n..."
        result = await nix_fn(action="stats", source="noogle")
        assert result == mock_stats.return_value
        mock_stats.assert_called_once()

    @patch("mcp_nixos.server._browse_noogle_options")
    @pytest.mark.asyncio
    async def test_options_noogle(self, mock_browse):
        """Test noogle options delegates correctly."""
        mock_browse.return_value = "Noogle functions with prefix 'lib.strings':\n..."
        result = await nix_fn(action="options", source="noogle", query="lib.strings")
        assert result == mock_browse.return_value
        mock_browse.assert_called_once_with("lib.strings")


@pytest.mark.unit
class TestStripHtml:
    """Test HTML stripping utility."""

    def test_strip_html_basic(self):
        from mcp_nixos.server import strip_html

        assert strip_html("<p>Hello world</p>") == "Hello world"

    def test_strip_html_nested(self):
        from mcp_nixos.server import strip_html

        assert strip_html("<p><code>foo</code> bar</p>") == "foo bar"

    def test_strip_html_empty(self):
        from mcp_nixos.server import strip_html

        assert strip_html("") == ""
        assert strip_html(None) == ""

    def test_strip_html_spans(self):
        from mcp_nixos.server import strip_html

        html = '<span class="code">value</span>'
        assert strip_html(html) == "value"


@pytest.mark.unit
class TestPlainTextOutput:
    """Verify MCP tools return plain text."""

    @pytest.mark.asyncio
    async def test_nix_error_no_xml(self):
        result = await nix_fn(action="invalid")
        assert "<error>" not in result
        assert "</error>" not in result

    @pytest.mark.asyncio
    async def test_nix_versions_error_no_xml(self):
        result = await nix_versions_fn(package="")
        assert "<error>" not in result
        assert "</error>" not in result


@pytest.mark.unit
class TestNixToolCacheAction:
    """Test nix tool cache action for checking binary cache status."""

    @pytest.mark.asyncio
    async def test_cache_requires_query(self):
        """Test cache action requires package name."""
        result = await nix_fn(action="cache", query="")
        assert "Error" in result
        assert "Package name required" in result

    @patch("mcp_nixos.server._check_binary_cache")
    @pytest.mark.asyncio
    async def test_cache_delegates_correctly(self, mock_cache):
        """Test cache action delegates to _check_binary_cache."""
        mock_cache.return_value = "Binary Cache Status: firefox@147.0.1\n..."
        result = await nix_fn(action="cache", query="firefox")
        assert result == mock_cache.return_value
        mock_cache.assert_called_once_with("firefox", "latest", "")

    @patch("mcp_nixos.server._check_binary_cache")
    @pytest.mark.asyncio
    async def test_cache_with_version(self, mock_cache):
        """Test cache action with specific version."""
        mock_cache.return_value = "Binary Cache Status: hello@2.12\n..."
        result = await nix_fn(action="cache", query="hello", version="2.12")
        assert result == mock_cache.return_value
        mock_cache.assert_called_once_with("hello", "2.12", "")

    @patch("mcp_nixos.server._check_binary_cache")
    @pytest.mark.asyncio
    async def test_cache_with_system(self, mock_cache):
        """Test cache action with specific system."""
        mock_cache.return_value = "Binary Cache Status: ripgrep@15.1.0\n..."
        result = await nix_fn(action="cache", query="ripgrep", system="x86_64-linux")
        assert result == mock_cache.return_value
        mock_cache.assert_called_once_with("ripgrep", "latest", "x86_64-linux")


@pytest.mark.unit
class TestBinaryCacheInternalFunctions:
    """Test binary cache internal functions with mocked API responses."""

    @patch("mcp_nixos.sources.nixhub.requests.head")
    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_check_binary_cache_cached(self, mock_get, mock_head):
        """Test _check_binary_cache when package is cached."""
        from mcp_nixos.server import _check_binary_cache

        # Mock NixHub v2/resolve API - systems is a dict with outputs array
        resolve_resp = Mock()
        resolve_resp.status_code = 200
        resolve_resp.json.return_value = {
            "name": "hello",
            "version": "2.12",
            "systems": {
                "x86_64-linux": {
                    "outputs": [
                        {
                            "name": "out",
                            "path": "/nix/store/abcdefghijklmnopqrstuvwxyz012345-hello-2.12",
                            "default": True,
                        }
                    ]
                },
            },
        }
        resolve_resp.raise_for_status = Mock()

        # Mock cache.nixos.org narinfo
        narinfo_head = Mock()
        narinfo_head.status_code = 200

        narinfo_resp = Mock()
        narinfo_resp.status_code = 200
        narinfo_resp.text = "StorePath: /nix/store/abc...\nFileSize: 100000\nNarSize: 500000\nCompression: xz"

        mock_get.side_effect = [resolve_resp, narinfo_resp]
        mock_head.return_value = narinfo_head

        result = await _check_binary_cache("hello", "2.12")
        assert "Binary Cache Status" in result
        assert "hello@2.12" in result
        assert "CACHED" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_check_binary_cache_not_found(self, mock_get):
        """Test _check_binary_cache when package not found on NixHub."""
        from mcp_nixos.server import _check_binary_cache

        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = await _check_binary_cache("nonexistent-package")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_check_binary_cache_timeout(self, mock_get):
        """Test _check_binary_cache when NixHub times out."""
        import requests
        from mcp_nixos.server import _check_binary_cache

        mock_get.side_effect = requests.Timeout()

        result = await _check_binary_cache("hello")
        assert "Error" in result
        assert "TIMEOUT" in result


@pytest.mark.unit
class TestNixToolNixHubSource:
    """Test nix tool search/info for nixhub source."""

    @patch("mcp_nixos.server._search_nixhub")
    @pytest.mark.asyncio
    async def test_search_nixhub(self, mock_search):
        """Test nixhub search delegates correctly."""
        mock_search.return_value = "Found 5 packages on NixHub matching 'python':\n..."
        result = await nix_fn(action="search", query="python", source="nixhub", limit=5)
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("python", 5)

    @patch("mcp_nixos.server._search_nixhub")
    @pytest.mark.asyncio
    async def test_search_nixhub_default_limit(self, mock_search):
        """Test nixhub search uses default limit."""
        mock_search.return_value = "Found packages"
        result = await nix_fn(action="search", query="nodejs", source="nixhub")
        assert result == mock_search.return_value
        mock_search.assert_called_once_with("nodejs", 20)

    @patch("mcp_nixos.server._info_nixhub")
    @pytest.mark.asyncio
    async def test_info_nixhub(self, mock_info):
        """Test nixhub info delegates correctly."""
        mock_info.return_value = "Package: ripgrep\nVersion: 15.1.0\n..."
        result = await nix_fn(action="info", query="ripgrep", source="nixhub")
        assert result == mock_info.return_value
        mock_info.assert_called_once_with("ripgrep")

    @pytest.mark.asyncio
    async def test_stats_nixhub_not_supported(self):
        """Test nixhub stats returns helpful message."""
        result = await nix_fn(action="stats", source="nixhub")
        assert "Error" in result
        assert "not available" in result.lower()


@pytest.mark.unit
class TestNixHubInternalFunctions:
    """Test NixHub internal functions with mocked API responses."""

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_search_nixhub_success(self, mock_get):
        from mcp_nixos.server import _search_nixhub

        mock_resp = Mock()
        mock_resp.status_code = 200
        # v2/search returns {"query": ..., "total_results": N, "results": [...]}
        mock_resp.json.return_value = {
            "query": "python",
            "total_results": 2,
            "results": [
                {
                    "name": "python",
                    "summary": "A programming language",
                    "last_updated": "2025-01-15T12:00:00Z",
                },
                {
                    "name": "python311",
                    "summary": "Python 3.11",
                },
            ],
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await _search_nixhub("python", 10)
        assert "Found 2 of 2 packages on NixHub" in result
        assert "python" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_search_nixhub_no_results(self, mock_get):
        from mcp_nixos.server import _search_nixhub

        mock_resp = Mock()
        mock_resp.status_code = 200
        # v2/search returns empty results array
        mock_resp.json.return_value = {"query": "nonexistent", "total_results": 0, "results": []}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await _search_nixhub("nonexistent", 10)
        assert "No packages found on NixHub" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_search_nixhub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _search_nixhub

        mock_get.side_effect = requests.Timeout()

        result = await _search_nixhub("python", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixhub_success(self, mock_get):
        from mcp_nixos.server import _info_nixhub

        # First call: v1/pkg - returns array of version records
        pkg_resp = Mock()
        pkg_resp.status_code = 200
        pkg_resp.json.return_value = [
            {
                "name": "ripgrep",
                "version": "15.1.0",
                "summary": "Fast search tool",
                "description": "ripgrep recursively searches directories...",
                "license": "Unlicense",
                "homepage": "https://github.com/BurntSushi/ripgrep",
                "platforms": ["x86_64-linux", "aarch64-darwin"],
                "systems": {
                    "x86_64-linux": {
                        "programs": ["rg"],
                        "attr_paths": ["ripgrep"],
                    },
                },
            }
        ]
        pkg_resp.raise_for_status = Mock()

        # Second call: v2/resolve - systems is a dict with outputs array
        resolve_resp = Mock()
        resolve_resp.status_code = 200
        resolve_resp.json.return_value = {
            "name": "ripgrep",
            "version": "15.1.0",
            "systems": {
                "x86_64-linux": {
                    "flake_installable": {
                        "ref": {"type": "github", "owner": "NixOS", "repo": "nixpkgs", "rev": "a1b2c3d4"},
                        "attr_path": "ripgrep",
                    },
                    "outputs": [{"name": "out", "path": "/nix/store/abc-ripgrep-15.1.0", "default": True}],
                },
            },
        }

        mock_get.side_effect = [pkg_resp, resolve_resp]

        result = await _info_nixhub("ripgrep")
        assert "Package: ripgrep" in result
        assert "Version: 15.1.0" in result
        assert "License: Unlicense" in result
        assert "Homepage: https://github.com/BurntSushi/ripgrep" in result
        assert "Programs: rg" in result
        assert "Flake Reference:" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixhub_not_found(self, mock_get):
        from mcp_nixos.server import _info_nixhub

        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        result = await _info_nixhub("nonexistent-package")
        assert "Error" in result
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_info_nixhub_timeout(self, mock_get):
        import requests
        from mcp_nixos.server import _info_nixhub

        mock_get.side_effect = requests.Timeout()

        result = await _info_nixhub("python")
        assert "Error" in result
        assert "TIMEOUT" in result


@pytest.mark.unit
class TestNixVersionsEnhanced:
    """Test enhanced nix_versions with rich metadata."""

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_versions_includes_metadata(self, mock_get):
        """Test nix_versions includes license, homepage, programs."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns array of version records
        mock_resp.json.return_value = [
            {
                "name": "ripgrep",
                "version": "15.1.0",
                "license": "Unlicense",
                "homepage": "https://github.com/BurntSushi/ripgrep",
                "platforms": ["x86_64-linux", "aarch64-darwin"],
                "commit_hash": "a" * 40,
                "last_updated": 1705320000,  # epoch timestamp
                "systems": {
                    "x86_64-linux": {
                        "programs": ["rg"],
                        "attr_paths": ["ripgrep"],
                    },
                },
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="ripgrep")
        assert "Package: ripgrep" in result
        assert "License: Unlicense" in result
        assert "Homepage: https://github.com/BurntSushi/ripgrep" in result
        assert "Programs: rg" in result
        assert "15.1.0" in result
        assert "Platforms:" in result

    @patch("mcp_nixos.sources.nixhub.requests.get")
    @pytest.mark.asyncio
    async def test_versions_platform_summary(self, mock_get):
        """Test nix_versions shows platform summary."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        # v1/pkg returns array - platforms is array of system names
        mock_resp.json.return_value = [
            {
                "name": "hello",
                "version": "1.0.0",
                "platforms": ["x86_64-linux", "aarch64-linux", "x86_64-darwin"],
                "commit_hash": "a" * 40,
                "last_updated": 1705320000,
                "systems": {},
            },
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = await nix_versions_fn(package="hello")
        assert "Linux and macOS" in result
