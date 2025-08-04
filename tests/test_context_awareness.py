"""Tests for context awareness and improvements from Claude Code Task."""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos import server
from mcp_nixos.server import NixOSContext, get_did_you_mean_suggestions


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
search = get_tool_function("search")
show = get_tool_function("show")
install = get_tool_function("install")
versions = get_tool_function("versions")
compare = get_tool_function("compare")
which = get_tool_function("which")


@pytest.mark.unit
class TestNixOSContext:
    """Test the NixOSContext class."""

    def test_context_initialization(self):
        """Test context initializes with proper defaults."""
        ctx = NixOSContext()
        assert ctx.last_search_results == []
        assert ctx.last_search_query == ""
        assert ctx.last_search_type == ""
        assert ctx.last_package_name is None
        assert ctx.last_channel == "unstable"
        assert ctx.user_preferences["verbosity"] == "normal"
        assert ctx.user_preferences["default_install_method"] == "user"

    def test_update_search_context(self):
        """Test updating search context."""
        ctx = NixOSContext()
        mock_hits = [
            {"_source": {"package_pname": "firefox", "package_pversion": "121.0"}},
            {"_source": {"package_pname": "firefox-esr", "package_pversion": "115.0"}},
        ]

        ctx.update_search_context("firefox", "packages", mock_hits)

        assert ctx.last_search_query == "firefox"
        assert ctx.last_search_type == "packages"
        assert len(ctx.last_search_results) == 2
        assert ctx.last_package_name == "firefox"

    def test_get_result_by_index(self):
        """Test getting search result by index."""
        ctx = NixOSContext()
        mock_hits = [
            {"_source": {"package_pname": "git", "package_pversion": "2.43"}},
            {"_source": {"package_pname": "gitoxide", "package_pversion": "0.40"}},
        ]
        ctx.update_search_context("git", "packages", mock_hits)

        # Test valid indices (1-based)
        result1 = ctx.get_result_by_index(1)
        assert result1 is not None
        assert result1["_source"]["package_pname"] == "git"

        result2 = ctx.get_result_by_index(2)
        assert result2 is not None
        assert result2["_source"]["package_pname"] == "gitoxide"

        # Test invalid indices
        assert ctx.get_result_by_index(0) is None  # 0 is invalid (1-based)
        assert ctx.get_result_by_index(10) is None

    def test_get_recent_package(self):
        """Test getting recent package from context."""
        ctx = NixOSContext()
        mock_hits = [
            {"_source": {"package_pname": "neovim"}},
            {"_source": {"package_pname": "vim"}},
        ]
        ctx.update_search_context("editor", "packages", mock_hits)

        # Test with name provided
        assert ctx.get_recent_package("firefox") == "firefox"

        # Test without name (should use last package)
        assert ctx.get_recent_package() == "neovim"

        # Test with single result - need to reset the search type
        ctx.last_search_results = [{"_source": {"package_pname": "emacs"}}]
        ctx.last_package_name = None  # Reset to force checking single result
        assert ctx.get_recent_package() == "emacs"

    def test_user_preferences(self):
        """Test user preferences in context."""
        ctx = NixOSContext()

        # Test default preferences
        assert ctx.user_preferences["verbosity"] == "normal"
        assert ctx.user_preferences["default_install_method"] == "user"

        # Test direct modification (since there's no set_preference method)
        ctx.user_preferences["verbosity"] = "concise"
        assert ctx.user_preferences["verbosity"] == "concise"


@pytest.mark.unit
class TestDidYouMeanSuggestions:
    """Test the did-you-mean suggestions."""

    def test_package_suggestions(self):
        """Test suggestions for package searches."""
        suggestions = get_did_you_mean_suggestions("neovim", "packages")

        # Should suggest nvim and vim
        assert any("nvim" in s for s in suggestions)
        assert any("vim" in s for s in suggestions)
        assert any("programs" in s for s in suggestions)
        assert any("which" in s for s in suggestions)

    def test_common_misspellings(self):
        """Test suggestions for common misspellings."""
        # Test postgres -> postgresql
        suggestions = get_did_you_mean_suggestions("postgres", "packages")
        assert any("postgresql" in s for s in suggestions)

        # Test node -> nodejs
        suggestions = get_did_you_mean_suggestions("node", "packages")
        assert any("nodejs" in s for s in suggestions)

        # Test python -> python3
        suggestions = get_did_you_mean_suggestions("python", "packages")
        assert any("python3" in s for s in suggestions)

    def test_option_suggestions(self):
        """Test suggestions for option searches."""
        suggestions = get_did_you_mean_suggestions("nginx", "options")

        assert any("dot notation" in s for s in suggestions)
        assert any("services.nginx" in s for s in suggestions)

    def test_program_suggestions(self):
        """Test suggestions for program searches."""
        suggestions = get_did_you_mean_suggestions("gcc", "programs")

        assert any("which" in s for s in suggestions)
        assert any("packages" in s for s in suggestions)


@pytest.mark.unit
class TestContextAwareTools:
    """Test context awareness in tools."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_search_updates_context(self, mock_es):
        """Test search updates context."""
        # Reset context
        server.context = NixOSContext()

        mock_es.return_value = [{"_source": {"package_pname": "firefox", "package_pversion": "121.0"}}]

        _ = await search("firefox")

        assert server.context.last_search_query == "firefox"
        assert server.context.last_package_name == "firefox"
        assert len(server.context.last_search_results) == 1

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_show_with_context(self, mock_es):
        """Test show using context from previous search."""
        # Setup context from a search
        server.context = NixOSContext()
        server.context.last_search_results = [
            {"name": "git", "_source": {"package_pname": "git"}},
            {"name": "gitoxide", "_source": {"package_pname": "gitoxide"}},
        ]
        server.context.last_package_name = "git"

        # Mock show response
        mock_es.return_value = [{"_source": {"package_pname": "gitoxide", "package_pversion": "0.40"}}]

        # Test show with index
        result = await show("2")  # Should resolve to gitoxide
        assert "gitoxide" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_install_with_context(self, mock_es):
        """Test install using context."""
        # Setup context with search results
        server.context = NixOSContext()
        server.context.last_search_results = [{"_source": {"package_pname": "firefox", "package_pversion": "121.0"}}]
        server.context.last_package_name = "firefox"
        server.context.last_search_type = "packages"

        mock_es.return_value = [{"_source": {"package_pname": "firefox", "package_pversion": "121.0"}}]

        # Test install without package name (uses context)
        result = await install()
        assert "firefox" in result
        assert "INSTALL:" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_versions_with_context(self, mock_es):
        """Test versions using context."""
        # Setup context
        server.context = NixOSContext()
        server.context.last_package_name = "ruby"

        # Test versions without package name
        with patch("requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 404  # Simulate not found
            mock_get.return_value = mock_resp

            result = await versions()
            assert "ruby" in result  # Should use context package name

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_compare_with_context(self, mock_es):
        """Test compare using context."""
        # Setup context
        server.context = NixOSContext()
        server.context.last_package_name = "postgresql"

        mock_es.return_value = []  # Empty result

        # Test compare without package name
        result = await compare()
        assert "postgresql" in result  # Should use context package name


@pytest.mark.unit
class TestConciseMode:
    """Test concise output mode."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_search_concise_mode(self, mock_es):
        """Test search with concise parameter."""
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "firefox",
                    "package_pversion": "121.0",
                    "package_description": "Mozilla Firefox web browser",
                }
            }
        ]

        # Normal mode
        result_normal = await search("firefox")
        assert "NEXT STEPS:" in result_normal

        # Concise mode
        result_concise = await search("firefox", concise=True)
        assert "NEXT STEPS:" not in result_concise
        assert "firefox (121.0)" in result_concise

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_show_concise_mode(self, mock_es):
        """Test show with concise parameter."""
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "git",
                    "package_pversion": "2.43.0",
                    "package_description": "Distributed version control system",
                    "package_homepage": ["https://git-scm.com"],
                }
            }
        ]

        result_concise = await show("git", concise=True)
        assert "NEXT STEPS:" not in result_concise
        assert "Name: git" in result_concise


@pytest.mark.unit
class TestPackageGrouping:
    """Test package version grouping in search."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_search_groups_versions(self, mock_es):
        """Test search groups multiple versions of same package."""
        mock_es.return_value = [
            {"_source": {"package_pname": "python3", "package_pversion": "3.11.8"}},
            {"_source": {"package_pname": "python3", "package_pversion": "3.12.1"}},
            {"_source": {"package_pname": "python3", "package_pversion": "3.10.13"}},
            {"_source": {"package_pname": "python2", "package_pversion": "2.7.18"}},
        ]

        result = await search("python")

        # Should group python3 versions
        assert "python3" in result
        assert "Versions: 3.11.8, 3.12.1, 3.10.13" in result
        # python2 should be separate
        assert "python2 (2.7.18)" in result
        # Should only have 2 package results (not 4) - count in the main results section
        # Split by NEXT STEPS to only count in results section
        results_section = result.split("NEXT STEPS")[0]
        assert results_section.count("•") == 2


@pytest.mark.unit
class TestImprovedWhichTool:
    """Test improvements to which tool."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_which_exact_match_priority(self, mock_es):
        """Test which prioritizes exact command matches."""
        # Mock will be called multiple times with different queries
        mock_es.side_effect = [
            # First call: programs query with boost
            [{"_source": {"package_pname": "ripgrep", "package_programs": ["rg"]}}],
            # Second call: wildcard query (fallback)
            [],
        ]

        result = await which("rg")

        assert "ripgrep" in result
        # Check for the actual format used by which tool
        assert "ripgrep" in result
        assert "Provides: rg" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_which_concise_mode(self, mock_es):
        """Test which with concise mode."""
        mock_es.return_value = [{"_source": {"package_pname": "git", "package_programs": ["git"]}}]

        result = await which("git", concise=True)

        assert "NEXT STEPS:" not in result
        assert "git" in result


@pytest.mark.unit
class TestInstallContextualMethod:
    """Test install tool's contextual method detection."""

    @patch("mcp_nixos.server.es_query")
    @patch("os.path.exists")
    @patch("os.getuid")
    @pytest.mark.asyncio
    async def test_install_detects_root_user(self, mock_uid, mock_exists, mock_es):
        """Test install detects root user and suggests system install."""
        mock_uid.return_value = 0  # Root user
        mock_exists.return_value = True  # /etc/nixos exists
        mock_es.return_value = [{"_source": {"package_pname": "htop", "package_pversion": "3.3.0"}}]

        result = await install("htop")

        # The detection message was removed in the refactor, check for system method
        assert "SYSTEM INSTALL" in result
        assert "system" in result  # Should suggest system install

    @patch("mcp_nixos.server.es_query")
    @patch("os.path.exists")
    @patch("os.getuid")
    @patch.dict("os.environ", {"HOME_MANAGER_CONFIG": "/home/user/.config/home-manager/home.nix"})
    @pytest.mark.asyncio
    async def test_install_detects_home_manager(self, mock_uid, mock_exists, mock_es):
        """Test install detects Home Manager configuration."""
        mock_uid.return_value = 1000  # Regular user
        mock_exists.return_value = False  # No /etc/nixos
        mock_es.return_value = [{"_source": {"package_pname": "neovim", "package_pversion": "0.9.5"}}]

        result = await install("neovim")

        # Check for home manager method being used
        assert "HOME MANAGER INSTALL" in result
        assert "home" in result


@pytest.mark.unit
class TestErrorMessagesWithSuggestions:
    """Test improved error messages."""

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_search_not_found_suggestions(self, mock_es):
        """Test search provides helpful suggestions when nothing found."""
        mock_es.return_value = []  # No results

        result = await search("neovim")

        assert "Error (NOT_FOUND):" in result
        assert "Try:" in result
        assert "nvim" in result or "vim" in result

    @patch("mcp_nixos.server.es_query")
    @pytest.mark.asyncio
    async def test_show_not_found_suggestions(self, mock_es):
        """Test show provides suggestions when package not found."""
        mock_es.return_value = []  # Not found

        result = await show("postgres")

        assert "Error (NOT_FOUND):" in result
        assert "postgresql" in result  # Should suggest postgresql
