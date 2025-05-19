"""
Tests for version detection in the MCP-NixOS package.

This module tests the version detection mechanisms in the mcp_nixos/__init__.py file.
"""

import sys
from unittest.mock import patch, MagicMock


def test_version_exists():
    """Test that the __version__ attribute exists and is a valid string."""
    import mcp_nixos

    assert hasattr(mcp_nixos, "__version__")
    assert isinstance(mcp_nixos.__version__, str)
    assert mcp_nixos.__version__ != ""


@patch("importlib.metadata.version")
def test_version_from_metadata(mock_version):
    """Test version detection using importlib.metadata.version."""
    # Mock the behavior of importlib.metadata.version
    mock_version.return_value = "1.2.3"

    # Force reload of the module
    if "mcp_nixos" in sys.modules:
        del sys.modules["mcp_nixos"]
    import mcp_nixos

    # Check that the correct version is set
    assert mcp_nixos.__version__ == "1.2.3"
    mock_version.assert_called_once_with("mcp-nixos")


@patch("importlib.metadata.version")
def test_version_fallback_package_not_found(mock_version):
    """Test version fallback when package is not found."""
    # Mock the behavior when package is not found
    from importlib.metadata import PackageNotFoundError

    mock_version.side_effect = PackageNotFoundError("mcp-nixos")

    # Force reload of the module
    if "mcp_nixos" in sys.modules:
        del sys.modules["mcp_nixos"]
    import mcp_nixos

    # Check that the default version is used
    assert mcp_nixos.__version__ == "0.5.0"
    mock_version.assert_called_once_with("mcp-nixos")


@patch("importlib.metadata.version", side_effect=ImportError)
@patch("pkg_resources.get_distribution")
def test_version_fallback_for_older_python(mock_get_distribution, _):
    """Test version detection using pkg_resources for older Python versions."""
    # Setup mock pkg_resources.get_distribution
    mock_dist = MagicMock()
    mock_dist.version = "3.4.5"
    mock_get_distribution.return_value = mock_dist

    # Force reload of the module
    if "mcp_nixos" in sys.modules:
        del sys.modules["mcp_nixos"]
    import mcp_nixos

    # Check that the version from pkg_resources is used
    assert mcp_nixos.__version__ == "3.4.5"
    mock_get_distribution.assert_called_once_with("mcp-nixos")


@patch("importlib.metadata.version", side_effect=ImportError)
@patch("pkg_resources.get_distribution", side_effect=Exception("Resource not found"))
def test_version_ultimate_fallback(mock_get_distribution, _):
    """Test the ultimate fallback to hardcoded version when all else fails."""
    # Force reload of the module
    if "mcp_nixos" in sys.modules:
        del sys.modules["mcp_nixos"]
    import mcp_nixos

    # Check that the default version is used when everything fails
    assert mcp_nixos.__version__ == "0.5.0"
    mock_get_distribution.assert_called_once()
