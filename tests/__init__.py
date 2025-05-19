"""Test utilities and base classes for MCP-NixOS tests."""

import unittest
import sys
import os
from unittest.mock import patch

# Configure import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mcp_nixos.contexts.nixos_context import NixOSContext
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient
from mcp_nixos.cache.simple_cache import SimpleCache


# Base test class with common setup for mocked tests
class MCPNixOSTestBase(unittest.TestCase):
    """Base test class for MCP-NixOS tests that use mocked Elasticsearch responses."""

    def setUp(self):
        """Set up the test environment with mocked Elasticsearch client."""
        # Create the context
        self.context = NixOSContext()

        # Patch the ElasticsearchClient methods to avoid real API calls
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)

        # Set up default mock responses
        self.mock_es_query.return_value = {"hits": {"hits": [], "total": {"value": 0}}}


# Base test class for real API tests
class MCPNixOSRealAPITestBase(unittest.TestCase):
    """Base test class for MCP-NixOS tests that use real Elasticsearch API calls."""

    def setUp(self):
        """Set up the test environment for real API tests."""
        # Create the context with real Elasticsearch client
        self.context = NixOSContext()

        # Ensure we're using the correct endpoints
        self.context.es_client.es_packages_url = "https://search.nixos.org/backend/latest-43-nixos-unstable/_search"
        self.context.es_client.es_options_url = (
            "https://search.nixos.org/backend/latest-43-nixos-unstable-options/_search"
        )

        # Use a smaller cache for testing
        self.context.es_client.cache = SimpleCache(max_size=10, ttl=60)

    def assertValidAPIResponse(self, result, check_found=True):
        """Assert that an API response has a valid structure.

        Args:
            result: The API response to check
            check_found: Whether to check the found flag
        """
        self.assertIsNotNone(result)

        # If there's an error, it should be a string
        if "error" in result:
            self.assertIsInstance(result["error"], str)
            return

        # For found responses, check the name field
        if "name" in result:
            self.assertIsInstance(result["name"], str)

        # Check the found flag if requested
        if check_found and "found" in result:
            self.assertIsInstance(result["found"], bool)
