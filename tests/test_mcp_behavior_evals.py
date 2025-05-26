#!/usr/bin/env python3
"""MCP behavior evaluation tests for real-world usage scenarios."""

import pytest
from typing import Dict


class MockAssistant:
    """Mock AI assistant for testing MCP tool usage patterns."""

    def __init__(self):
        self.tool_calls = []
        self.responses = []

    def use_tool(self, tool_name: str, **kwargs) -> str:
        """Simulate using an MCP tool."""
        from mcp_nixos import server

        self.tool_calls.append({"tool": tool_name, "args": kwargs})

        # Call the actual tool
        tool_func = getattr(server, tool_name)
        result = tool_func(**kwargs)
        self.responses.append(result)
        return result

    def analyze_response(self, response: str) -> Dict[str, bool | int]:
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

    def test_scenario_install_package(self):
        """User wants to install a specific package."""
        assistant = MockAssistant()

        # Step 1: Search for the package
        response1 = assistant.use_tool("nixos_search", query="neovim", search_type="packages", limit=5)
        analysis1 = assistant.analyze_response(response1)

        assert analysis1["has_results"] or analysis1["mentions_not_found"]
        assert not analysis1["is_error"]

        # Step 2: Get detailed info if found
        if analysis1["has_results"]:
            response2 = assistant.use_tool("nixos_info", name="neovim", type="package")
            analysis2 = assistant.analyze_response(response2)

            assert "Package:" in response2
            assert "Version:" in response2
            assert not analysis2["is_error"]

        # Verify tool usage pattern
        assert len(assistant.tool_calls) >= 1
        assert assistant.tool_calls[0]["tool"] == "nixos_search"

    def test_scenario_configure_service(self):
        """User wants to configure a NixOS service."""
        assistant = MockAssistant()

        # Step 1: Search for service options
        response1 = assistant.use_tool("nixos_search", query="nginx", search_type="options", limit=10)

        # Step 2: Get specific option details
        if "services.nginx.enable" in response1:
            response2 = assistant.use_tool("nixos_info", name="services.nginx.enable", type="option")

            assert "Type: boolean" in response2
            assert "Default:" in response2

    def test_scenario_explore_home_manager(self):
        """User wants to explore Home Manager configuration."""
        assistant = MockAssistant()

        # Step 1: List categories
        response1 = assistant.use_tool("home_manager_list_options")
        assert "programs" in response1
        assert "services" in response1

        # Step 2: Explore programs category
        assistant.use_tool("home_manager_options_by_prefix", option_prefix="programs")

        # Step 3: Search for specific program
        response3 = assistant.use_tool("home_manager_search", query="firefox", limit=5)

        # Step 4: Get details on specific option
        if "programs.firefox.enable" in response3:
            response4 = assistant.use_tool("home_manager_info", name="programs.firefox.enable")
            assert "Option:" in response4

    def test_scenario_macos_configuration(self):
        """User wants to configure macOS with nix-darwin."""
        assistant = MockAssistant()

        # Step 1: Search for Homebrew integration
        assistant.use_tool("darwin_search", query="homebrew", limit=10)

        # Step 2: Explore system defaults
        response2 = assistant.use_tool("darwin_options_by_prefix", option_prefix="system.defaults")

        # Step 3: Get specific dock settings
        if "system.defaults.dock" in response2:
            response3 = assistant.use_tool("darwin_options_by_prefix", option_prefix="system.defaults.dock")

            # Check for autohide option
            if "autohide" in response3:
                response4 = assistant.use_tool("darwin_info", name="system.defaults.dock.autohide")
                assert "Option:" in response4

    def test_scenario_compare_channels(self):
        """User wants to compare packages across channels."""
        assistant = MockAssistant()

        package = "postgresql"
        channels = ["unstable", "stable"]

        results = {}
        for channel in channels:
            response = assistant.use_tool("nixos_info", name=package, type="package", channel=channel)
            if "Version:" in response:
                # Extract version
                for line in response.split("\n"):
                    if line.startswith("Version:"):
                        results[channel] = line.split("Version:")[1].strip()

        # User can now compare versions across channels
        assert len(assistant.tool_calls) == len(channels)

    def test_scenario_find_package_by_program(self):
        """User wants to find which package provides a specific program."""
        assistant = MockAssistant()

        # Search for package that provides 'gcc'
        response = assistant.use_tool("nixos_search", query="gcc", search_type="programs", limit=10)

        analysis = assistant.analyze_response(response)
        if analysis["has_results"]:
            assert "provided by" in response
            assert "gcc" in response.lower()

    def test_scenario_complex_option_exploration(self):
        """User wants to understand complex NixOS options."""
        assistant = MockAssistant()

        # Look for virtualisation options
        response1 = assistant.use_tool("nixos_search", query="virtualisation.docker", search_type="options", limit=20)

        if "virtualisation.docker.enable" in response1:
            # Get details on enable option
            assistant.use_tool("nixos_info", name="virtualisation.docker.enable", type="option")

            # Search for related options
            assistant.use_tool("nixos_search", query="docker", search_type="options", limit=10)

            # Verify we get comprehensive docker configuration options
            assert any(r for r in assistant.responses if "docker" in r.lower())

    def test_scenario_git_configuration(self):
        """User wants to configure git with Home Manager."""
        assistant = MockAssistant()

        # Explore git options
        response1 = assistant.use_tool("home_manager_options_by_prefix", option_prefix="programs.git")

        # Count git-related options
        git_options = response1.count("programs.git")
        assert git_options > 10  # Git should have many options

        # Look for specific features
        features = ["delta", "lfs", "signing", "aliases"]
        found_features = sum(1 for f in features if f in response1)
        assert found_features >= 2  # Should find at least some features

    def test_scenario_error_recovery(self):
        """Test how tools handle errors and guide users."""
        assistant = MockAssistant()

        # Try invalid channel
        response1 = assistant.use_tool("nixos_search", query="test", channel="invalid-channel")
        assert "Error" in response1
        assert "Invalid channel" in response1

        # Try non-existent package
        response2 = assistant.use_tool("nixos_info", name="definitely-not-a-real-package-12345", type="package")
        assert "not found" in response2.lower()

        # Try invalid type
        response3 = assistant.use_tool("nixos_search", query="test", search_type="invalid-type")
        assert "Error" in response3
        assert "Invalid type" in response3

    def test_scenario_bulk_option_discovery(self):
        """User wants to discover all options for a service."""
        assistant = MockAssistant()

        # Search for all nginx options
        response1 = assistant.use_tool("nixos_search", query="services.nginx", search_type="options", limit=50)

        if "Found" in response1:
            # Count unique option types
            option_types = set()
            for line in response1.split("\n"):
                if "Type:" in line:
                    option_type = line.split("Type:")[1].strip()
                    option_types.add(option_type)

            # nginx should have various option types
            assert len(option_types) >= 2

    def test_scenario_multi_tool_workflow(self):
        """Test realistic multi-step workflows."""
        assistant = MockAssistant()

        # Workflow: Set up a development environment

        # 1. Check statistics
        stats = assistant.use_tool("nixos_stats")
        assert "Packages:" in stats

        # 2. Search for development tools
        dev_tools = ["vscode", "git", "docker", "nodejs"]
        for tool in dev_tools[:2]:  # Test first two to save time
            response = assistant.use_tool("nixos_search", query=tool, search_type="packages", limit=3)
            if "Found" in response:
                # Get info on first result
                package_name = None
                for line in response.split("\n"):
                    if line.startswith("•"):
                        # Extract package name
                        package_name = line.split("•")[1].split("(")[0].strip()
                        break

                if package_name:
                    info = assistant.use_tool("nixos_info", name=package_name, type="package")
                    assert "Package:" in info

        # 3. Configure git in Home Manager
        assistant.use_tool("home_manager_search", query="git", limit=10)

        # Verify workflow completed
        assert len(assistant.tool_calls) >= 4
        assert not any("Error" in r for r in assistant.responses[:3])  # First 3 should succeed

    def test_scenario_performance_monitoring(self):
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
                assistant.use_tool(op_name, **op_args)
                elapsed = time.time() - start
                timings[op_name] = elapsed
            except Exception:
                timings[op_name] = -1

        # All operations should complete reasonably quickly
        for op, timing in timings.items():
            if timing > 0:
                assert timing < 30, f"{op} took too long: {timing}s"

    def test_scenario_option_value_types(self):
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
            response = assistant.use_tool("nixos_search", query=search_term, search_type="options", limit=5)
            if "Type:" in response:
                found_types[type_name] = response

        # Should find at least some different types
        assert len(found_types) >= 2
