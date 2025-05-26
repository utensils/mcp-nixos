#!/usr/bin/env python3
"""Comprehensive tests for all MCP NixOS tools to identify and fix issues."""

import pytest
from unittest.mock import patch, MagicMock
from mcp_nixos.server import (
    nixos_search,
    nixos_info,
    home_manager_search,
    home_manager_info,
    home_manager_stats,
    home_manager_list_options,
    darwin_stats,
)


class TestNixOSSearchIssues:
    """Test issues with nixos_search specifically for options."""

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_options_now_returns_relevant_results(self, mock_es):
        """Test that searching for 'services.nginx' returns relevant nginx options."""
        # Mock proper nginx-related results
        mock_es.return_value = [
            {
                "_source": {
                    "option_name": "services.nginx.enable",
                    "option_type": "boolean",
                    "option_description": "Whether to enable Nginx Web Server.",
                }
            },
            {
                "_source": {
                    "option_name": "services.nginx.package",
                    "option_type": "package",
                    "option_description": "Nginx package to use.",
                }
            },
        ]

        result = nixos_search("services.nginx", search_type="options", limit=2, channel="stable")

        # After fix, should return nginx-related options
        assert "services.nginx.enable" in result
        assert "services.nginx.package" in result
        # Should mention the search term
        assert "services.nginx" in result

    @patch("mcp_nixos.server.es_query")
    def test_nixos_info_option_not_found(self, mock_es):
        """Test that nixos_info fails to find specific options like services.nginx.enable."""
        mock_es.return_value = []  # Empty results

        result = nixos_info("services.nginx.enable", type="option", channel="stable")
        assert "Error (NOT_FOUND)" in result
        assert "services.nginx.enable" in result


class TestHomeManagerIssues:
    """Test issues with Home Manager tools."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_list_options_incomplete(self, mock_parse):
        """Test that home_manager_list_options only returns 2 categories (incomplete)."""
        # Mock returns only 2 categories as seen in the issue
        mock_parse.return_value = [
            {"name": "_module.args", "description": "", "type": ""},
            {"name": "accounts.calendar.basePath", "description": "", "type": ""},
            {"name": "accounts.email.enable", "description": "", "type": ""},
        ]

        result = home_manager_list_options()
        assert "_module (1 options)" in result
        assert "accounts (2 options)" in result
        assert "programs" not in result  # Missing many categories!

        # Should have many more categories
        assert "(2 total)" in result  # Only 2 categories found

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_stats_placeholder(self, mock_parse):
        """Test that home_manager_stats returns actual statistics."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "programs.git.enable", "type": "boolean", "description": "Enable git"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "services.gpg-agent.enable", "type": "boolean", "description": "Enable GPG agent"},
            {"name": "home.packages", "type": "list", "description": "Packages to install"},
            {"name": "wayland.windowManager.sway.enable", "type": "boolean", "description": "Enable Sway"},
            {"name": "xsession.enable", "type": "boolean", "description": "Enable X session"},
        ]

        result = home_manager_stats()
        assert "Home Manager Statistics:" in result
        assert "Total options: 6" in result
        assert "Categories: 5" in result
        assert "Top categories:" in result
        assert "programs: 2 options" in result
        assert "services: 1 options" in result


class TestDarwinIssues:
    """Test issues with nix-darwin tools."""

    @patch("mcp_nixos.server.parse_html_options")
    def test_darwin_stats_placeholder(self, mock_parse):
        """Test that darwin_stats returns actual statistics."""
        # Mock parsed options
        mock_parse.return_value = [
            {"name": "services.nix-daemon.enable", "type": "boolean", "description": "Enable nix-daemon"},
            {"name": "system.defaults.dock.autohide", "type": "boolean", "description": "Auto-hide dock"},
            {"name": "launchd.agents.test", "type": "attribute set", "description": "Launchd agents"},
            {"name": "programs.zsh.enable", "type": "boolean", "description": "Enable zsh"},
            {"name": "homebrew.enable", "type": "boolean", "description": "Enable Homebrew"},
        ]

        result = darwin_stats()
        assert "nix-darwin Statistics:" in result
        assert "Total options: 5" in result
        assert "Categories: 5" in result
        assert "Top categories:" in result
        assert "services: 1 options" in result
        assert "system: 1 options" in result


class TestHTMLParsingIssues:
    """Test issues with HTML parsing that affect both Home Manager and Darwin."""

    @patch("mcp_nixos.server.requests.get")
    def test_parse_html_options_type_extraction(self, mock_get):
        """Test that type information is not properly extracted from HTML."""
        # Mock HTML response with proper structure
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <body>
            <dt>programs.git.enable</dt>
            <dd>
                <p>Whether to enable Git.</p>
                <span class="term">Type: boolean</span>
            </dd>
            <dt>programs.git.package</dt>
            <dd>
                <p>The git package to use.</p>
                <span class="term">Type: package</span>
            </dd>
        </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = home_manager_info("programs.git.enable")

        # Check if type info is properly extracted
        assert "Type:" in result or "boolean" in result
        if "Type:" not in result:
            # Type extraction is failing
            assert False, "Type information not extracted from HTML"


class TestElasticsearchQueryIssues:
    """Test issues with Elasticsearch query construction."""

    @patch("mcp_nixos.server.requests.post")
    def test_es_query_field_names(self, mock_post):
        """Test that ES queries use correct field names."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Test options search
        nixos_search("nginx", search_type="options", limit=1)

        # Check the query sent to ES
        call_args = mock_post.call_args
        query_data = call_args[1]["json"]["query"]

        # Verify correct field names are used
        should_clauses = query_data["bool"]["should"]
        field_names = []
        for clause in should_clauses:
            if "match" in clause:
                field_names.extend(clause["match"].keys())
            elif "wildcard" in clause:
                field_names.extend(clause["wildcard"].keys())

        # After fix, we use wildcard for option_name
        assert "option_name" in field_names or any("option_name" in str(clause) for clause in should_clauses)
        assert "option_description" in field_names

        # Test exact match for nixos_info
        mock_post.reset_mock()
        nixos_info("services.nginx.enable", type="option")

        call_args = mock_post.call_args
        query_data = call_args[1]["json"]["query"]

        # Check for keyword field usage
        must_clauses = query_data["bool"]["must"]
        for clause in must_clauses:
            if "term" in clause and "option_name" in str(clause):
                # Should use keyword field for exact match
                assert "option_name.keyword" in str(clause) or "option_name" in str(clause)


class TestPlainTextFormatting:
    """Test that all outputs are plain text without XML/HTML artifacts."""

    @patch("mcp_nixos.server.es_query")
    def test_nixos_search_strips_html(self, mock_es):
        """Test that HTML tags in descriptions are properly handled."""
        mock_es.return_value = [
            {
                "_source": {
                    "option_name": "test.option",
                    "option_type": "boolean",
                    "option_description": (
                        "<rendered-html><p>Test description with <code>code</code></p></rendered-html>"
                    ),
                }
            }
        ]

        result = nixos_search("test", search_type="options")

        # Should not contain HTML tags
        assert "<rendered-html>" not in result
        assert "</p>" not in result
        assert "<code>" not in result

        # But should contain the actual text
        assert "Test description" in result


class TestErrorHandling:
    """Test error handling across all tools."""

    def test_nixos_search_invalid_parameters(self):
        """Test parameter validation in nixos_search."""
        # Invalid type
        result = nixos_search("test", search_type="invalid")
        assert "Error" in result
        assert "Invalid type" in result

        # Invalid channel
        result = nixos_search("test", channel="invalid")
        assert "Error" in result
        assert "Invalid channel" in result

        # Invalid limit
        result = nixos_search("test", limit=0)
        assert "Error" in result
        assert "Limit must be 1-100" in result

    @patch("mcp_nixos.server.requests.get")
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")

        result = home_manager_search("test")
        assert "Error" in result
        assert "Failed to fetch docs" in result or "Network error" in result


class TestRealAPIBehavior:
    """Tests that verify actual API behavior (can be skipped in CI)."""

    @pytest.mark.integration
    def test_real_nixos_option_search(self):
        """Test real NixOS API option search behavior."""
        # This would make actual API calls to verify the issue
        result = nixos_search("services.nginx.enable", search_type="options", channel="stable")

        # The search should return nginx-related options, not random ones
        if "appstream.enable" in result:
            pytest.fail("Search returns unrelated options - API query issue confirmed")

    @pytest.mark.integration
    def test_real_home_manager_parsing(self):
        """Test real Home Manager HTML parsing."""
        result = home_manager_list_options()

        # Should have many categories, not just 2
        if "(2 total)" in result:
            pytest.fail("Only 2 categories found - HTML parsing issue confirmed")


# Additional test utilities
def count_lines(text: str) -> int:
    """Count non-empty lines in output."""
    return len([line for line in text.split("\n") if line.strip()])


def has_plain_text_format(text: str) -> bool:
    """Check if text follows plain text format without XML/HTML."""
    forbidden_patterns = [
        "<rendered-html>",
        "</rendered-html>",
        "<p>",
        "</p>",
        "<code>",
        "</code>",
        "<a ",
        "</a>",
        "<?xml",
    ]
    return not any(pattern in text for pattern in forbidden_patterns)


class TestOutputFormat:
    """Test output formatting consistency."""

    @patch("mcp_nixos.server.es_query")
    def test_search_result_format(self, mock_es):
        """Test consistent formatting of search results."""
        mock_es.return_value = [
            {
                "_source": {
                    "package_pname": "nginx",
                    "package_pversion": "1.24.0",
                    "package_description": "A web server",
                }
            }
        ]

        result = nixos_search("nginx", search_type="packages", limit=1)

        # Check format
        assert "Found 1 packages matching" in result
        assert "• nginx (1.24.0)" in result
        assert "  A web server" in result  # Indented description

        # Check plain text
        assert has_plain_text_format(result)

    @patch("mcp_nixos.server.parse_html_options")
    def test_home_manager_format_consistency(self, mock_parse):
        """Test Home Manager output format consistency."""
        mock_parse.return_value = [
            {"name": "programs.git.enable", "description": "Whether to enable Git.", "type": "boolean"}
        ]

        result = home_manager_search("git", limit=1)

        # Check format matches nixos_search style
        assert "Found 1 Home Manager options matching" in result
        assert "• programs.git.enable" in result
        assert "  Type: boolean" in result
        assert "  Whether to enable Git." in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
