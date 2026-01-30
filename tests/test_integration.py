"""Integration tests that verify actual API responses."""

import pytest
from mcp_nixos.server import nix, nix_versions

# Get underlying functions from MCP tool wrappers
nix_fn = nix.fn
nix_versions_fn = nix_versions.fn


def assert_plain_text(result: str) -> None:
    """Assert result is plain text, not XML/JSON.

    Note: NixOS options can contain <name> placeholders which are valid,
    so we check for XML tags specifically rather than any '<' character.
    """
    assert not result.strip().startswith("<"), "Output looks like XML"
    assert not result.strip().startswith("{"), "Output looks like JSON"
    assert "</result>" not in result, "Contains XML result tags"
    assert "<result>" not in result, "Contains XML result tags"
    assert "</error>" not in result, "Contains XML error tags"
    assert "<error>" not in result, "Contains XML error tags"


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixSearchIntegration:
    """Test nix search action against real APIs."""

    @pytest.mark.asyncio
    async def test_search_nixos_packages(self):
        result = await nix_fn(action="search", query="firefox", source="nixos", type="packages", limit=3)
        assert "Found" in result or "firefox" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_nixos_options(self):
        result = await nix_fn(action="search", query="nginx", source="nixos", type="options", limit=3)
        assert "nginx" in result.lower() or "No options found" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_home_manager(self):
        result = await nix_fn(action="search", query="git", source="home-manager", limit=3)
        assert "git" in result.lower() or "No Home Manager" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_darwin(self):
        result = await nix_fn(action="search", query="dock", source="darwin", limit=3)
        assert "dock" in result.lower() or "No nix-darwin" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_flakes(self):
        result = await nix_fn(action="search", query="neovim", source="flakes", limit=3)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_nixvim(self):
        result = await nix_fn(action="search", query="telescope", source="nixvim", limit=3)
        assert "telescope" in result.lower() or "No Nixvim" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_flakehub(self):
        result = await nix_fn(action="search", query="nixpkgs", source="flakehub", limit=3)
        assert "flakehub" in result.lower() or "nixpkgs" in result.lower() or "No flakes" in result
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixInfoIntegration:
    """Test nix info action against real APIs."""

    @pytest.mark.asyncio
    async def test_info_nixos_package(self):
        result = await nix_fn(action="info", query="firefox", source="nixos", type="package")
        assert "Package: firefox" in result or "NOT_FOUND" in result
        if "NOT_FOUND" not in result:
            assert "Version:" in result
            assert "Description:" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_nixos_option(self):
        result = await nix_fn(action="info", query="services.nginx.enable", source="nixos", type="option")
        assert "Option:" in result or "NOT_FOUND" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_home_manager(self):
        result = await nix_fn(action="info", query="programs.git.enable", source="home-manager")
        assert "Option: programs.git.enable" in result or "not found" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_darwin(self):
        result = await nix_fn(action="info", query="system.defaults.dock.autohide", source="darwin")
        assert "Option:" in result or "not found" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_nixvim(self):
        result = await nix_fn(action="info", query="plugins.telescope.enable", source="nixvim")
        assert "Nixvim Option:" in result or "not found" in result or "NOT_FOUND" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_flakehub(self):
        result = await nix_fn(action="info", query="NixOS/nixpkgs", source="flakehub")
        assert "FlakeHub Flake:" in result or "NOT_FOUND" in result
        if "NOT_FOUND" not in result:
            assert "NixOS/nixpkgs" in result
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixStatsIntegration:
    """Test nix stats action against real APIs."""

    @pytest.mark.asyncio
    async def test_stats_nixos(self):
        result = await nix_fn(action="stats", source="nixos")
        assert "NixOS Statistics" in result
        assert "Packages:" in result
        assert "Options:" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_home_manager(self):
        result = await nix_fn(action="stats", source="home-manager")
        assert "Home Manager Statistics" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_darwin(self):
        result = await nix_fn(action="stats", source="darwin")
        assert "nix-darwin Statistics" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_flakes(self):
        result = await nix_fn(action="stats", source="flakes")
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_nixvim(self):
        result = await nix_fn(action="stats", source="nixvim")
        assert "Nixvim Statistics" in result
        assert "Total options:" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_flakehub(self):
        result = await nix_fn(action="stats", source="flakehub")
        assert "FlakeHub Statistics" in result
        assert "Total flakes:" in result
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixOptionsIntegration:
    """Test nix options action against real APIs."""

    @pytest.mark.asyncio
    async def test_browse_home_manager(self):
        result = await nix_fn(action="options", source="home-manager")
        assert "Home Manager" in result or "categories" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_darwin(self):
        result = await nix_fn(action="options", source="darwin")
        assert "nix-darwin" in result or "categories" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_with_prefix(self):
        result = await nix_fn(action="options", source="home-manager", query="programs")
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_nixvim(self):
        result = await nix_fn(action="options", source="nixvim")
        assert "Nixvim option categories" in result or "categories" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_nixvim_with_prefix(self):
        result = await nix_fn(action="options", source="nixvim", query="plugins")
        assert "plugins" in result.lower()
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixChannelsIntegration:
    """Test nix channels action."""

    @pytest.mark.asyncio
    async def test_list_channels(self):
        result = await nix_fn(action="channels")
        assert "unstable" in result.lower()
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixVersionsIntegration:
    """Test nix_versions against real NixHub API."""

    @pytest.mark.asyncio
    async def test_package_versions(self):
        result = await nix_versions_fn(package="python", limit=3)
        assert "Package: python" in result or "Error" in result
        if "Error" not in result:
            assert "version" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_find_specific_version(self):
        result = await nix_versions_fn(package="nodejs", version="20.0.0", limit=5)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_nonexistent_package(self):
        result = await nix_versions_fn(package="nonexistent-package-xyz-123")
        assert "Error" in result
        assert "NOT_FOUND" in result
        assert_plain_text(result)


@pytest.mark.integration
class TestPlainTextOutput:
    """Verify all integration outputs are plain text."""

    @pytest.mark.asyncio
    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    async def test_no_xml_in_search(self):
        result = await nix_fn(action="search", query="git", source="nixos", limit=1)
        assert_plain_text(result)

    @pytest.mark.asyncio
    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    async def test_no_json_in_stats(self):
        result = await nix_fn(action="stats", source="nixos")
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestWikiIntegration:
    """Integration tests for wiki.nixos.org (hits real API)."""

    @pytest.mark.asyncio
    async def test_search_wiki(self):
        """Test real wiki search."""
        result = await nix_fn(action="search", query="installation", source="wiki", limit=5)
        # Should return results or graceful error (timeout is OK)
        assert isinstance(result, str)
        if "Error" not in result:
            assert "wiki" in result.lower() or "Found" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_wiki_flakes(self):
        """Test wiki search for flakes."""
        result = await nix_fn(action="search", query="flakes", source="wiki", limit=5)
        assert isinstance(result, str)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_wiki(self):
        """Test real wiki page info."""
        result = await nix_fn(action="info", query="Flakes", source="wiki")
        assert isinstance(result, str)
        if "NOT_FOUND" not in result and "Error" not in result:
            assert "Wiki:" in result
            assert "wiki.nixos.org" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_wiki_nvidia(self):
        """Test wiki page info for Nvidia."""
        result = await nix_fn(action="info", query="Nvidia", source="wiki")
        assert isinstance(result, str)
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNixDevIntegration:
    """Integration tests for nix.dev (hits real API)."""

    @pytest.mark.asyncio
    async def test_search_nixdev(self):
        """Test real nix.dev search."""
        from mcp_nixos.server import nixdev_cache

        nixdev_cache.index = None  # Reset cache for fresh fetch

        result = await nix_fn(action="search", query="flakes", source="nix-dev", limit=5)
        assert isinstance(result, str)
        if "Error" not in result:
            assert "nix.dev" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_nixdev_tutorials(self):
        """Test nix.dev search for tutorials."""
        from mcp_nixos.server import nixdev_cache

        nixdev_cache.index = None

        result = await nix_fn(action="search", query="tutorial", source="nix-dev", limit=10)
        assert isinstance(result, str)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_nixdev_packaging(self):
        """Test nix.dev search for packaging."""
        result = await nix_fn(action="search", query="packaging", source="nix-dev", limit=5)
        assert isinstance(result, str)
        assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestFlakeInputsIntegration:
    """Test flake-inputs action against real local flake.

    These tests run against this repo's own flake.nix.
    Skip if nix is not installed.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_nix(self):
        """Skip tests if nix is not available."""
        import shutil

        if not shutil.which("nix"):
            pytest.skip("Nix not installed")

    @pytest.fixture
    def repo_root(self):
        """Get the repository root directory."""
        import os

        # This test file is in tests/, so repo root is one level up
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @pytest.mark.asyncio
    async def test_list_inputs(self, repo_root):
        """Test listing flake inputs from this repo."""
        result = await nix_fn(action="flake-inputs", type="list", source=repo_root)
        # Should either list inputs or show no inputs
        assert "Flake inputs" in result or "No inputs found" in result or "FLAKE_ERROR" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_ls_input_root(self, repo_root):
        """Test listing root of a flake input."""
        # First list inputs to get an input name
        list_result = await nix_fn(action="flake-inputs", type="list", source=repo_root)

        if "No inputs found" in list_result or "FLAKE_ERROR" in list_result:
            pytest.skip("No flake inputs available")

        # Extract first input name from result
        import re

        match = re.search(r"\* (\S+)", list_result)
        if not match:
            pytest.skip("Could not parse input name from list")

        input_name = match.group(1)
        result = await nix_fn(action="flake-inputs", type="ls", query=input_name, source=repo_root)
        assert "Contents of" in result or "Error" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_read_flake_nix(self, repo_root):
        """Test reading flake.nix from an input."""
        # First list inputs to get an input name
        list_result = await nix_fn(action="flake-inputs", type="list", source=repo_root)

        if "No inputs found" in list_result or "FLAKE_ERROR" in list_result:
            pytest.skip("No flake inputs available")

        # Extract first input name from result
        import re

        match = re.search(r"\* (\S+)", list_result)
        if not match:
            pytest.skip("Could not parse input name from list")

        input_name = match.group(1)
        result = await nix_fn(action="flake-inputs", type="read", query=f"{input_name}:flake.nix", source=repo_root)
        # Should either read the file or give a file not found error
        assert "File:" in result or "NOT_FOUND" in result or "Error" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_invalid_input_name(self, repo_root):
        """Test error handling for non-existent input."""
        result = await nix_fn(action="flake-inputs", type="ls", query="nonexistent-input-xyz", source=repo_root)
        # Should either fail with input not found or flake error
        assert "NOT_FOUND" in result or "Error" in result or "FLAKE_ERROR" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_flake(self):
        """Test graceful handling when directory is not a flake."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await nix_fn(action="flake-inputs", type="list", source=tmpdir)
            assert "FLAKE_ERROR" in result
            assert "no flake.nix" in result.lower()
            assert_plain_text(result)


@pytest.mark.integration
@pytest.mark.flaky(reruns=3, reruns_delay=2)
class TestNoogleIntegration:
    """Integration tests for Noogle (hits real noogle.dev API)."""

    @pytest.mark.asyncio
    async def test_search_noogle(self):
        """Test real Noogle search."""
        from mcp_nixos.server import noogle_cache

        noogle_cache._data = None  # Reset cache for fresh fetch
        noogle_cache._builtin_types = None

        result = await nix_fn(action="search", query="mapAttrs", source="noogle", limit=5)
        assert isinstance(result, str)
        if "Error" not in result:
            assert "mapAttrs" in result or "Found" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_search_noogle_strings(self):
        """Test Noogle search for string functions."""
        result = await nix_fn(action="search", query="concatStrings", source="noogle", limit=5)
        assert isinstance(result, str)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_noogle(self):
        """Test real Noogle function info."""
        result = await nix_fn(action="info", query="lib.attrsets.mapAttrs", source="noogle")
        assert isinstance(result, str)
        if "NOT_FOUND" not in result and "Error" not in result:
            assert "Noogle Function:" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_info_noogle_builtins(self):
        """Test Noogle info for builtins."""
        result = await nix_fn(action="info", query="builtins.map", source="noogle")
        assert isinstance(result, str)
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_stats_noogle(self):
        """Test Noogle statistics."""
        result = await nix_fn(action="stats", source="noogle")
        assert isinstance(result, str)
        if "Error" not in result:
            assert "Noogle Statistics:" in result
            assert "Total functions:" in result
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_noogle_categories(self):
        """Test browsing Noogle categories."""
        result = await nix_fn(action="options", source="noogle")
        assert isinstance(result, str)
        if "Error" not in result:
            assert "categories" in result.lower() or "lib" in result.lower()
        assert_plain_text(result)

    @pytest.mark.asyncio
    async def test_browse_noogle_with_prefix(self):
        """Test browsing Noogle with a prefix."""
        result = await nix_fn(action="options", source="noogle", query="lib.strings")
        assert isinstance(result, str)
        if "Error" not in result and "No Noogle functions found" not in result:
            assert "lib.strings" in result.lower()
        assert_plain_text(result)
