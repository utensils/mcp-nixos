"""Tests for discussion/community search tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
discourse_search = get_tool_function("discourse_search")
github_search = get_tool_function("github_search")


def create_mock_aiohttp_session(response_status, response_data, side_effect=None):
    """Create a properly mocked aiohttp ClientSession."""
    # Create the response mock
    mock_response = MagicMock()
    mock_response.status = response_status
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # Create the session mock
    mock_session = MagicMock()
    if side_effect:
        mock_session.get = MagicMock(side_effect=side_effect)
    else:
        mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return mock_session


@pytest.mark.unit
class TestDiscourseSearch:
    """Test NixOS Discourse search functionality."""

    @pytest.mark.asyncio
    async def test_discourse_search_success(self):
        """Test successful Discourse search."""
        mock_response_data = {
            "topics": [
                {
                    "id": 1234,
                    "title": "How to install Home Manager",
                    "posts_count": 15,
                    "created_at": "2024-01-15T10:30:00Z",
                    "category_id": 5,
                },
                {
                    "id": 5678,
                    "title": "Home Manager configuration examples",
                    "posts_count": 8,
                    "created_at": "2024-02-20T14:45:00Z",
                    "category_id": 3,
                },
            ]
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await discourse_search("home manager")

            assert "NixOS Discourse discussions for 'home manager':" in result
            assert "How to install Home Manager" in result
            assert "Posts: 15" in result
            assert "https://discourse.nixos.org/t/1234" in result
            assert "Home Manager configuration examples" in result
            assert "Posts: 8" in result
            assert "https://discourse.nixos.org/t/5678" in result

    @pytest.mark.asyncio
    async def test_discourse_search_no_results(self):
        """Test Discourse search with no results."""
        mock_response_data = {"topics": []}

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await discourse_search("xyzabc123")

            assert "No discussions found for 'xyzabc123'" in result
            assert "Try:" in result
            assert "Different keywords" in result

    @pytest.mark.asyncio
    async def test_discourse_search_empty_query(self):
        """Test Discourse search with empty query."""
        result = await discourse_search("")
        assert "Error" in result
        assert "Search query cannot be empty" in result

    @pytest.mark.asyncio
    async def test_discourse_search_invalid_limit(self):
        """Test Discourse search with invalid limit."""
        result = await discourse_search("test", limit=50)
        assert "Error" in result
        assert "Limit must be between 1 and 30" in result

        result = await discourse_search("test", limit=0)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_discourse_search_api_error(self):
        """Test Discourse search with API error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(500, {})

            result = await discourse_search("test")
            assert "Error" in result
            assert "Discourse API error: 500" in result

    @pytest.mark.asyncio
    async def test_discourse_search_timeout(self):
        """Test Discourse search timeout handling."""

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(None, None, side_effect=TimeoutError())

            result = await discourse_search("test")
            assert "Error" in result
            assert "Request timeout" in result

    @pytest.mark.asyncio
    async def test_discourse_search_limit_handling(self):
        """Test Discourse search respects limit."""
        mock_response_data = {
            "topics": [
                {
                    "id": i,
                    "title": f"Topic {i}",
                    "posts_count": i * 2,
                    "created_at": f"2024-01-{i:02d}T10:00:00Z",
                }
                for i in range(1, 20)
            ]
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await discourse_search("test", limit=5)

            # Should only show 5 results
            assert result.count("https://discourse.nixos.org/t/") == 5
            assert "Showing first 5 results" in result


@pytest.mark.unit
class TestGitHubSearch:
    """Test GitHub search functionality."""

    @pytest.mark.asyncio
    async def test_github_search_issues_success(self):
        """Test successful GitHub issue search."""
        mock_response_data = {
            "total_count": 2,
            "items": [
                {
                    "number": 12345,
                    "title": "Python package broken",
                    "state": "open",
                    "created_at": "2024-01-15T10:30:00Z",
                    "comments": 5,
                    "html_url": "https://github.com/NixOS/nixpkgs/issues/12345",
                    "labels": [{"name": "bug"}, {"name": "python"}],
                },
                {
                    "number": 67890,
                    "title": "Update python to 3.12",
                    "state": "closed",
                    "created_at": "2024-02-01T08:00:00Z",
                    "comments": 12,
                    "html_url": "https://github.com/NixOS/nixpkgs/issues/67890",
                    "labels": [{"name": "enhancement"}],
                },
            ],
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await github_search("python broken")

            assert "GitHub issues in NixOS/nixpkgs for 'python broken':" in result
            assert "🟢 Python package broken" in result
            assert "#12345 | open | Comments: 5" in result
            assert "Labels: bug, python" in result
            assert "🔴 Update python to 3.12" in result
            assert "#67890 | closed | Comments: 12" in result

    @pytest.mark.asyncio
    async def test_github_search_prs(self):
        """Test GitHub PR search."""
        mock_response_data = {
            "total_count": 1,
            "items": [
                {
                    "number": 54321,
                    "title": "Fix: python build on darwin",
                    "state": "open",
                    "created_at": "2024-03-01T12:00:00Z",
                    "comments": 3,
                    "html_url": "https://github.com/NixOS/nixpkgs/pull/54321",
                    "labels": [{"name": "darwin"}, {"name": "fix"}],
                }
            ],
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await github_search("python darwin", search_type="prs")

            assert "GitHub prs in NixOS/nixpkgs" in result
            assert "Fix: python build on darwin" in result
            assert "#54321" in result

    @pytest.mark.asyncio
    async def test_github_search_empty_query(self):
        """Test GitHub search with empty query."""
        result = await github_search("")
        assert "Error" in result
        assert "Search query cannot be empty" in result

    @pytest.mark.asyncio
    async def test_github_search_invalid_type(self):
        """Test GitHub search with invalid type."""
        result = await github_search("test", search_type="invalid")
        assert "Error" in result
        assert "Invalid search_type" in result
        assert "issues, prs, discussions" in result

    @pytest.mark.asyncio
    async def test_github_search_discussions(self):
        """Test GitHub discussions search returns helpful message."""
        result = await github_search("test", search_type="discussions")
        assert "GitHub Discussions search requires GraphQL API" in result
        assert "browse discussions directly" in result
        assert "https://github.com/NixOS/nixpkgs/discussions" in result

    @pytest.mark.asyncio
    async def test_github_search_rate_limit(self):
        """Test GitHub search rate limit handling."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(403, {})

            result = await github_search("test")
            assert "Error" in result
            assert "rate limit exceeded" in result

    @pytest.mark.asyncio
    async def test_github_search_no_results(self):
        """Test GitHub search with no results."""
        mock_response_data = {"total_count": 0, "items": []}

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await github_search("xyzabc123")

            assert "No issues found for 'xyzabc123'" in result
            assert "Try:" in result
            assert "Different keywords" in result
            assert "discourse_search()" in result

    @pytest.mark.asyncio
    async def test_github_search_custom_repo(self):
        """Test GitHub search with custom repository."""
        mock_response_data = {
            "total_count": 1,
            "items": [
                {
                    "number": 123,
                    "title": "Add flake support",
                    "state": "open",
                    "created_at": "2024-01-01T00:00:00Z",
                    "comments": 2,
                    "html_url": "https://github.com/nix-community/home-manager/issues/123",
                    "labels": [],
                }
            ],
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await github_search("flake", repo="nix-community/home-manager")

            assert "GitHub issues in nix-community/home-manager" in result
            assert "Add flake support" in result

    @pytest.mark.asyncio
    async def test_github_search_shows_total_count(self):
        """Test GitHub search shows total count when over limit."""
        mock_response_data = {
            "total_count": 150,
            "items": [
                {
                    "number": i,
                    "title": f"Issue {i}",
                    "state": "open",
                    "created_at": "2024-01-01T00:00:00Z",
                    "comments": 0,
                    "html_url": f"https://github.com/NixOS/nixpkgs/issues/{i}",
                    "labels": [],
                }
                for i in range(10)
            ],
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = create_mock_aiohttp_session(200, mock_response_data)

            result = await github_search("test", limit=10)

            assert "Showing 10 of 150 results" in result


@pytest.mark.integration
class TestDiscussionSearchIntegration:
    """Integration tests for discussion search tools."""

    @pytest.mark.asyncio
    async def test_real_discourse_search(self):
        """Test real Discourse API search."""
        result = await discourse_search("flakes", limit=3)

        # Basic validation - API should return something
        assert "NixOS Discourse discussions" in result or "No discussions found" in result or "Error" in result

        # If we get results, validate structure
        if "NixOS Discourse discussions" in result and "Error" not in result:
            assert "https://discourse.nixos.org/t/" in result
            assert "Posts:" in result

    @pytest.mark.asyncio
    async def test_real_github_search(self):
        """Test real GitHub API search."""
        result = await github_search("segfault", repo="NixOS/nixpkgs", limit=3)

        # Basic validation - should get something back
        assert "GitHub issues" in result or "No issues found" in result or "rate limit" in result or "Error" in result

        # If we get results, validate structure
        if "GitHub issues" in result and "rate limit" not in result and "Error" not in result:
            assert "#" in result  # Issue numbers
            assert "https://github.com/" in result


@pytest.mark.unit
class TestHelpToolUpdate:
    """Test that help tool includes new discussion tools."""

    @pytest.mark.asyncio
    async def test_help_includes_discussion_tools(self):
        """Test help tool lists discussion search tools."""
        help_fn = get_tool_function("help")
        result = await help_fn()

        assert "COMMUNITY & HELP" in result
        assert "discourse_search" in result
        assert "github_search" in result
        assert "Search forum" in result
        assert "Search issues/PRs" in result
