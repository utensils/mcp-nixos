#!/usr/bin/env python3
"""MCP behavior evaluation tests for real-world usage scenarios."""

from unittest.mock import Mock, patch

import pytest
from mcp_nixos import server


def get_tool_function(tool_name: str):
    """Get the underlying function from a FastMCP tool."""
    tool = getattr(server, tool_name)
    if hasattr(tool, "fn"):
        return tool.fn
    return tool


# Get the underlying functions for direct use
darwin_info = get_tool_function("darwin_info")
darwin_options_by_prefix = get_tool_function("darwin_options_by_prefix")
darwin_search = get_tool_function("darwin_search")
darwin_stats = get_tool_function("darwin_stats")
home_manager_info = get_tool_function("home_manager_info")
home_manager_list_options = get_tool_function("home_manager_list_options")
home_manager_options_by_prefix = get_tool_function("home_manager_options_by_prefix")
home_manager_search = get_tool_function("home_manager_search")
home_manager_stats = get_tool_function("home_manager_stats")
nixos_channels = get_tool_function("nixos_channels")
nixos_info = get_tool_function("nixos_info")
nixos_search = get_tool_function("nixos_search")
nixos_stats = get_tool_function("nixos_stats")


class MockAssistant:
    """Mock AI assistant for testing MCP tool usage patterns."""

    def __init__(self):
        self.tool_calls = []
        self.responses = []

    async def use_tool(self, tool_name: str, **kwargs) -> str:
        """Simulate using an MCP tool."""
        from mcp_nixos import server

        self.tool_calls.append({"tool": tool_name, "args": kwargs})

        # Call the actual tool - get the underlying function from FastMCP tool
        tool_func = getattr(server, tool_name)
        if hasattr(tool_func, "fn"):
            # FastMCP wrapped function - use the underlying function
            result = await tool_func.fn(**kwargs)
        else:
            # Direct function call
            result = await tool_func(**kwargs)
        self.responses.append(result)
        return result

    def analyze_response(self, response: str) -> dict[str, bool | int]:
        """Analyze tool response for key information."""
        analysis = {
            "has_results": "Found" in response or ":" in response,
            "is_error": "Error" in response,
            "has_bullet_points": "•" in response,
            "line_count": len(response.strip().split("\n")),
            "mentions_not_found": "not found" in response.lower(),
        }
        return analysis


@pytest.mark.evals
class TestMCPBehaviorEvals:
    """Test MCP tool behavior in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_scenario_install_package(self):
        """User wants to install a specific package."""
        assistant = MockAssistant()

        # Step 1: Search for the package
        response1 = await assistant.use_tool("nixos_search", query="neovim", search_type="packages", limit=5)
        analysis1 = assistant.analyze_response(response1)

        assert analysis1["has_results"] or analysis1["mentions_not_found"]
        assert not analysis1["is_error"]

        # Step 2: Get detailed info if found
        if analysis1["has_results"]:
            response2 = await assistant.use_tool("nixos_info", name="neovim", type="package")
            analysis2 = assistant.analyze_response(response2)

            assert "Package:" in response2
            assert "Version:" in response2
            assert not analysis2["is_error"]

        # Verify tool usage pattern
        assert len(assistant.tool_calls) >= 1
        assert assistant.tool_calls[0]["tool"] == "nixos_search"

    @pytest.mark.asyncio
    async def test_scenario_configure_service(self):
        """User wants to configure a NixOS service."""
        assistant = MockAssistant()

        # Step 1: Search for service options
        response1 = await assistant.use_tool("nixos_search", query="nginx", search_type="options", limit=10)

        # Step 2: Get specific option details
        if "services.nginx.enable" in response1:
            response2 = await assistant.use_tool("nixos_info", name="services.nginx.enable", type="option")

            assert "Type: boolean" in response2
            assert "Default:" in response2

    @pytest.mark.asyncio
    async def test_scenario_explore_home_manager(self):
        """User wants to explore Home Manager configuration."""
        assistant = MockAssistant()

        # Step 1: List categories
        response1 = await assistant.use_tool("home_manager_list_options")
        assert "programs" in response1
        assert "services" in response1

        # Step 2: Explore programs category
        await assistant.use_tool("home_manager_options_by_prefix", option_prefix="programs")

        # Step 3: Search for specific program
        response3 = await assistant.use_tool("home_manager_search", query="firefox", limit=5)

        # Step 4: Get details on specific option
        if "programs.firefox.enable" in response3:
            response4 = await assistant.use_tool("home_manager_info", name="programs.firefox.enable")
            assert "Option:" in response4

    @pytest.mark.asyncio
    async def test_scenario_macos_configuration(self):
        """User wants to configure macOS with nix-darwin."""
        assistant = MockAssistant()

        # Step 1: Search for Homebrew integration
        await assistant.use_tool("darwin_search", query="homebrew", limit=10)

        # Step 2: Explore system defaults
        response2 = await assistant.use_tool("darwin_options_by_prefix", option_prefix="system.defaults")

        # Step 3: Get specific dock settings
        if "system.defaults.dock" in response2:
            response3 = await assistant.use_tool("darwin_options_by_prefix", option_prefix="system.defaults.dock")

            # Check for autohide option
            if "autohide" in response3:
                response4 = await assistant.use_tool("darwin_info", name="system.defaults.dock.autohide")
                assert "Option:" in response4

    @pytest.mark.asyncio
    async def test_scenario_compare_channels(self):
        """User wants to compare packages across channels."""
        assistant = MockAssistant()

        package = "postgresql"
        channels = ["unstable", "stable"]

        results = {}
        for channel in channels:
            response = await assistant.use_tool("nixos_info", name=package, type="package", channel=channel)
            if "Version:" in response:
                # Extract version
                for line in response.split("\n"):
                    if line.startswith("Version:"):
                        results[channel] = line.split("Version:")[1].strip()

        # User can now compare versions across channels
        assert len(assistant.tool_calls) == len(channels)

    @pytest.mark.asyncio
    async def test_scenario_find_package_by_program(self):
        """User wants to find which package provides a specific program."""
        assistant = MockAssistant()

        # Search for package that provides 'gcc'
        response = await assistant.use_tool("nixos_search", query="gcc", search_type="programs", limit=10)

        analysis = assistant.analyze_response(response)
        if analysis["has_results"]:
            assert "provided by" in response
            assert "gcc" in response.lower()

    @pytest.mark.asyncio
    async def test_scenario_complex_option_exploration(self):
        """User wants to understand complex NixOS options."""
        assistant = MockAssistant()

        # Look for virtualisation options
        response1 = await assistant.use_tool(
            "nixos_search", query="virtualisation.docker", search_type="options", limit=20
        )

        if "virtualisation.docker.enable" in response1:
            # Get details on enable option
            await assistant.use_tool("nixos_info", name="virtualisation.docker.enable", type="option")

            # Search for related options
            await assistant.use_tool("nixos_search", query="docker", search_type="options", limit=10)

            # Verify we get comprehensive docker configuration options
            assert any(r for r in assistant.responses if "docker" in r.lower())

    @pytest.mark.asyncio
    async def test_scenario_git_configuration(self):
        """User wants to configure git with Home Manager."""
        assistant = MockAssistant()

        # Explore git options
        response1 = await assistant.use_tool("home_manager_options_by_prefix", option_prefix="programs.git")

        # Count git-related options
        git_options = response1.count("programs.git")
        assert git_options > 10  # Git should have many options

        # Look for specific features
        features = ["delta", "lfs", "signing", "aliases"]
        found_features = sum(1 for f in features if f in response1)
        assert found_features >= 2  # Should find at least some features

    @pytest.mark.asyncio
    async def test_scenario_error_recovery(self):
        """Test how tools handle errors and guide users."""
        assistant = MockAssistant()

        # Try invalid channel
        response1 = await assistant.use_tool("nixos_search", query="test", channel="invalid-channel")
        assert "Error" in response1
        assert "Invalid channel" in response1

        # Try non-existent package
        response2 = await assistant.use_tool("nixos_info", name="definitely-not-a-real-package-12345", type="package")
        assert "not found" in response2.lower()

        # Try invalid type
        response3 = await assistant.use_tool("nixos_search", query="test", search_type="invalid-type")
        assert "Error" in response3
        assert "Invalid type" in response3

    @pytest.mark.asyncio
    async def test_scenario_bulk_option_discovery(self):
        """User wants to discover all options for a service."""
        assistant = MockAssistant()

        # Search for all nginx options
        response1 = await assistant.use_tool("nixos_search", query="services.nginx", search_type="options", limit=50)

        if "Found" in response1:
            # Count unique option types
            option_types = set()
            for line in response1.split("\n"):
                if "Type:" in line:
                    option_type = line.split("Type:")[1].strip()
                    option_types.add(option_type)

            # nginx should have various option types
            assert len(option_types) >= 2

    @pytest.mark.asyncio
    async def test_scenario_multi_tool_workflow(self):
        """Test realistic multi-step workflows."""
        assistant = MockAssistant()

        # Workflow: Set up a development environment

        # 1. Check statistics
        stats = await assistant.use_tool("nixos_stats")
        assert "Packages:" in stats

        # 2. Search for development tools
        dev_tools = ["vscode", "git", "docker", "nodejs"]
        for tool in dev_tools[:2]:  # Test first two to save time
            response = await assistant.use_tool("nixos_search", query=tool, search_type="packages", limit=3)
            if "Found" in response:
                # Get info on first result
                package_name = None
                for line in response.split("\n"):
                    if line.startswith("•"):
                        # Extract package name
                        package_name = line.split("•")[1].split("(")[0].strip()
                        break

                if package_name:
                    info = await assistant.use_tool("nixos_info", name=package_name, type="package")
                    assert "Package:" in info

        # 3. Configure git in Home Manager
        await assistant.use_tool("home_manager_search", query="git", limit=10)

        # Verify workflow completed
        assert len(assistant.tool_calls) >= 4
        assert not any("Error" in r for r in assistant.responses[:3])  # First 3 should succeed

    @pytest.mark.asyncio
    async def test_scenario_performance_monitoring(self):
        """Monitor performance characteristics of tool calls."""
        import time

        assistant = MockAssistant()
        timings = {}

        # Time different operations
        operations = [
            ("nixos_stats", {}),
            ("nixos_search", {"query": "python", "limit": 20}),
            ("home_manager_list_options", {}),
            ("darwin_search", {"query": "system", "limit": 10}),
        ]

        for op_name, op_args in operations:
            start = time.time()
            try:
                await assistant.use_tool(op_name, **op_args)
                elapsed = time.time() - start
                timings[op_name] = elapsed
            except Exception:
                timings[op_name] = -1

        # All operations should complete reasonably quickly
        for op, timing in timings.items():
            if timing > 0:
                assert timing < 30, f"{op} took too long: {timing}s"

    @pytest.mark.asyncio
    async def test_scenario_option_value_types(self):
        """Test understanding different option value types."""
        assistant = MockAssistant()

        # Search for options with different types
        type_examples = {
            "boolean": "enable",
            "string": "description",
            "list": "allowedTCPPorts",
            "attribute set": "extraConfig",
        }

        found_types = {}
        for type_name, search_term in type_examples.items():
            response = await assistant.use_tool("nixos_search", query=search_term, search_type="options", limit=5)
            if "Type:" in response:
                found_types[type_name] = response

        # Should find at least some different types
        assert len(found_types) >= 2


# ===== Content from test_mcp_behavior_comprehensive.py =====
class TestMCPBehaviorComprehensive:
    """Test real-world usage patterns based on actual tool testing results."""

    @pytest.mark.asyncio
    async def test_nixos_package_discovery_flow(self):
        """Test typical package discovery workflow."""
        # 1. Search for packages
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                    }
                },
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "gitoxide",
                        "package_pversion": "0.40.0",
                        "package_description": "Rust implementation of Git",
                    }
                },
            ]

            result = await nixos_search("git", limit=5)
            assert "git (2.49.0)" in result
            assert "Distributed version control system" in result
            assert "gitoxide" in result

        # 2. Get detailed info about a specific package
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = [
                {
                    "_source": {
                        "type": "package",
                        "package_pname": "git",
                        "package_pversion": "2.49.0",
                        "package_description": "Distributed version control system",
                        "package_homepage": ["https://git-scm.com/"],
                        "package_license_set": ["GNU General Public License v2.0"],
                    }
                }
            ]

            result = await nixos_info("git")
            assert "Package: git" in result
            assert "Version: 2.49.0" in result
            assert "Homepage: https://git-scm.com/" in result
            assert "License: GNU General Public License v2.0" in result

    @pytest.mark.asyncio
    async def test_nixos_channel_awareness(self):
        """Test channel discovery and usage."""
        # 1. List available channels
        with patch("mcp_nixos.server.channel_cache.get_available") as mock_discover:
            mock_discover.return_value = {
                "latest-43-nixos-unstable": "151,798 documents",
                "latest-43-nixos-25.05": "151,698 documents",
                "latest-43-nixos-24.11": "142,034 documents",
            }

            result = await nixos_channels()
            assert "NixOS Channels" in result
            assert "stable (current: 25.05)" in result
            assert "unstable" in result
            assert "✓ Available" in result

        # 2. Get stats for a channel
        with patch("requests.post") as mock_post:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.side_effect = [
                {"count": 129865},  # packages
                {"count": 21933},  # options
            ]
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            result = await nixos_stats()
            assert "NixOS Statistics" in result
            assert "129,865" in result
            assert "21,933" in result

    @pytest.mark.asyncio
    async def test_home_manager_option_discovery_flow(self):
        """Test typical Home Manager option discovery workflow."""
        # 1. Search for options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Default Git username",
                },
                {
                    "name": "programs.git.userEmail",
                    "type": "string",
                    "description": "Default Git email",
                },
            ]

            result = await home_manager_search("git", limit=3)
            assert "programs.git.enable" in result
            assert "programs.git.userName" in result
            assert "programs.git.userEmail" in result

        # 2. Browse by prefix to find exact option names
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.aliases",
                    "type": "attribute set of string",
                    "description": "Git aliases",
                },
                {
                    "name": "programs.git.delta.enable",
                    "type": "boolean",
                    "description": "Whether to enable delta syntax highlighting",
                },
            ]

            result = await home_manager_options_by_prefix("programs.git")
            assert "programs.git.enable" in result
            assert "programs.git.aliases" in result
            assert "programs.git.delta.enable" in result

        # 3. Get specific option info (requires exact name)
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                }
            ]

            result = await home_manager_info("programs.git.enable")
            assert "Option: programs.git.enable" in result
            assert "Type: boolean" in result
            assert "Whether to enable Git" in result

    @pytest.mark.asyncio
    async def test_home_manager_category_exploration(self):
        """Test exploring Home Manager categories."""
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Simulate real category distribution
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "", "description": ""},
                {"name": "programs.vim.enable", "type": "", "description": ""},
                {"name": "services.gpg-agent.enable", "type": "", "description": ""},
                {"name": "home.packages", "type": "", "description": ""},
                {"name": "accounts.email.accounts", "type": "", "description": ""},
            ]

            result = await home_manager_list_options()
            assert "Home Manager option categories" in result
            assert "programs (2 options)" in result
            assert "services (1 options)" in result
            assert "home (1 options)" in result
            assert "accounts (1 options)" in result

    @pytest.mark.asyncio
    async def test_darwin_system_configuration_flow(self):
        """Test typical Darwin configuration workflow."""
        # 1. Search for system options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "system.defaults.dock.autohide",
                    "type": "boolean",
                    "description": "Whether to automatically hide the dock",
                },
                {
                    "name": "system.defaults.NSGlobalDomain.AppleInterfaceStyle",
                    "type": "string",
                    "description": "Set to 'Dark' to enable dark mode",
                },
                {
                    "name": "system.stateVersion",
                    "type": "string",
                    "description": "The nix-darwin state version",
                },
            ]

            result = await darwin_search("system", limit=3)
            assert "system.defaults.dock.autohide" in result
            assert "system.defaults.NSGlobalDomain.AppleInterfaceStyle" in result
            assert "system.stateVersion" in result

        # 2. Browse system options by prefix
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "system.defaults.dock.autohide",
                    "type": "boolean",
                    "description": "Whether to automatically hide the dock",
                },
                {
                    "name": "system.defaults.dock.autohide-delay",
                    "type": "float",
                    "description": "Dock autohide delay",
                },
                {
                    "name": "system.defaults.dock.orientation",
                    "type": "string",
                    "description": "Dock position on screen",
                },
            ]

            result = await darwin_options_by_prefix("system.defaults.dock")
            assert "system.defaults.dock.autohide" in result
            assert "system.defaults.dock.autohide-delay" in result
            assert "system.defaults.dock.orientation" in result

    @pytest.mark.asyncio
    async def test_error_handling_with_suggestions(self):
        """Test error handling provides helpful suggestions."""
        # Invalid channel
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-43-nixos-25.05",
                "unstable": "latest-43-nixos-unstable",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
            }

            result = await nixos_search("test", channel="24.05")
            assert "Invalid channel" in result
            assert "Available channels:" in result
            assert "24.11" in result or "25.05" in result

    @pytest.mark.asyncio
    async def test_cross_tool_consistency(self):
        """Test that different tools provide consistent information."""
        # Channel consistency
        with patch("mcp_nixos.server.get_channels") as mock_get:
            channels = {
                "stable": "latest-43-nixos-25.05",
                "unstable": "latest-43-nixos-unstable",
                "25.05": "latest-43-nixos-25.05",
                "beta": "latest-43-nixos-25.05",
            }
            mock_get.return_value = channels

            # All tools should accept the same channels
            for channel in ["stable", "unstable", "25.05", "beta"]:
                with patch("mcp_nixos.server.es_query") as mock_es:
                    mock_es.return_value = []
                    result = await nixos_search("test", channel=channel)
                    assert "Error" not in result or "Invalid channel" not in result

    @pytest.mark.asyncio
    async def test_real_world_git_configuration_scenario(self):
        """Test a complete Git configuration discovery scenario."""
        # User wants to configure Git in Home Manager

        # Step 1: Search for git-related options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Default Git username",
                },
            ]

            result = await home_manager_search("git user")
            assert "programs.git.userName" in result

        # Step 2: Browse all git options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {"name": "programs.git.enable", "type": "boolean", "description": "Whether to enable Git"},
                {"name": "programs.git.userName", "type": "string", "description": "Default Git username"},
                {"name": "programs.git.userEmail", "type": "string", "description": "Default Git email"},
                {"name": "programs.git.signing.key", "type": "string", "description": "GPG signing key"},
                {
                    "name": "programs.git.signing.signByDefault",
                    "type": "boolean",
                    "description": "Sign commits by default",
                },
            ]

            result = await home_manager_options_by_prefix("programs.git")
            assert "programs.git.userName" in result
            assert "programs.git.userEmail" in result
            assert "programs.git.signing.key" in result

        # Step 3: Get details for specific options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = [
                {
                    "name": "programs.git.signing.signByDefault",
                    "type": "boolean",
                    "description": "Whether to sign commits by default",
                }
            ]

            result = await home_manager_info("programs.git.signing.signByDefault")
            assert "Type: boolean" in result
            assert "sign commits by default" in result

    @pytest.mark.asyncio
    async def test_performance_with_large_result_sets(self):
        """Test handling of large result sets efficiently."""
        # Home Manager has 2000+ options
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            # Simulate large option set
            mock_options = []
            for i in range(2129):  # Actual count from testing
                mock_options.append(
                    {
                        "name": f"programs.option{i}",
                        "type": "string",
                        "description": f"Option {i}",
                    }
                )
            mock_parse.return_value = mock_options

            result = await home_manager_list_options()
            assert "2129 options" in result or "programs (" in result

    @pytest.mark.asyncio
    async def test_package_not_found_behavior(self):
        """Test behavior when packages/options are not found."""
        # Package not found
        with patch("mcp_nixos.server.es_query") as mock_es:
            mock_es.return_value = []

            result = await nixos_info("nonexistent-package")
            assert "not found" in result.lower()

        # Option not found
        with patch("mcp_nixos.server.parse_html_options") as mock_parse:
            mock_parse.return_value = []

            result = await home_manager_info("nonexistent.option")
            assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_channel_migration_scenario(self):
        """Test that users can migrate from old to new channels."""
        # User on 24.11 wants to upgrade to 25.05
        with patch("mcp_nixos.server.get_channels") as mock_get:
            mock_get.return_value = {
                "stable": "latest-43-nixos-25.05",
                "25.05": "latest-43-nixos-25.05",
                "24.11": "latest-43-nixos-24.11",
                "unstable": "latest-43-nixos-unstable",
            }

            # Can still query old channel
            with patch("mcp_nixos.server.es_query") as mock_es:
                mock_es.return_value = []
                result = await nixos_search("test", channel="24.11")
                assert "Error" not in result or "Invalid channel" not in result

            # Can query new stable
            with patch("mcp_nixos.server.es_query") as mock_es:
                mock_es.return_value = []
                result = await nixos_search("test", channel="stable")
                assert "Error" not in result or "Invalid channel" not in result

    @pytest.mark.asyncio
    async def test_option_type_information(self):
        """Test that option type information is properly displayed."""
        test_cases = [
            ("boolean option", "boolean", "programs.git.enable"),
            ("string option", "string", "programs.git.userName"),
            ("attribute set", "attribute set of string", "programs.git.aliases"),
            ("list option", "list of string", "home.packages"),
            ("complex type", "null or string or signed integer", "services.dunst.settings.global.offset"),
        ]

        for desc, type_str, option_name in test_cases:
            with patch("mcp_nixos.server.parse_html_options") as mock_parse:
                mock_parse.return_value = [
                    {
                        "name": option_name,
                        "type": type_str,
                        "description": f"Test {desc}",
                    }
                ]

                result = await home_manager_info(option_name)
                assert f"Type: {type_str}" in result

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.parse_html_options")
    async def test_stats_functions_limitations(self, mock_parse):
        """Test that stats functions return actual statistics now."""
        # Mock parsed options for Home Manager
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg-agent.enable", "type": "boolean", "description": "Enable GPG agent"},
            {"name": "home.packages", "type": "list", "description": "Packages to install"},
            {"name": "wayland.windowManager.sway.enable", "type": "boolean", "description": "Enable Sway"},
            {"name": "xsession.enable", "type": "boolean", "description": "Enable X session"},
        ]

        # Home Manager stats now return actual statistics
        result = await home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result

        # Mock parsed options for Darwin
        mock_parse.return_value = [
            {"name": "services.nix-daemon.enable", "type": "boolean", "description": "Enable nix-daemon"},
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            {"name": "launchd.agents.test", "type": "attribute set", "description": "Launchd agents"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "homebrew.enable", "type": "boolean", "description": "Enable Homebrew"},
        ]

        # Darwin stats now return actual statistics
        result = await darwin_stats()
        assert "nix-darwin Statistics:" in result
        assert "Total options:" in result
        assert "Categories:" in result
        assert "Top categories:" in result
