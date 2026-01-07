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
