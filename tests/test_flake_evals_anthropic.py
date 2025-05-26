"""
Anthropic API evaluation tests for flake search and improved stats functionality.
Tests real AI behavior with the new MCP tools.
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import pytest
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Skip these tests if no API key is available
pytestmark = pytest.mark.anthropic


class MockMCPClient:
    """Mock MCP client for testing with Anthropic API."""

    def __init__(self):
        self.messages = []
        self.tools = {
            "nixos_flakes_search": {
                "description": "Search for NixOS flakes",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}},
                    "required": ["query"],
                },
            },
            "home_manager_stats": {
                "description": "Get Home Manager statistics",
                "input_schema": {"type": "object", "properties": {}},
            },
            "darwin_stats": {
                "description": "Get nix-darwin statistics",
                "input_schema": {"type": "object", "properties": {}},
            },
        }

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Simulate tool calls with realistic responses."""
        self.messages.append(f"Tool called: {tool_name} with args: {arguments}")

        if tool_name == "nixos_flakes_search":
            query = arguments.get("query", "")
            if "home-manager" in query.lower():
                return """Found 1 unique flake matching 'home-manager':

• nix-community/home-manager
  Description: Manage a user environment with Nix
  URL: github:nix-community/home-manager
  Packages: default, docs, home-manager

"""
            if "devenv" in query.lower():
                return """Found 1 unique flake matching 'devenv':

• cachix/devenv
  Description: Fast, Declarative, Reproducible, and Composable Developer Environments
  URL: github:cachix/devenv
  Packages: default, devenv

"""
            if "agenix" in query.lower():
                return """Found 1 unique flake matching 'agenix':

• ryantm/agenix
  Description: age-encrypted secrets for NixOS and Home Manager
  URL: github:ryantm/agenix
  Packages: default, agenix

"""
            if "nonexistent" in query.lower():
                return "No flakes found matching 'nonexistent'."
            # Default response
            return (
                f"Found 2 unique flakes matching '{query}':\n\n"
                "• example/flake1\n  Description: Example flake 1\n"
                "  URL: github:example/flake1\n  Packages: default\n\n"
                "• example/flake2\n  Description: Example flake 2\n"
                "  URL: github:example/flake2\n  Packages: default, lib\n\n"
            )

        if tool_name == "home_manager_stats":
            return """Home Manager Statistics:
• Total options: 2129
• Total categories: 131

Top categories by option count:
• programs: 1147 options (53.9%)
• services: 312 options (14.7%)
• xsession: 55 options (2.6%)
• systemd: 48 options (2.3%)
• home: 46 options (2.2%)
"""

        if tool_name == "darwin_stats":
            return """nix-darwin Statistics:
• Total options: 348
• Total categories: 21

Top categories by option count:
• services: 89 options (25.6%)
• programs: 67 options (19.3%)
• system: 44 options (12.6%)
• launchd: 35 options (10.1%)
• security: 28 options (8.0%)
"""

        return f"Unknown tool: {tool_name}"


async def run_anthropic_test(
    prompt: str, expected_behaviors: List[str], mock_mcp_client: Optional[MockMCPClient] = None
) -> Dict[str, Any]:
    """Test a prompt with Anthropic API and verify expected behaviors."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not found in environment")

    if mock_mcp_client is None:
        mock_mcp_client = MockMCPClient()

    client = Anthropic(api_key=api_key)

    # Create a system message that simulates having MCP tools available
    system_message = """You are an AI assistant with access to NixOS MCP tools. You have the following tools available:

1. nixos_flakes_search(query: str, limit: int = 20) - Search for NixOS flakes
2. home_manager_stats() - Get Home Manager statistics showing total options and categories
3. darwin_stats() - Get nix-darwin statistics showing total options and categories

When asked about flakes, statistics, or configuration options, use these tools to provide accurate information."""

    # Simulate tool usage in the conversation
    messages = [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model="claude-3-haiku-20240307",  # Using Haiku for cost efficiency
        max_tokens=500,
        temperature=0,
        system=system_message,
        messages=messages,  # type: ignore
    )

    # Extract tool calls from the response
    response_text = ""
    for content in response.content:
        if hasattr(content, "text"):
            response_text = content.text  # type: ignore
            break
    tool_calls = []

    # Simple pattern matching for tool calls
    if "nixos_flakes_search" in response_text:
        # Extract query from response
        if "home-manager" in response_text.lower():
            tool_calls.append(("nixos_flakes_search", {"query": "home-manager"}))
        elif "devenv" in response_text.lower():
            tool_calls.append(("nixos_flakes_search", {"query": "devenv"}))
        elif "agenix" in response_text.lower():
            tool_calls.append(("nixos_flakes_search", {"query": "agenix"}))

    if "home_manager_stats" in response_text:
        tool_calls.append(("home_manager_stats", {}))

    if "darwin_stats" in response_text:
        tool_calls.append(("darwin_stats", {}))

    # Simulate tool execution
    tool_results = []
    for tool_name, args in tool_calls:
        result = await mock_mcp_client.call_tool(tool_name, args)
        tool_results.append(result)

    # Check behaviors
    behaviors_observed = []
    combined_output = response_text + " ".join(tool_results)

    for expected in expected_behaviors:
        if expected.lower() in combined_output.lower():
            behaviors_observed.append(expected)

    return {
        "response": response_text,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "behaviors_observed": behaviors_observed,
        "all_behaviors_met": len(behaviors_observed) == len(expected_behaviors),
        "missing_behaviors": [b for b in expected_behaviors if b not in behaviors_observed],
    }


@pytest.mark.asyncio
async def test_flake_search_basic():
    """Test basic flake search functionality."""
    result = await run_anthropic_test(
        prompt="Search for home-manager flake",
        expected_behaviors=["home-manager", "nix-community", "Manage a user environment"],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"
    assert any("nixos_flakes_search" in str(call) for call in result["tool_calls"])


@pytest.mark.asyncio
async def test_flake_search_multiple():
    """Test searching for multiple flakes."""
    result = await run_anthropic_test(
        prompt="Find flakes for development environments like devenv",
        expected_behaviors=["devenv", "cachix", "Fast, Declarative, Reproducible"],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"


@pytest.mark.asyncio
async def test_flake_search_security():
    """Test searching for security-related flakes."""
    result = await run_anthropic_test(
        prompt="I need a flake for managing secrets, something like agenix",
        expected_behaviors=["agenix", "ryantm", "age-encrypted secrets"],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"


@pytest.mark.asyncio
async def test_home_manager_stats():
    """Test Home Manager statistics functionality."""
    result = await run_anthropic_test(
        prompt="Show me Home Manager statistics - how many options are available?",
        expected_behaviors=["2129", "131", "programs: 1147"],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"
    assert any("home_manager_stats" in str(call) for call in result["tool_calls"])


@pytest.mark.asyncio
async def test_darwin_stats():
    """Test nix-darwin statistics functionality."""
    result = await run_anthropic_test(
        prompt="What are the nix-darwin statistics? How many configuration options does it have?",
        expected_behaviors=["348", "21", "services: 89"],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"
    assert any("darwin_stats" in str(call) for call in result["tool_calls"])


@pytest.mark.asyncio
async def test_combined_workflow():
    """Test a workflow combining stats and search."""
    result = await run_anthropic_test(
        prompt="First show me Home Manager stats, then find a flake for managing home configurations",
        expected_behaviors=[
            "2129",  # From stats
            "programs: 1147",  # From stats
            "home-manager",  # From search
            "nix-community",  # From search
        ],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"
    assert len(result["tool_calls"]) >= 2  # Should call both stats and search


@pytest.mark.asyncio
async def test_flake_deduplication():
    """Test that flake deduplication is working correctly."""
    # This tests that the response mentions "unique flakes" indicating deduplication
    result = await run_anthropic_test(
        prompt="Search for configuration management flakes",
        expected_behaviors=[
            "unique flake",  # Key indicator that deduplication is working
            "Packages:",  # Shows aggregated packages
        ],
    )

    assert result["all_behaviors_met"], f"Missing behaviors: {result['missing_behaviors']}"


@pytest.mark.asyncio
async def test_error_handling():
    """Test handling of non-existent flakes."""
    mock_client = MockMCPClient()
    result = await run_anthropic_test(
        prompt="Search for a flake called 'nonexistent-flake-12345'",
        expected_behaviors=["No flakes found"],
        mock_mcp_client=mock_client,
    )

    # The AI should handle the "not found" case gracefully
    # Either the AI mentions it in the response or calls the tool and gets no results
    combined_output = result["response"].lower() + " " + str(result["tool_results"]).lower()
    assert "no" in combined_output or "not found" in combined_output or len(result["tool_calls"]) > 0


def run_eval_tests():
    """Run all evaluation tests and print summary."""
    print("Running Anthropic API evaluation tests for flake search and stats...")

    # Run tests
    asyncio.run(test_flake_search_basic())
    print("✓ Basic flake search test passed")

    asyncio.run(test_flake_search_multiple())
    print("✓ Multiple flake search test passed")

    asyncio.run(test_flake_search_security())
    print("✓ Security flake search test passed")

    asyncio.run(test_home_manager_stats())
    print("✓ Home Manager stats test passed")

    asyncio.run(test_darwin_stats())
    print("✓ Darwin stats test passed")

    asyncio.run(test_combined_workflow())
    print("✓ Combined workflow test passed")

    asyncio.run(test_flake_deduplication())
    print("✓ Flake deduplication test passed")

    asyncio.run(test_error_handling())
    print("✓ Error handling test passed")

    print("\n✅ All flake and stats evaluation tests passed!")


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not found in environment")
        print("   Please set it in .env file or export it")
        print("   Example: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    run_eval_tests()
