"""Tests for server helper functions and internal logic."""

import time
from unittest.mock import Mock, patch

import pytest
import requests
from mcp_nixos.config import FALLBACK_CHANNELS
from mcp_nixos.server import (
    HOME_MANAGER_URL,
    NIXOS_API,
    NIXOS_AUTH,
    ChannelCache,
    error,
    es_query,
    get_channel_suggestions,
    get_channels,
    parse_html_options,
    validate_channel,
)


@pytest.mark.unit
class TestErrorFunction:
    """Test error formatting helper."""

    def test_basic_error(self):
        result = error("Test message")
        assert result == "Error (ERROR): Test message"

    def test_custom_code(self):
        result = error("Not found", "NOT_FOUND")
        assert result == "Error (NOT_FOUND): Not found"

    def test_special_characters(self):
        result = error('Error <tag> & "quotes"', "CODE")
        assert result == 'Error (CODE): Error <tag> & "quotes"'

    def test_empty_message(self):
        result = error("")
        assert result == "Error (ERROR): "


@pytest.mark.unit
class TestElasticsearchQuery:
    """Test Elasticsearch query helper."""

    @patch("mcp_nixos.sources.base.requests.post")
    def test_success(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": [{"_source": {"test": "data"}}]}}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert len(result) == 1
        assert result[0]["_source"]["test"] == "data"
        mock_post.assert_called_once_with(
            f"{NIXOS_API}/test-index/_search",
            json={"query": {"match_all": {}}, "size": 20},
            auth=NIXOS_AUTH,
            timeout=10,
        )

    @patch("mcp_nixos.sources.base.requests.post")
    def test_custom_size(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_post.return_value = mock_resp

        es_query("test-index", {"match_all": {}}, size=50)
        call_args = mock_post.call_args[1]
        assert call_args["json"]["size"] == 50

    @patch("mcp_nixos.sources.base.requests.post")
    def test_timeout(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.Timeout()
        with pytest.raises(APIError, match="Connection timed out"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.sources.base.requests.post")
    def test_request_error(self, mock_post):
        from mcp_nixos.server import APIError

        mock_post.side_effect = requests.HTTPError("HTTP error")
        with pytest.raises(APIError, match="API error"):
            es_query("test-index", {"match_all": {}})

    @patch("mcp_nixos.sources.base.requests.post")
    def test_malformed_response(self, mock_post):
        mock_resp = Mock()
        mock_resp.json.return_value = {"invalid": "structure"}
        mock_post.return_value = mock_resp

        result = es_query("test-index", {"match_all": {}})
        assert result == []


@pytest.mark.unit
class TestParseHtmlOptions:
    """Test HTML option parsing."""

    @patch("mcp_nixos.utils.requests.get")
    def test_success(self, mock_get):
        html = b"""
        <html><body>
        <dt><a id="opt-programs.git.enable">programs.git.enable</a></dt>
        <dd><p>Description</p><span class="term">Type: boolean</span></dd>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL)
        assert isinstance(result, list)

    @patch("mcp_nixos.utils.requests.get")
    def test_with_query(self, mock_get):
        html = b"""
        <html><body>
        <dt><a id="opt-programs.git.enable">programs.git.enable</a></dt>
        <dd><p>Enable git</p><span class="term">Type: boolean</span></dd>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL, query="git")
        assert isinstance(result, list)
        # Should find the git option
        assert len(result) >= 1

    @patch("mcp_nixos.utils.requests.get")
    def test_home_manager_mdbook_format(self, mock_get):
        html = b"""
        <html><body>
        <h2 id="opt-programs.git.enable">
          <a class="header" href="#opt-programs.git.enable">programs.git.enable</a>
        </h2>
        <p>Whether to enable Git.</p>
        <p><em>Type:</em> boolean</p>
        <p><em>Default:</em></p>
        <pre><code>false</code></pre>
        <p><em>Declared by:</em></p>
        <ul><li>modules/programs/git.nix</li></ul>
        <h2 id="opt-accounts.email.accounts._name_.primary">
          <a class="header" href="#opt-accounts.email.accounts._name_.primary">
            accounts.email.accounts.&lt;name&gt;.primary
          </a>
        </h2>
        <p>Whether this is the primary account.</p>
        <p><em>Type:</em> boolean</p>
        <h2 id="nixos-opt-services.test.enable">
          <a class="header">services.test.enable</a>
        </h2>
        <p>This belongs to the NixOS option catalogue.</p>
        <p><em>Type:</em> boolean</p>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL, limit=None)

        assert result == [
            {
                "name": "programs.git.enable",
                "description": "Whether to enable Git.",
                "type": "boolean",
            },
            {
                "name": "accounts.email.accounts.<name>.primary",
                "description": "Whether this is the primary account.",
                "type": "boolean",
            },
        ]

    @patch("mcp_nixos.utils.requests.get")
    def test_home_manager_mdbook_query_and_prefix(self, mock_get):
        html = b"""
        <html><body>
        <h2 id="opt-programs.git.enable"><a class="header">programs.git.enable</a></h2>
        <p>Whether to enable Git.</p><p><em>Type:</em> boolean</p>
        <h2 id="opt-services.syncthing.enable"><a class="header">services.syncthing.enable</a></h2>
        <p>Whether to enable Syncthing.</p><p><em>Type:</em> boolean</p>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options(HOME_MANAGER_URL, query="git", prefix="programs")

        assert [option["name"] for option in result] == ["programs.git.enable"]

    @patch("mcp_nixos.utils.requests.get")
    def test_mdbook_dispatch_is_structural_not_url_based(self, mock_get):
        """The mdBook parser is chosen by document structure, not by the URL."""
        html = b"""
        <html><body>
        <h2 id="opt-system.defaults.dock.autohide"><a class="header">system.defaults.dock.autohide</a></h2>
        <p>Whether to hide the dock.</p><p><em>Type:</em> boolean</p>
        </body></html>
        """
        mock_resp = Mock()
        mock_resp.content = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = parse_html_options("https://example.invalid/manual/index.html", limit=None)

        assert [option["name"] for option in result] == ["system.defaults.dock.autohide"]
        assert result[0]["type"] == "boolean"

    @patch("mcp_nixos.utils.requests.get")
    def test_timeout(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.Timeout()
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)

    @patch("mcp_nixos.utils.requests.get")
    def test_request_error(self, mock_get):
        from mcp_nixos.server import DocumentParseError

        mock_get.side_effect = requests.RequestException("Network error")
        with pytest.raises(DocumentParseError, match="Failed to fetch docs"):
            parse_html_options(HOME_MANAGER_URL)


@pytest.mark.unit
class TestChannelCache:
    """Test channel cache functionality."""

    def test_singleton_behavior(self):
        cache = ChannelCache()
        cache.available_channels = {"test": "value"}
        result = cache.get_available()
        assert result == {"test": "value"}

    @patch("mcp_nixos.caches.requests.get")
    def test_flake_index_is_discovered_from_aliases(self, mock_get):
        """The flake alias rolls forward with Hydra; pick the newest generation."""
        aliases_resp = Mock(status_code=200)
        aliases_resp.json.return_value = [
            {"alias": "latest-50-nixos-unstable"},
            {"alias": "latest-50-group-manual"},
            {"alias": "latest-51-nixos-unstable"},
            {"alias": "latest-51-group-manual"},
            {"alias": ".kibana"},
        ]
        mock_get.return_value = aliases_resp
        cache = ChannelCache()
        assert cache.get_flake_index() == "latest-51-group-manual"
        # Flake aliases must not leak into channel resolution.
        assert cache.alias_names == ["latest-50-nixos-unstable", "latest-51-nixos-unstable"]
        # Memoized: a second call does not probe again.
        assert cache.get_flake_index() == "latest-51-group-manual"
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_flake_index_falls_back_when_probe_fails(self, mock_get):
        from mcp_nixos.config import FLAKE_INDEX

        mock_get.side_effect = Exception("backend unreachable")
        cache = ChannelCache()
        assert cache.get_flake_index() == FLAKE_INDEX
        assert cache.flake_index is None

    @patch("mcp_nixos.caches.requests.get")
    def test_flake_index_falls_back_when_alias_absent(self, mock_get):
        from mcp_nixos.config import FLAKE_INDEX

        aliases_resp = Mock(status_code=200)
        aliases_resp.json.return_value = [{"alias": "latest-51-nixos-unstable"}]
        mock_get.return_value = aliases_resp
        cache = ChannelCache()
        assert cache.get_flake_index() == FLAKE_INDEX

    @patch("mcp_nixos.caches.requests.get")
    def test_resolved_channels_fallback(self, mock_get):
        mock_get.side_effect = Exception("backend unreachable")
        cache = ChannelCache()
        cache.available_channels = {}  # Empty available channels
        cache.resolved_channels = None
        result = cache.get_resolved()
        assert cache.using_fallback is True
        assert "unstable" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_fallback_is_not_memoized(self, mock_get):
        """A transient discovery failure must not poison the process.

        The fallback generations go stale — Hydra retires old aliases, and a
        retired alias 404s on every query. Caching one failed probe would make
        every later request fail too, and no amount of retrying would recover.
        """
        mock_get.side_effect = Exception("backend unreachable")
        cache = ChannelCache()
        assert cache.get_resolved() == FALLBACK_CHANNELS
        assert cache.using_fallback is True
        # Nothing cached, so the next call re-probes instead of reusing the fallback.
        assert cache.resolved_channels is None
        assert cache.available_channels is None

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_recovers_after_a_transient_failure(self, mock_get, mock_post):
        """Once the backend answers again, resolution must use live aliases."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [{"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"}]
        mock_get.side_effect = [Exception("backend unreachable"), aliases_resp]

        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 100000}
        mock_post.return_value = count_resp

        cache = ChannelCache()
        assert cache.get_resolved() == FALLBACK_CHANNELS
        cache._failed_at = None  # skip the retry cooldown
        assert cache.get_resolved() == {"unstable": "latest-48-nixos-unstable"}
        assert cache.using_fallback is False

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_resolves_when_count_probes_fail(self, mock_get, mock_post):
        """Resolution needs alias names only — failing `_count` must not force the fallback."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"},
            {"alias": "latest-48-nixos-25.11", "index": "nixos-48-25.11-cafebabe"},
        ]
        mock_get.return_value = aliases_resp
        mock_post.side_effect = Exception("count refused")

        cache = ChannelCache()
        resolved = cache.get_resolved()
        assert cache.using_fallback is False
        assert resolved["unstable"] == "latest-48-nixos-unstable"
        assert resolved["stable"] == "latest-48-nixos-25.11"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_failed_counts_are_not_memoized(self, mock_get, mock_post):
        """An empty count map while aliases exist means the probes failed, not that
        the channels are gone — memoizing it would report every channel as
        Unavailable for the life of the process."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [{"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"}]
        mock_get.return_value = aliases_resp

        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 100000}
        mock_post.side_effect = [Exception("count refused"), count_resp]

        cache = ChannelCache()
        assert cache.get_available() == {}
        assert cache.available_channels is None, "a failed count probe must not be cached"
        assert cache.get_available() == {"latest-48-nixos-unstable": "100,000 documents"}

    @patch("mcp_nixos.caches.requests.get")
    def test_failed_discovery_backs_off_before_retrying(self, mock_get):
        """Fallback results are not cached, so without a cooldown every caller
        would pay for its own round of 10s requests during an outage."""
        mock_get.side_effect = Exception("backend unreachable")
        cache = ChannelCache()

        assert cache.get_resolved() == FALLBACK_CHANNELS
        assert mock_get.call_count == 1
        # Still inside the cooldown: serve the fallback without re-probing.
        assert cache.get_resolved() == FALLBACK_CHANNELS
        assert mock_get.call_count == 1

        cache._failed_at = time.monotonic() - ChannelCache._DISCOVERY_RETRY_COOLDOWN - 1
        assert cache.get_resolved() == FALLBACK_CHANNELS
        assert mock_get.call_count == 2, "cooldown expiry must allow another probe"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_confirmed_empty_alias_is_never_resolved(self, mock_get, mock_post):
        """Hydra publishes an alias before its index fills, so mid-rollover the
        highest generation can be live but empty. Resolving to it would fail
        every search for that channel for the life of the process."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-50-nixos-unstable", "index": "nixos-50-unstable-deadbeef"},
            {"alias": "latest-51-nixos-unstable", "index": "nixos-51-unstable-fresh"},
        ]
        mock_get.return_value = aliases_resp

        def fake_post(url, **_kwargs):
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = {"count": 0 if "latest-51" in url else 450000}
            return resp

        mock_post.side_effect = fake_post

        cache = ChannelCache()
        assert cache.get_resolved()["unstable"] == "latest-50-nixos-unstable"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_rollover_state_expires_so_the_new_generation_is_picked_up(self, mock_get, mock_post):
        """A snapshot taken mid-publish must not outlive the publish window, or a
        long-running server stays pinned to the old generation forever."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-50-nixos-unstable", "index": "nixos-50-unstable-deadbeef"},
            {"alias": "latest-51-nixos-unstable", "index": "nixos-51-unstable-fresh"},
        ]
        mock_get.return_value = aliases_resp
        filled = {"yet": False}

        def fake_post(url, **_kwargs):
            resp = Mock()
            resp.status_code = 200
            if "latest-51" in url:
                resp.json.return_value = {"count": 450000 if filled["yet"] else 0}
            else:
                resp.json.return_value = {"count": 440000}
            return resp

        mock_post.side_effect = fake_post

        cache = ChannelCache()
        assert cache.get_resolved()["unstable"] == "latest-50-nixos-unstable"
        assert cache.get_resolved()["unstable"] == "latest-50-nixos-unstable"

        filled["yet"] = True
        cache._rollover_at = time.monotonic() - ChannelCache._ROLLOVER_RECHECK - 1
        assert cache.get_resolved()["unstable"] == "latest-51-nixos-unstable"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_resolution_after_a_failed_count_is_not_cached(self, mock_get, mock_post):
        """A failed probe leaves the alias a candidate, so the winner might be an
        empty rollover index we could not rule out. Memoizing that would break
        the channel until restart, so the resolution is recomputed next call."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-50-nixos-unstable", "index": "nixos-50-unstable-deadbeef"},
            {"alias": "latest-51-nixos-unstable", "index": "nixos-51-unstable-fresh"},
        ]
        mock_get.return_value = aliases_resp

        def probe(url, fresh_count):
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = {"count": fresh_count if "latest-51" in url else 450000}
            return resp

        # First pass: the new alias's probe fails, so it stays a candidate and wins.
        # Second pass: the probe succeeds and confirms it is empty.
        state = {"first": True}

        def fake_post(url, **_kwargs):
            if "latest-51" in url and state["first"]:
                state["first"] = False
                raise requests.RequestException("count refused")
            return probe(url, 0)

        mock_post.side_effect = fake_post

        cache = ChannelCache()
        assert cache.get_resolved()["unstable"] == "latest-51-nixos-unstable"
        assert cache.resolved_channels is None, "an incomplete probe must not be memoized"
        assert cache.get_resolved()["unstable"] == "latest-50-nixos-unstable"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_partial_count_failure_keeps_every_channel_resolvable(self, mock_get, mock_post):
        """Regression: caching the successfully-counted subset dropped channels
        whose probe failed — `stable` could vanish until process restart."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"},
            {"alias": "latest-48-nixos-25.11", "index": "nixos-48-25.11-cafebabe"},
        ]
        mock_get.return_value = aliases_resp

        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 100000}

        def fake_post(url, **_kwargs):
            if "25.11" in url:
                raise requests.RequestException("count refused")
            return count_resp

        mock_post.side_effect = fake_post

        cache = ChannelCache()
        assert cache.get_available() == {"latest-48-nixos-unstable": "100,000 documents"}
        assert cache.available_channels is None, "a partial listing must not be cached"
        # Resolution reads alias names, so the un-counted channel still resolves.
        resolved = cache.get_resolved()
        assert resolved["stable"] == "latest-48-nixos-25.11"
        assert resolved["unstable"] == "latest-48-nixos-unstable"

    @patch("mcp_nixos.caches.requests.get")
    def test_concurrent_resolution_never_caches_a_fallback(self, mock_get):
        """Regression: `using_fallback` used to be shared mutable state, so a
        concurrent success could clear the flag before a fallback resolution
        checked it — permanently caching the stale map."""
        import threading

        mock_get.side_effect = Exception("backend unreachable")
        cache = ChannelCache()
        results: list[dict[str, str]] = []
        threads = [threading.Thread(target=lambda: results.append(cache.get_resolved())) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert all(r == FALLBACK_CHANNELS for r in results)
        assert cache.resolved_channels is None, "a fallback must never end up cached"

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_discover_channels(self, mock_get, mock_post):
        # _cat/aliases returns the list of `latest-*-nixos-*` aliases live on
        # the backend; each one then gets a per-alias _count probe.
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"},
            {"alias": "latest-46-nixos-25.11", "index": "nixos-46-25.11-cafebabe"},
            {"alias": ".kibana", "index": ".kibana_1"},  # noise the discovery must skip
        ]
        mock_get.return_value = aliases_resp

        count_resp = Mock()
        count_resp.status_code = 200
        count_resp.json.return_value = {"count": 100000}
        mock_post.return_value = count_resp

        cache = ChannelCache()
        cache.available_channels = None
        result = cache.get_available()
        assert set(result) == {"latest-48-nixos-unstable", "latest-46-nixos-25.11"}

    @patch("mcp_nixos.caches.requests.post")
    @patch("mcp_nixos.caches.requests.get")
    def test_discover_skips_zero_count_aliases(self, mock_get, mock_post):
        """An alias that responds with count=0 must not appear in available."""
        aliases_resp = Mock()
        aliases_resp.status_code = 200
        aliases_resp.json.return_value = [
            {"alias": "latest-48-nixos-unstable", "index": "nixos-48-unstable-deadbeef"},
            {"alias": "latest-99-nixos-99.99", "index": "nixos-99-99.99-empty"},
        ]
        mock_get.return_value = aliases_resp

        responses = {
            "latest-48-nixos-unstable": (200, {"count": 100000}),
            "latest-99-nixos-99.99": (200, {"count": 0}),
        }

        def fake_post(url, **_kwargs):
            for alias, (status, body) in responses.items():
                if alias in url:
                    resp = Mock()
                    resp.status_code = status
                    resp.json.return_value = body
                    return resp
            raise AssertionError(f"unexpected POST: {url}")

        mock_post.side_effect = fake_post

        cache = ChannelCache()
        cache.available_channels = None
        assert cache.get_available() == {"latest-48-nixos-unstable": "100,000 documents"}

    @patch("mcp_nixos.caches.requests.get")
    def test_discover_returns_empty_on_api_error(self, mock_get):
        """Non-200 from _cat/aliases must short-circuit to {} so the caller
        falls back to FALLBACK_CHANNELS instead of crashing."""
        aliases_resp = Mock()
        aliases_resp.status_code = 503
        mock_get.return_value = aliases_resp

        cache = ChannelCache()
        cache.available_channels = None
        assert cache.get_available() == {}

    def test_resolve_picks_highest_generation_for_unstable(self):
        """Regression: previously `_resolve_channels` picked the first unstable
        match in dict-insertion order, which yielded the lowest generation. The
        freshest data lives on the highest generation, so the resolver must
        prefer that even when older generations are still live."""
        cache = ChannelCache()
        cache.alias_names = [
            "latest-45-nixos-unstable",
            "latest-46-nixos-unstable",
            "latest-48-nixos-unstable",
            "latest-47-nixos-unstable",
        ]
        cache.available_channels = dict.fromkeys(cache.alias_names, "400,000 documents")
        resolved = cache.get_resolved()
        assert resolved["unstable"] == "latest-48-nixos-unstable"

    def test_resolve_picks_highest_generation_per_release(self):
        """Same logic for release channels: when multiple generations of the
        same release version are live during a rollover window, pick the max."""
        cache = ChannelCache()
        cache.alias_names = [
            "latest-46-nixos-25.11",
            "latest-48-nixos-25.11",
            "latest-47-nixos-25.11",
        ]
        cache.available_channels = dict.fromkeys(cache.alias_names, "400,000 documents")
        resolved = cache.get_resolved()
        assert resolved["25.11"] == "latest-48-nixos-25.11"
        assert resolved["stable"] == "latest-48-nixos-25.11"
        assert resolved["beta"] == "latest-48-nixos-25.11"

    def test_resolve_picks_highest_release_version_for_stable(self):
        """`stable` aliases to the newest release version (not the newest
        generation across versions)."""
        cache = ChannelCache()
        cache.alias_names = [
            "latest-48-nixos-25.05",
            "latest-48-nixos-25.11",
            "latest-48-nixos-26.05",
        ]
        cache.available_channels = dict.fromkeys(cache.alias_names, "400,000 documents")
        resolved = cache.get_resolved()
        assert resolved["stable"] == "latest-48-nixos-26.05"
        assert resolved["beta"] == "latest-48-nixos-26.05"
        assert resolved["25.05"] == "latest-48-nixos-25.05"
        assert resolved["25.11"] == "latest-48-nixos-25.11"
        assert resolved["26.05"] == "latest-48-nixos-26.05"

    def test_resolve_unstable_without_stable_releases(self):
        """Only unstable is live — resolver must still produce a usable map
        and must not synthesize a fake `stable` / `beta` entry."""
        cache = ChannelCache()
        cache.alias_names = ["latest-48-nixos-unstable"]
        cache.available_channels = {"latest-48-nixos-unstable": "450,000 documents"}
        resolved = cache.get_resolved()
        assert resolved == {"unstable": "latest-48-nixos-unstable"}


@pytest.mark.unit
class TestChannelValidation:
    """Test channel validation helpers."""

    @patch("mcp_nixos.sources.base.requests.post")
    @patch("mcp_nixos.sources.base.get_channels")
    def test_valid_channel(self, mock_get_channels, mock_post):
        mock_get_channels.return_value = {"stable": "latest-44-nixos-25.11"}
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"count": 100}
        result = validate_channel("stable")
        assert result is True

    @patch("mcp_nixos.sources.base.get_channels")
    def test_invalid_channel(self, mock_get_channels):
        mock_get_channels.return_value = {"stable": "latest-44-nixos-25.11"}
        result = validate_channel("nonexistent")
        assert result is False

    def test_special_characters(self):
        result = validate_channel("invalid<>channel")
        assert result is False

    def test_suggestions(self):
        result = get_channel_suggestions("unstabel")
        assert "unstable" in result or "Did you mean" in result or "Available" in result


class TestGetChannels:
    """Test get_channels function."""

    def test_returns_dict(self):
        result = get_channels()
        assert isinstance(result, dict)

    def test_contains_unstable(self):
        result = get_channels()
        assert "unstable" in result


@pytest.mark.unit
class TestWikiFunctions:
    """Test wiki.nixos.org internal functions."""

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_success(self, mock_get):
        """Test successful wiki search."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {
                "search": [
                    {"title": "Flakes", "snippet": "Flakes are...", "wordcount": 1500},
                    {"title": "Nvidia", "snippet": "GPU drivers...", "wordcount": 800},
                ]
            }
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("flakes", 10)
        assert "Found 2 wiki articles" in result
        assert "Flakes" in result
        assert "wiki.nixos.org" in result
        assert "Error" not in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_no_results(self, mock_get):
        """Test wiki search with no results."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"search": []}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("xyznonexistent", 10)
        assert "No wiki articles found" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_timeout(self, mock_get):
        """Test wiki search timeout handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.Timeout()
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_api_error(self, mock_get):
        """Test wiki search API error handling."""
        from mcp_nixos.server import _search_wiki

        mock_get.side_effect = requests.RequestException("Connection failed")
        result = _search_wiki("test", 10)
        assert "Error" in result
        assert "API_ERROR" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_search_wiki_strips_html(self, mock_get):
        """Test wiki search strips HTML from snippets."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {
                "search": [
                    {
                        "title": "Test",
                        "snippet": '<span class="searchmatch">highlighted</span> text',
                        "wordcount": 100,
                    }
                ]
            }
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("test", 10)
        assert "<span" not in result
        assert "highlighted" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_success(self, mock_get):
        """Wiki info renders section 0 via action=parse and strips page chrome."""
        from mcp_nixos.server import _info_wiki

        html = (
            '<div class="mw-parser-output">'
            '<div class="mw-pt-languages noprint">Other languages: English español</div>'
            '<div class="box">This article or section needs cleanup.</div>'
            "<p>&lt;translate&gt; &lt;!--T:182--&gt; <b>Nix flakes</b> are a new way to manage Nix projects"
            '<sup class="reference">[1]</sup> , really&lt;/translate&gt;.</p>'
            '<div class="mw-references-wrap"><ol><li>ref</li></ol></div>'
            "</div>"
        )
        mock_resp = Mock()
        mock_resp.json.return_value = {"parse": {"title": "Flakes", "text": {"*": html}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Flakes")
        assert "Wiki: Flakes" in result
        assert "https://wiki.nixos.org/wiki/Flakes" in result
        assert "Nix flakes are a new way to manage Nix projects, really." in result
        for chrome in ("Other languages", "needs cleanup", "[1]", "translate", "T:182", "ref"):
            assert chrome not in result
        params = mock_get.call_args.kwargs["params"]
        assert params["action"] == "parse"
        assert params["section"] == "0"
        assert params["redirects"] == "1"

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_not_found(self, mock_get):
        """A missing page is an API-level error object, not an HTTP error."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("NonexistentPage")
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_other_api_error(self, mock_get):
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"error": {"code": "readapidenied", "info": "You need read permission"}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Flakes")
        assert "API_ERROR" in result
        assert "read permission" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_timeout(self, mock_get):
        """Test wiki info timeout handling."""
        from mcp_nixos.server import _info_wiki

        mock_get.side_effect = requests.Timeout()
        result = _info_wiki("test")
        assert "Error" in result
        assert "TIMEOUT" in result

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_info_wiki_truncates_long_extract(self, mock_get):
        """Test wiki info truncates very long intros."""
        from mcp_nixos.server import _info_wiki

        long_text = "A" * 2000
        mock_resp = Mock()
        mock_resp.json.return_value = {"parse": {"title": "Test", "text": {"*": f"<p>{long_text}</p>"}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Test")
        assert len(result) < len(long_text) + 200  # Account for header
        assert result.endswith("...")


@pytest.mark.unit
class TestNixDevFunctions:
    """Test nix.dev internal functions."""

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_success(self, mock_get):
        """Test successful nix.dev search."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/first-steps", "concepts/flakes"],
            "titles": ["First Steps", "Flakes"],
            "terms": {"flake": [1], "nix": [0, 1], "tutorial": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Reset cache to trigger fetch
        nixdev_cache.index = None

        result = _search_nixdev("flakes", 10)
        assert "Flakes" in result
        assert "nix.dev" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_matches_sphinx_stems(self, mock_get):
        """Sphinx indexes Porter stems, so whole query words must match their stem.

        Regression: "derivation" and "getting started" returned nothing because
        the index only holds "deriv", "get" and "start". Single-document terms
        are stored as a bare int, which used to be dropped as well.
        """
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/packaging", "concepts/faq", "tutorials/first-steps"],
            "titles": ["Packaging existing software", "FAQ", "First steps"],
            "terms": {"deriv": [0, 1], "get": 2, "start": 2, "1m": [1]},
            "titleterms": {"deriv": 0},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp
        nixdev_cache.index = None

        result = _search_nixdev("derivation", 10)
        lines = [line for line in result.splitlines() if line.startswith("* ")]
        # Title stem hit ranks the tutorial above the page that merely mentions it.
        assert lines == ["* Packaging existing software", "* FAQ"]

        result = _search_nixdev("getting started", 10)
        assert "First steps" in result

        # Stems shorter than the minimum never match by prefix ("1m" vs "1mb").
        assert "No nix.dev documentation found" in _search_nixdev("1mb", 10)

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_partial_matches_rank_below_exact(self, mock_get):
        """A query word inside a longer body term still scores, below exact hits.

        "shell" is an exact stem for the dev-shell guide and a partial match for
        the single-document (bare int) body term "nix-shell". Title terms never
        match partially, so a page whose only link is a partial titleterm is
        absent. Equal scores order by document id.
        """
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/first-steps", "guides/dev-shell", "concepts/other"],
            "titles": ["First steps", "Dev shells", "Other"],
            "terms": {"shell": [1], "nix-shell": 0},
            "titleterms": {"shell-history": [2]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp
        nixdev_cache.index = None

        result = _search_nixdev("shell", 10)
        lines = [line for line in result.splitlines() if line.startswith("* ")]
        assert lines == ["* Dev shells", "* First steps"]
        assert "Other" not in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_no_results(self, mock_get):
        """Test nix.dev search with no matches."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {"docnames": ["tutorials/first-steps"], "titles": ["First Steps"], "terms": {"tutorial": [0]}}
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        result = _search_nixdev("xyznonexistent", 10)
        assert "No nix.dev documentation found" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_nixdev_cache_reuse(self, mock_get):
        """Test that nix.dev cache is reused."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/first-steps"],
            "titles": ["First Steps"],
            "terms": {"nix": [0], "tutorial": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        _search_nixdev("nix", 10)
        _search_nixdev("tutorial", 10)

        # Should only fetch once due to caching
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_nixdev_cache_timeout(self, mock_get):
        """Test nix.dev cache handles timeout."""
        from mcp_nixos.server import APIError, nixdev_cache

        mock_get.side_effect = requests.Timeout()
        nixdev_cache.index = None

        with pytest.raises(APIError) as exc_info:
            nixdev_cache.get_index()
        assert "Timeout" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_search_nixdev_title_match_bonus(self, mock_get):
        """Test nix.dev search gives bonus to title matches."""
        import json

        from mcp_nixos.server import _search_nixdev, nixdev_cache

        mock_index = {
            "docnames": ["tutorials/packaging", "concepts/flakes", "tutorials/flakes"],
            "titles": ["Packaging Python Apps", "Flakes Intro", "Flakes Tutorial"],
            "terms": {"flakes": [1, 2], "packaging": [0]},
        }
        mock_resp = Mock()
        mock_resp.text = f"Search.setIndex({json.dumps(mock_index)})"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        nixdev_cache.index = None

        result = _search_nixdev("flakes", 10)
        # Title matches should appear
        assert "Flakes" in result


@pytest.mark.unit
class TestNixvimCache:
    """Test NixvimCache chunked loader (issue #167)."""

    def _fresh_cache(self):
        """Reset the module-level nixvim_cache singleton so each test gets a clean slate."""
        from mcp_nixos import caches

        caches.nixvim_cache = caches.NixvimCache()
        return caches.nixvim_cache

    def _chunk_resp(self, chunk):
        """Build a Mock response that returns `chunk` from .json() once."""
        resp = Mock(status_code=200, raise_for_status=Mock())

        def _json():
            return chunk

        resp.json = _json
        return resp

    @patch("mcp_nixos.caches.requests.get")
    def test_loads_chunks_until_404(self, mock_get):
        """Walks chunks 0,1,2 and stops at the first 404."""
        chunk0 = [{"name": "opt0", "type": "boolean", "description": ""}]
        chunk1 = [{"name": "opt1", "type": "boolean", "description": ""}]
        chunk2 = [{"name": "opt2", "type": "boolean", "description": ""}]

        mock_get.side_effect = [
            self._chunk_resp(chunk0),
            self._chunk_resp(chunk1),
            self._chunk_resp(chunk2),
            Mock(status_code=404),
        ]

        cache = self._fresh_cache()
        options = cache.get_options()

        assert len(options) == 3
        assert [o["name"] for o in options] == ["opt0", "opt1", "opt2"]
        assert mock_get.call_count == 4  # 3 chunks + 1 probe that 404'd

    @patch("mcp_nixos.caches.requests.get")
    def test_empty_first_chunk_still_stops(self, mock_get):
        """An empty first chunk is not an error — just means zero options."""
        mock_get.side_effect = [
            self._chunk_resp([]),
            Mock(status_code=404),
        ]

        cache = self._fresh_cache()
        options = cache.get_options()

        assert options == []
        assert mock_get.call_count == 2  # chunk 0 + 404 probe

    @patch("mcp_nixos.caches.requests.get")
    def test_404_on_first_chunk_raises(self, mock_get):
        """A 404 on chunk 0 raises APIError so a wrong URL doesn't masquerade as 'no options'."""
        from mcp_nixos.caches import APIError

        mock_get.return_value = Mock(status_code=404)

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache.get_options()
        assert "First Nixvim options chunk" in str(exc_info.value)
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_request_exception_raises(self, mock_get):
        """A network error during fetch surfaces as APIError."""
        from mcp_nixos.caches import APIError

        mock_get.side_effect = requests.RequestException("connection reset")

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache.get_options()
        assert "Failed to fetch" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_timeout_raises(self, mock_get):
        """A timeout surfaces as APIError with a Timeout message."""
        from mcp_nixos.caches import APIError

        mock_get.side_effect = requests.Timeout()

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache.get_options()
        assert "Timeout" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_cache_reused_on_subsequent_calls(self, mock_get):
        """A second call returns the cached list without re-fetching."""
        chunk = [{"name": "opt0", "type": "boolean", "description": ""}]
        mock_get.side_effect = [
            self._chunk_resp(chunk),
            Mock(status_code=404),
        ]

        cache = self._fresh_cache()
        first = cache.get_options()
        second = cache.get_options()

        assert first is second
        # 1 chunk + 1 404 probe on the first call; zero network calls on the second.
        assert mock_get.call_count == 2

    @patch("mcp_nixos.caches.requests.get")
    def test_unexpected_payload_raises(self, mock_get):
        """A non-list payload mid-walk raises APIError so a layout change
        doesn't silently cache a partial option set."""
        from mcp_nixos.caches import APIError

        unexpected_resp = Mock(status_code=200, raise_for_status=Mock())
        unexpected_resp.json = lambda: {"not": "a list"}

        mock_get.side_effect = [
            self._chunk_resp([{"name": "a"}]),
            unexpected_resp,
        ]

        cache = self._fresh_cache()
        with pytest.raises(APIError) as exc_info:
            cache.get_options()
        assert "Unexpected Nixvim options payload" in str(exc_info.value)

    @patch("mcp_nixos.caches.requests.get")
    def test_concurrent_first_call_only_fetches_once(self, mock_get):
        """Double-checked locking: N concurrent first calls perform the
        walk exactly once, not N times."""
        from concurrent.futures import ThreadPoolExecutor

        # 1 listing-style "first chunk" + 1 trailing 404 = 2 calls per walk.
        # The lock must collapse N concurrent callers into a single walk.
        chunk = [{"name": "a"}]
        mock_get.side_effect = [
            self._chunk_resp(chunk),
            Mock(status_code=404),
        ] * 50  # plenty of responses for any number of concurrent walks

        cache = self._fresh_cache()
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: cache.get_options(), range(20)))

        # Exactly one walk happened, so exactly 2 network calls.
        assert mock_get.call_count == 2


@pytest.mark.unit
class TestPlainTextOutputDocs:
    """Verify wiki/nix-dev outputs are plain text."""

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_wiki_search_no_xml(self, mock_get):
        """Test wiki search returns plain text."""
        from mcp_nixos.server import _search_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "query": {"search": [{"title": "Test", "snippet": "<code>example</code>", "wordcount": 100}]}
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _search_wiki("test", 10)
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")

    @patch("mcp_nixos.sources.wiki.requests.get")
    def test_wiki_info_no_xml(self, mock_get):
        """Test wiki info returns plain text."""
        from mcp_nixos.server import _info_wiki

        mock_resp = Mock()
        mock_resp.json.return_value = {"query": {"pages": {"123": {"title": "Test", "extract": "Some content"}}}}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        result = _info_wiki("Test")
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")


@pytest.mark.unit
class TestPlainTextOutput:
    """Verify all outputs are plain text without XML/JSON."""

    def test_error_no_xml(self):
        result = error("Test <message>")
        assert "<error>" not in result
        assert "</error>" not in result

    def test_error_no_json(self):
        result = error("Test message")
        assert not result.startswith("{")
        assert not result.startswith("[")


@pytest.mark.unit
class TestNoogleFunctions:
    """Test Noogle (noogle.dev) internal functions."""

    def test_type_signature_comes_from_meta(self):
        """Noogle stores signatures under meta, not content.

        Regression: every search/info result lacked a Type line and stats
        reported "With type signatures: 0" because only content was inspected.
        """
        from mcp_nixos.sources.noogle import _get_noogle_type_signature

        doc = {
            "meta": {"title": "builtins.mapAttrs", "signature": "mapAttrs :: (String -> a -> b) -> AttrSet\n"},
            "content": {"content": "Apply a function..."},
        }
        assert _get_noogle_type_signature(doc) == "mapAttrs :: (String -> a -> b) -> AttrSet"
        assert _get_noogle_type_signature({"meta": {"signature": None}, "content": {"type": "a -> b"}}) == "a -> b"
        assert _get_noogle_type_signature({"meta": {}, "content": {}}) == ""

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_success(self, mock_get):
        """Test successful Noogle search."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"title": "mapAttrs", "path": ["lib", "attrsets", "mapAttrs"], "aliases": []},
                    "content": {
                        "signature": "(String -> Any -> Any) -> AttrSet -> AttrSet",
                        "content": "Apply a function to each element in an attribute set.",
                    },
                },
                {
                    "meta": {"title": "mapAttrs'", "path": ["lib", "attrsets", "mapAttrs'"], "aliases": []},
                    "content": {
                        "signature": "(String -> Any -> { name :: String; value :: Any; }) -> AttrSet -> AttrSet",
                        "content": "Like mapAttrs but allows changing names.",
                    },
                },
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # Reset cache to trigger fetch
        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("mapAttrs", 10)
        assert "Found" in result
        assert "mapAttrs" in result
        assert "lib.attrsets.mapAttrs" in result
        assert "Error" not in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_no_results(self, mock_get):
        """Test Noogle search with no matches."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"title": "test", "path": ["lib", "test"], "aliases": []}, "content": {"content": "test"}}
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("xyznonexistent", 10)
        assert "No Noogle functions found" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_timeout(self, mock_get):
        """Test Noogle search timeout handling."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_get.side_effect = requests.Timeout()
        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("test", 10)
        assert "Error" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_info_noogle_success(self, mock_get):
        """Test successful Noogle function info."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {
                        "title": "mapAttrs",
                        "path": ["lib", "attrsets", "mapAttrs"],
                        "aliases": [["builtins", "mapAttrs"], ["lib", "mapAttrs"]],
                        "position": {"file": "lib/attrsets.nix", "line": 1016},
                    },
                    "content": {
                        "signature": "(String -> Any -> Any) -> AttrSet -> AttrSet",
                        "content": "Apply a function to each element in an attribute set.",
                        "example": 'mapAttrs (name: value: name + "-" + value) { x = "foo"; }',
                    },
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("lib.attrsets.mapAttrs")
        assert "Noogle Function: lib.attrsets.mapAttrs" in result
        assert "Type:" in result
        assert "Path:" in result
        assert "Aliases:" in result
        assert "Description:" in result
        assert "Example:" in result
        assert "Source:" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_info_noogle_not_found(self, mock_get):
        """Test Noogle function not found."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"title": "test", "path": ["lib", "test"], "aliases": []}, "content": {"content": "test"}}
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("nonexistent.function")
        assert "NOT_FOUND" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_stats_noogle_success(self, mock_get):
        """Test Noogle statistics."""
        from mcp_nixos.server import _stats_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "strings", "concatStrings"]},
                    "content": {"signature": "[String] -> String", "content": "Concatenate strings"},
                },
                {
                    "meta": {"path": ["lib", "strings", "hasPrefix"]},
                    "content": {"signature": "String -> String -> Bool", "content": "Check prefix"},
                },
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {"content": "Map over attrs"}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _stats_noogle()
        assert "Noogle Statistics:" in result
        assert "Total functions:" in result
        assert "With type signatures:" in result
        assert "Categories:" in result
        assert "noogle.dev" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_browse_noogle_no_prefix(self, mock_get):
        """Test browsing Noogle categories with no prefix."""
        from mcp_nixos.server import _browse_noogle_options, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {"meta": {"path": ["lib", "strings", "concatStrings"]}, "content": {}},
                {"meta": {"path": ["lib", "strings", "hasPrefix"]}, "content": {}},
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _browse_noogle_options("")
        assert "Noogle function categories" in result
        assert "lib.strings" in result
        assert "lib.attrsets" in result

    @patch("mcp_nixos.caches.requests.get")
    def test_browse_noogle_with_prefix(self, mock_get):
        """Test browsing Noogle functions with a prefix."""
        from mcp_nixos.server import _browse_noogle_options, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "strings", "concatStrings"]},
                    "content": {"signature": "[String] -> String", "content": "Concatenate strings"},
                },
                {
                    "meta": {"path": ["lib", "strings", "hasPrefix"]},
                    "content": {"signature": "String -> String -> Bool", "content": "Check prefix"},
                },
                {"meta": {"path": ["lib", "attrsets", "mapAttrs"]}, "content": {}},
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _browse_noogle_options("lib.strings")
        assert "lib.strings" in result
        assert "concatStrings" in result
        assert "hasPrefix" in result
        assert "mapAttrs" not in result

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_cache_reuse(self, mock_get):
        """Test that Noogle cache is reused."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [{"meta": {"path": ["lib", "test"]}, "content": {"content": "test"}}],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        _search_noogle("test", 10)
        _search_noogle("other", 10)

        # Should only fetch once due to caching
        assert mock_get.call_count == 1

    @patch("mcp_nixos.caches.requests.get")
    def test_search_noogle_alias_matching(self, mock_get):
        """Test Noogle search matches aliases."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {
                        "title": "mapAttrs",
                        "path": ["lib", "attrsets", "mapAttrs"],
                        "aliases": [["builtins", "mapAttrs"]],
                    },
                    "content": {"content": "Map over attrs"},
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("builtins.mapAttrs", 10)
        assert "lib.attrsets.mapAttrs" in result
        assert "builtins.mapAttrs" in result


@pytest.mark.unit
class TestNooglePlainTextOutput:
    """Verify Noogle outputs are plain text."""

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_search_no_xml(self, mock_get):
        """Test Noogle search returns plain text."""
        from mcp_nixos.server import _search_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [{"meta": {"path": ["lib", "test"]}, "content": {"content": "test"}}],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _search_noogle("test", 10)
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")

    @patch("mcp_nixos.caches.requests.get")
    def test_noogle_info_no_xml(self, mock_get):
        """Test Noogle info returns plain text."""
        from mcp_nixos.server import _info_noogle, noogle_cache

        mock_resp = Mock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "meta": {"path": ["lib", "test"], "aliases": []},
                    "content": {"content": "test", "signature": "a -> b"},
                }
            ],
            "builtinTypes": {},
        }
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        noogle_cache._data = None
        noogle_cache._builtin_types = None

        result = _info_noogle("lib.test")
        assert "<error>" not in result
        assert "</error>" not in result
        assert not result.strip().startswith("{")
