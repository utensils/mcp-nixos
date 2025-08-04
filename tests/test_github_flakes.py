"""Simple tests for GitHub flakes integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
search = get_tool_function("search")


@pytest.mark.integration
class TestGitHubFlakesReal:
    """Test real GitHub API integration for flake search."""

    @pytest.mark.asyncio
    async def test_real_github_flakes_search(self):
        """Test actual GitHub flakes search integration."""
        # This is an integration test - it actually calls GitHub API
        result = await search("home-manager", search_type="flakes", limit=5)

        # Should find results (either from GitHub or NixOS index)
        assert "home-manager" in result.lower()
        assert "Found" in result or "No flakes found" in result

        # If results found, check for expected format
        if "Found" in result:
            # Should have flake reference format
            assert "github:" in result or "Repository:" in result

    @pytest.mark.asyncio
    async def test_real_github_popular_flakes(self):
        """Test searching for popular flakes shows GitHub stars."""
        # Search for a popular flake
        result = await search("nixpkgs", search_type="flakes", limit=3)

        # nixpkgs is very popular, should have stars if GitHub worked
        if "[" in result and "stars]" in result:
            # GitHub integration worked - check star count is shown
            assert "nixpkgs" in result.lower()
            # Should be sorted by stars (nixpkgs should be high)
            lines = result.split("\n")
            for line in lines:
                if "stars]" in line and "nixpkgs" in line.lower():
                    # Extract star count
                    import re

                    match = re.search(r"\[(\d+) stars\]", line)
                    if match:
                        stars = int(match.group(1))
                        assert stars > 1000  # nixpkgs has many stars

    @pytest.mark.asyncio
    async def test_empty_query_returns_popular(self):
        """Test empty query returns popular flakes."""
        result = await search("", search_type="flakes", limit=5)

        # Should return some results
        assert "Found" in result or "No flakes found" in result

        # If GitHub works, should see high-starred repos
        if "[" in result and "stars]" in result:
            # Should have sorted by stars
            assert any(keyword in result.lower() for keyword in ["nixpkgs", "home-manager", "flake-utils"])


@pytest.mark.unit
class TestGitHubFlakesMocked:
    """Test GitHub flakes with mocked responses."""

    @pytest.mark.asyncio
    async def test_github_api_timeout_graceful(self):
        """Test that timeouts are handled gracefully."""
        # Mock channels
        with patch("mcp_nixos.server.get_channels") as mock_channels:
            mock_channels.return_value = {"unstable": "latest-43-nixos-unstable"}

            # Mock GitHub to timeout
            with patch("mcp_nixos.server.aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session

                # Make get() raise timeout
                mock_session.get.side_effect = TimeoutError()

                # Mock NixOS index to return a result
                with patch("requests.post") as mock_post:
                    mock_post.return_value = Mock(
                        status_code=200,
                        json=lambda: {
                            "hits": {
                                "hits": [
                                    {
                                        "_source": {
                                            "flake_name": "test-flake",
                                            "flake_description": "Test flake",
                                            "package_pname": "test",
                                            "flake_resolved": {"owner": "test", "repo": "test"},
                                        }
                                    }
                                ],
                                "total": {"value": 1},
                            }
                        },
                    )

                    result = await search("test", search_type="flakes", limit=5)

                    # Should still get NixOS results despite GitHub timeout
                    assert "test-flake" in result
                    assert "Error" not in result  # Should not show error to user
