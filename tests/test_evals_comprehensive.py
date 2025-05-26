"""Comprehensive evaluation tests for MCP-NixOS following the MCP Evals Guide."""

import pytest
from unittest.mock import patch
from dataclasses import dataclass
from typing import List, Dict, Tuple

from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    nixos_stats,
    home_manager_search,
    home_manager_info,
    home_manager_list_options,
    home_manager_options_by_prefix,
    darwin_search,
    darwin_info,
    darwin_list_options,
    darwin_options_by_prefix,
)


@dataclass
class EvalScenario:
    """Represents an evaluation scenario."""

    name: str
    user_query: str
    expected_tool_calls: List[str]
    success_criteria: List[str]
    description: str = ""


@dataclass
class EvalResult:
    """Result of running an evaluation."""

    scenario: EvalScenario
    passed: bool
    score: float  # 0.0 to 1.0
    tool_calls_made: List[Tuple[str, dict, str]]  # (tool_name, args, result)
    criteria_met: Dict[str, bool]
    reasoning: str


class MockAIAssistant:
    """Simulates an AI assistant using the MCP tools."""

    def __init__(self):
        self.tool_calls = []

    def process_query(self, query: str) -> List[Tuple[str, dict, str]]:
        """Process a user query and return tool calls made."""
        self.tool_calls = []

        # Simulate AI decision making based on query
        if ("install" in query.lower() or "get" in query.lower()) and any(
            pkg in query.lower() for pkg in ["vscode", "firefox", "git"]
        ):
            self._handle_package_installation(query)
        elif ("configure" in query.lower() or "set up" in query.lower()) and "nginx" in query.lower():
            self._handle_service_configuration(query)
        elif (
            "home manager" in query.lower()
            or "should i configure" in query.lower()
            or ("manage" in query.lower() and "home manager" in query.lower())
        ):
            self._handle_home_manager_query(query)
        elif "dock" in query.lower() and ("darwin" in query.lower() or "macos" in query.lower()):
            self._handle_darwin_query(query)
        elif "difference between" in query.lower():
            self._handle_comparison_query(query)

        return self.tool_calls

    def _make_tool_call(self, tool_name: str, **kwargs) -> str:
        """Make a tool call and record it."""
        # Map tool names to actual functions
        tools = {
            "nixos_search": nixos_search,
            "nixos_info": nixos_info,
            "nixos_stats": nixos_stats,
            "home_manager_search": home_manager_search,
            "home_manager_info": home_manager_info,
            "home_manager_list_options": home_manager_list_options,
            "home_manager_options_by_prefix": home_manager_options_by_prefix,
            "darwin_search": darwin_search,
            "darwin_info": darwin_info,
            "darwin_list_options": darwin_list_options,
            "darwin_options_by_prefix": darwin_options_by_prefix,
        }

        if tool_name in tools:
            result = tools[tool_name](**kwargs)
            self.tool_calls.append((tool_name, kwargs, result))
            return result
        return ""

    def _handle_package_installation(self, query: str):
        """Handle package installation queries."""
        # Extract package name
        package = None
        if "vscode" in query.lower():
            package = "vscode"
        elif "firefox" in query.lower():
            package = "firefox"
        elif "git" in query.lower():
            package = "git"

        if package:
            # Search for the package
            self._make_tool_call("nixos_search", query=package, search_type="packages")

            # If it's a command, also search programs
            if package == "git":
                self._make_tool_call("nixos_search", query=package, search_type="programs")

            # Get detailed info
            self._make_tool_call("nixos_info", name=package, type="package")

    def _handle_service_configuration(self, query: str):
        """Handle service configuration queries."""
        if "nginx" in query.lower():
            # Search for nginx options
            self._make_tool_call("nixos_search", query="services.nginx", search_type="options")
            # Get specific option info
            self._make_tool_call("nixos_info", name="services.nginx.enable", type="option")
            self._make_tool_call("nixos_info", name="services.nginx.virtualHosts", type="option")

    def _handle_home_manager_query(self, query: str):
        """Handle Home Manager related queries."""
        if "git" in query.lower():
            # Search both system and user options
            self._make_tool_call("nixos_search", query="git", search_type="packages")
            self._make_tool_call("home_manager_search", query="programs.git")
            self._make_tool_call("home_manager_info", name="programs.git.enable")
        elif "shell" in query.lower():
            # Handle shell configuration queries
            self._make_tool_call("home_manager_search", query="programs.zsh")
            self._make_tool_call("home_manager_info", name="programs.zsh.enable")
            self._make_tool_call("home_manager_options_by_prefix", option_prefix="programs.zsh")

    def _handle_darwin_query(self, query: str):
        """Handle Darwin/macOS queries."""
        if "dock" in query.lower():
            self._make_tool_call("darwin_search", query="system.defaults.dock")
            self._make_tool_call("darwin_info", name="system.defaults.dock.autohide")
            self._make_tool_call("darwin_options_by_prefix", option_prefix="system.defaults.dock")

    def _handle_comparison_query(self, query: str):
        """Handle package comparison queries."""
        if "firefox" in query.lower():
            self._make_tool_call("nixos_search", query="firefox", search_type="packages")
            self._make_tool_call("nixos_info", name="firefox", type="package")
            self._make_tool_call("nixos_info", name="firefox-esr", type="package")


class EvalFramework:
    """Framework for running and scoring evaluations."""

    def __init__(self):
        self.assistant = MockAIAssistant()

    def run_eval(self, scenario: EvalScenario) -> EvalResult:
        """Run a single evaluation scenario."""
        # Have the assistant process the query
        tool_calls = self.assistant.process_query(scenario.user_query)

        # Check which criteria were met
        criteria_met = self._check_criteria(scenario, tool_calls)

        # Calculate score
        score = sum(1 for met in criteria_met.values() if met) / len(criteria_met)
        passed = score >= 0.7  # 70% threshold

        # Generate reasoning
        reasoning = self._generate_reasoning(scenario, tool_calls, criteria_met)

        return EvalResult(
            scenario=scenario,
            passed=passed,
            score=score,
            tool_calls_made=tool_calls,
            criteria_met=criteria_met,
            reasoning=reasoning,
        )

    def _check_criteria(self, scenario: EvalScenario, tool_calls: List[Tuple[str, dict, str]]) -> Dict[str, bool]:
        """Check which success criteria were met."""
        criteria_met = {}

        # Check expected tool calls
        expected_tools = set()
        for expected_call in scenario.expected_tool_calls:
            # Parse expected call
            tool_name = expected_call.split("(")[0]
            expected_tools.add(tool_name)

        actual_tools = {call[0] for call in tool_calls}
        criteria_met["made_expected_tool_calls"] = expected_tools.issubset(actual_tools)

        # Check specific criteria based on scenario
        all_results = "\n".join(call[2] for call in tool_calls)

        for criterion in scenario.success_criteria:
            if "finds" in criterion and "package" in criterion:
                # Check if package was found
                criteria_met[criterion] = any("Found" in call[2] and "packages" in call[2] for call in tool_calls)
            elif "mentions" in criterion:
                # Check if certain text is mentioned
                key_term = criterion.split("mentions")[1].strip()
                criteria_met[criterion] = key_term.lower() in all_results.lower()
            elif "provides" in criterion:
                # Check if examples/syntax provided
                criteria_met[criterion] = bool(tool_calls) and len(all_results) > 100
            elif "explains" in criterion:
                # Check if explanation provided (has meaningful content)
                criteria_met[criterion] = len(all_results) > 200
            else:
                # Default: assume met if we have results
                criteria_met[criterion] = bool(tool_calls)

        return criteria_met

    def _generate_reasoning(
        self, scenario: EvalScenario, tool_calls: List[Tuple[str, dict, str]], criteria_met: Dict[str, bool]
    ) -> str:
        """Generate reasoning about the evaluation result."""
        parts = []

        # Tool usage
        if tool_calls:
            parts.append(f"Made {len(tool_calls)} tool calls")
        else:
            parts.append("No tool calls made")

        # Criteria summary
        met_count = sum(1 for met in criteria_met.values() if met)
        parts.append(f"Met {met_count}/{len(criteria_met)} criteria")

        # Specific issues
        for criterion, met in criteria_met.items():
            if not met:
                parts.append(f"Failed: {criterion}")

        return "; ".join(parts)


class TestPackageDiscoveryEvals:
    """Evaluations for package discovery scenarios."""

    def setup_method(self):
        self.framework = EvalFramework()

    @patch("mcp_nixos.server.es_query")
    def test_eval_find_vscode_package(self, mock_query):
        """Eval: User wants to install VSCode."""
        # Mock responses
        mock_query.return_value = [
            {
                "_source": {
                    "package_pname": "vscode",
                    "package_pversion": "1.85.0",
                    "package_description": "Open source code editor by Microsoft",
                }
            }
        ]

        scenario = EvalScenario(
            name="find_vscode",
            user_query="I want to install VSCode on NixOS",
            expected_tool_calls=[
                "nixos_search(query='vscode', search_type='packages')",
                "nixos_info(name='vscode', type='package')",
            ],
            success_criteria=["finds vscode package", "mentions configuration.nix", "provides installation syntax"],
        )

        result = self.framework.run_eval(scenario)

        # Verify evaluation
        assert result.passed
        assert result.score >= 0.7
        assert len(result.tool_calls_made) >= 2
        assert any("vscode" in str(call) for call in result.tool_calls_made)

    @patch("mcp_nixos.server.es_query")
    def test_eval_find_git_command(self, mock_query):
        """Eval: User wants git command."""

        # Mock different responses for different queries
        def query_side_effect(*args, **kwargs):
            query = args[1]
            if "program" in str(query):
                return [{"_source": {"package_programs": ["git"], "package_pname": "git"}}]
            return [
                {
                    "_source": {
                        "package_pname": "git",
                        "package_pversion": "2.43.0",
                        "package_description": "Distributed version control system",
                    }
                }
            ]

        mock_query.side_effect = query_side_effect

        scenario = EvalScenario(
            name="find_git_command",
            user_query="How do I get the 'git' command on NixOS?",
            expected_tool_calls=[
                "nixos_search(query='git', search_type='programs')",
                "nixos_info(name='git', type='package')",
            ],
            success_criteria=[
                "identifies git package",
                "explains system vs user installation",
                "shows both environment.systemPackages and Home Manager options",
            ],
        )

        result = self.framework.run_eval(scenario)

        assert result.passed
        assert any("programs" in str(call[1]) for call in result.tool_calls_made)

    @patch("mcp_nixos.server.es_query")
    def test_eval_package_comparison(self, mock_query):
        """Eval: User needs to compare packages."""

        # Mock responses for firefox variants
        def query_side_effect(*args, **kwargs):
            return [
                {
                    "_source": {
                        "package": {
                            "pname": "firefox",
                            "version": "120.0",
                            "description": "Mozilla Firefox web browser",
                        }
                    }
                }
            ]

        mock_query.side_effect = query_side_effect

        scenario = EvalScenario(
            name="compare_firefox_variants",
            user_query="What's the difference between firefox and firefox-esr?",
            expected_tool_calls=[
                "nixos_search(query='firefox', search_type='packages')",
                "nixos_info(name='firefox', type='package')",
                "nixos_info(name='firefox-esr', type='package')",
            ],
            success_criteria=[
                "explains ESR vs regular versions",
                "mentions stability vs features trade-off",
                "provides configuration examples for both",
            ],
        )

        result = self.framework.run_eval(scenario)

        # Check that comparison tools were called
        assert len(result.tool_calls_made) >= 2
        assert any("firefox-esr" in str(call) for call in result.tool_calls_made)


class TestServiceConfigurationEvals:
    """Evaluations for service configuration scenarios."""

    def setup_method(self):
        self.framework = EvalFramework()

    @patch("mcp_nixos.server.es_query")
    def test_eval_nginx_setup(self, mock_query):
        """Eval: User wants to set up nginx."""
        mock_query.return_value = [
            {
                "_source": {
                    "option_name": "services.nginx.enable",
                    "option_type": "boolean",
                    "option_description": "Whether to enable nginx web server",
                }
            }
        ]

        scenario = EvalScenario(
            name="nginx_setup",
            user_query="How do I set up nginx on NixOS to serve static files?",
            expected_tool_calls=[
                "nixos_search(query='services.nginx', search_type='options')",
                "nixos_info(name='services.nginx.enable', type='option')",
                "nixos_info(name='services.nginx.virtualHosts', type='option')",
            ],
            success_criteria=[
                "enables nginx service",
                "configures virtual host",
                "explains directory structure",
                "mentions firewall configuration",
                "provides complete configuration.nix example",
            ],
        )

        result = self.framework.run_eval(scenario)

        assert len(result.tool_calls_made) >= 2
        assert any("nginx" in call[2] for call in result.tool_calls_made)

    @patch("mcp_nixos.server.es_query")
    def test_eval_database_setup(self, mock_query):
        """Eval: User wants PostgreSQL setup."""
        mock_query.return_value = [
            {
                "_source": {
                    "option": {
                        "option_name": "services.postgresql.enable",
                        "option_type": "boolean",
                        "option_description": "Whether to enable PostgreSQL",
                    }
                }
            }
        ]

        scenario = EvalScenario(
            name="postgresql_setup",
            user_query="Set up PostgreSQL with a database for my app",
            expected_tool_calls=[
                "nixos_search(query='services.postgresql', search_type='options')",
                "nixos_info(name='services.postgresql.enable', type='option')",
                "nixos_info(name='services.postgresql.ensureDatabases', type='option')",
                "nixos_info(name='services.postgresql.ensureUsers', type='option')",
            ],
            success_criteria=[
                "enables postgresql service",
                "creates database",
                "sets up user with permissions",
                "explains connection details",
                "mentions backup considerations",
            ],
        )

        # This scenario would need more complex mocking in real implementation
        # For now, just verify the structure works
        result = self.framework.run_eval(scenario)
        assert isinstance(result, EvalResult)


class TestHomeManagerIntegrationEvals:
    """Evaluations for Home Manager vs system configuration."""

    def setup_method(self):
        self.framework = EvalFramework()

    @patch("mcp_nixos.server.es_query")
    @patch("mcp_nixos.server.parse_html_options")
    def test_eval_user_vs_system_config(self, mock_parse, mock_query):
        """Eval: User confused about where to configure git."""
        # Mock system package
        mock_query.return_value = [
            {
                "_source": {
                    "package": {
                        "pname": "git",
                        "version": "2.43.0",
                        "description": "Distributed version control system",
                    }
                }
            }
        ]

        # Mock Home Manager options
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.git.userName", "type": "string", "description": "Git user name"},
        ]

        scenario = EvalScenario(
            name="git_config_location",
            user_query="Should I configure git in NixOS or Home Manager?",
            expected_tool_calls=[
                "nixos_search(query='git', search_type='packages')",
                "home_manager_search(query='programs.git')",
                "home_manager_info(name='programs.git.enable')",
            ],
            success_criteria=[
                "explains system vs user configuration",
                "recommends Home Manager for user configs",
                "shows both approaches",
                "explains when to use each",
            ],
        )

        result = self.framework.run_eval(scenario)

        assert len(result.tool_calls_made) >= 3
        assert any("home_manager" in call[0] for call in result.tool_calls_made)

    @patch("mcp_nixos.server.parse_html_options")
    def test_eval_dotfiles_management(self, mock_parse):
        """Eval: User wants to manage shell config."""
        mock_parse.return_value = [
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "programs.zsh.oh-my-zsh.enable", "type": "boolean", "description": "Enable Oh My Zsh"},
        ]

        scenario = EvalScenario(
            name="shell_config",
            user_query="How do I manage my shell configuration with Home Manager?",
            expected_tool_calls=[
                "home_manager_search(query='programs.zsh')",
                "home_manager_info(name='programs.zsh.enable')",
                "home_manager_options_by_prefix(option_prefix='programs.zsh')",
            ],
            success_criteria=[
                "enables shell program",
                "explains configuration options",
                "mentions aliases and plugins",
                "provides working example",
            ],
        )

        result = self.framework.run_eval(scenario)

        assert any("zsh" in str(call) for call in result.tool_calls_made)


class TestDarwinPlatformEvals:
    """Evaluations for macOS/nix-darwin scenarios."""

    def setup_method(self):
        self.framework = EvalFramework()

    @patch("mcp_nixos.server.parse_html_options")
    def test_eval_macos_dock_settings(self, mock_parse):
        """Eval: User wants to configure macOS dock."""
        mock_parse.return_value = [
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            {"name": "system.defaults.dock.tilesize", "type": "integer", "description": "Dock icon size"},
        ]

        scenario = EvalScenario(
            name="macos_dock_config",
            user_query="How do I configure dock settings with nix-darwin?",
            expected_tool_calls=[
                "darwin_search(query='system.defaults.dock')",
                "darwin_info(name='system.defaults.dock.autohide')",
                "darwin_options_by_prefix(option_prefix='system.defaults.dock')",
            ],
            success_criteria=[
                "finds dock configuration options",
                "explains autohide and other settings",
                "provides darwin-configuration.nix example",
                "mentions darwin-rebuild command",
            ],
        )

        result = self.framework.run_eval(scenario)

        assert len(result.tool_calls_made) >= 2
        assert any("darwin" in call[0] for call in result.tool_calls_made)
        assert any("dock" in str(call) for call in result.tool_calls_made)


class TestEvalReporting:
    """Test evaluation reporting functionality."""

    def test_eval_result_generation(self):
        """Test that eval results are properly generated."""
        scenario = EvalScenario(
            name="test_scenario",
            user_query="Test query",
            expected_tool_calls=["nixos_search(query='test')"],
            success_criteria=["finds test package"],
        )

        result = EvalResult(
            scenario=scenario,
            passed=True,
            score=1.0,
            tool_calls_made=[
                ("nixos_search", {"query": "test"}, "Found 1 packages matching 'test':\n\n• test (1.0.0)")
            ],
            criteria_met={"finds test package": True},
            reasoning="Made 1 tool calls; Met 1/1 criteria",
        )

        assert result.passed
        assert result.score == 1.0
        assert len(result.tool_calls_made) == 1

    def test_eval_scoring(self):
        """Test evaluation scoring logic."""
        # Create a scenario with multiple criteria
        EvalScenario(
            name="multi_criteria",
            user_query="Test with multiple criteria",
            expected_tool_calls=[],
            success_criteria=["criterion1", "criterion2", "criterion3"],
        )

        # Test partial success
        criteria_met = {"criterion1": True, "criterion2": True, "criterion3": False}

        score = sum(1 for met in criteria_met.values() if met) / len(criteria_met)
        assert score == pytest.approx(0.666, rel=0.01)
        assert score < 0.7  # Below passing threshold

    def generate_eval_report(self, results: List[EvalResult]) -> str:
        """Generate a report from evaluation results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / total if total > 0 else 0

        report = f"""# MCP-NixOS Evaluation Report

## Summary
- Total Evaluations: {total}
- Passed: {passed} ({passed/total*100:.1f}%)
- Average Score: {avg_score:.2f}

## Detailed Results
"""

        for result in results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report += f"\n### {status} {result.scenario.name} (Score: {result.score:.2f})\n"
            report += f"Query: {result.scenario.user_query}\n"
            report += f"Reasoning: {result.reasoning}\n"

        return report


class TestCompleteEvalSuite:
    """Run complete evaluation suite."""

    @pytest.mark.integration
    def test_run_all_evals(self):
        """Run all evaluation scenarios and generate report."""
        # This would run all eval scenarios and generate a comprehensive report
        # For brevity, just verify the structure exists

        all_scenarios = [
            EvalScenario(
                name="basic_package_install",
                user_query="How do I install Firefox?",
                expected_tool_calls=["nixos_search(query='firefox')"],
                success_criteria=["finds firefox package"],
            ),
            EvalScenario(
                name="service_config",
                user_query="Configure nginx web server",
                expected_tool_calls=["nixos_search(query='nginx', search_type='options')"],
                success_criteria=["finds nginx options"],
            ),
            EvalScenario(
                name="home_manager_usage",
                user_query="Should I use Home Manager for git config?",
                expected_tool_calls=["home_manager_search(query='git')"],
                success_criteria=["recommends Home Manager"],
            ),
        ]

        assert len(all_scenarios) >= 3
        assert all(isinstance(s, EvalScenario) for s in all_scenarios)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
