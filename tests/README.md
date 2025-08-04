# MCP-NixOS Test Suite

This directory contains comprehensive tests for the MCP-NixOS server, organized by functionality and purpose.

## Test Organization

### Core Functionality Tests
- `test_server.py` - Main server module tests including helper functions, NixOS tools, Home Manager tools, and Darwin tools
- `test_channels.py` - Channel discovery and management functionality
- `test_options.py` - Configuration option search and display
- `test_flakes.py` - Flake search and ecosystem functionality
- `test_github_flakes.py` - GitHub flake search integration
- `test_nixhub.py` - NixHub version history integration
- `test_discussions.py` - Discourse and GitHub issue search

### Output and Formatting Tests
- `test_plain_text_output.py` - Ensures all outputs are plain text (no XML/JSON leakage)
- `test_error_handling_edge_cases.py` - Edge case handling and error conditions

### Integration and Real-World Tests
- `test_integration.py` - Integration tests with real APIs (marked with @pytest.mark.integration)
- `test_real_world_scenarios.py` - Common user workflows and scenarios
- `test_mcp_behavior.py` - MCP tool usage patterns and behavior evaluation
- `test_context_awareness.py` - Context tracking and smart suggestions

### Specialized Tests
- `test_search_relevance_fixes.py` - Fixes based on agent feedback (darwin_search dock prioritization, hm_show enhancements)
- `test_server_features.py` - Additional tests to improve code coverage to 90%+
- `test_regression.py` - Regression tests for previously fixed bugs
- `test_nixos_stats.py` - Statistics functionality tests
- `test_ai_usability_evaluations.py` - AI usability evaluation tests
- `test_mcp_tools.py` - MCP-specific tool tests

### Support Files
- `conftest.py` - Pytest configuration and fixtures
- `test_main.py` - Main entry point tests

## Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest -k "not integration"

# Run with coverage
pytest --cov=mcp_nixos --cov-report=html

# Run specific test file
pytest tests/test_server.py

# Run with verbose output
pytest -v
```

## Test Markers

- `@pytest.mark.unit` - Unit tests that mock external dependencies
- `@pytest.mark.integration` - Integration tests that make real API calls
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.evals` - Evaluation tests for AI usability

## Coverage

The test suite aims for 90%+ code coverage. Current coverage can be checked with:

```bash
pytest --cov=mcp_nixos --cov-report=term
```