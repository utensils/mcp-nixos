"""Minimal test configuration for refactored MCP-NixOS."""

import pytest  # pylint: disable=unused-import


def pytest_addoption(parser):
    """Add test filtering options."""
    parser.addoption("--unit", action="store_true", help="Run unit tests only")
    parser.addoption("--integration", action="store_true", help="Run integration tests only")


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "asyncio: mark test as async")

    # Handle test filtering
    if config.getoption("--unit"):
        config.option.markexpr = "not integration"
    elif config.getoption("--integration"):
        config.option.markexpr = "integration"
