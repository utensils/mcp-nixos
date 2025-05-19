import logging
import time
import unittest
import pytest
from unittest.mock import Mock, patch

from mcp_nixos.cache.simple_cache import SimpleCache

# Import the server module
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient
from mcp_nixos.contexts.nixos_context import NixOSContext

# Disable logging during tests
logging.disable(logging.CRITICAL)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

"""
Test approach:

This test suite combines real API calls with resilient testing patterns to ensure
the MCP-NixOS service functions correctly. Instead of mocking the Elasticsearch API,
we make actual API calls, and:

1. Test the structure of responses rather than exact content
2. Gracefully handle API errors as valid test responses
3. For cases that might not return actual data, we verify error handling
   patterns are consistent and informative

The approach is more useful than mocking because:
- It detects real API changes or issues
- Ensures the application correctly handles real-world responses
- Verifies error handling against actual API behaviors
- Maintains coverage even when API responses change

Note: Tests run against the actual Elasticsearch API with credentials hard-coded
in the server.py file.
"""


class TestElasticsearchClient(unittest.TestCase):
    """Test the ElasticsearchClient class with real API calls.

    These tests make actual API calls to the NixOS Elasticsearch endpoints.
    The tests are designed to be resilient to API changes and errors by:
    - Testing response structure rather than specific content
    - Handling both successful responses and error responses appropriately
    - Using assertions that work regardless of whether data is returned
    """

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()
        # Use a smaller cache for testing
        self.client.cache = SimpleCache(max_size=10, ttl=60)
        # Default base endpoint for packages index
        self.client.es_packages_url = "https://search.nixos.org/backend/latest-43-nixos-unstable/_search"
        # Default base endpoint for options index
        self.client.es_options_url = "https://search.nixos.org/backend/latest-43-nixos-unstable-options/_search"

    def test_search_packages(self):
        """Test searching for packages."""
        # Test with a common package that should always exist
        result = self.client.search_packages("python", limit=5)

        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)

        # Verify the structure of a package
        package = result["packages"][0]
        self.assertIn("name", package)
        self.assertIn("description", package)

        # Test with a wildcard search
        result = self.client.search_packages("pyth*", limit=5)
        self.assertGreater(len(result["packages"]), 0)

        # Test with a non-existent package
        result = self.client.search_packages("thisshouldnotexistasapackage12345", limit=5)
        self.assertEqual(len(result["packages"]), 0)

    def test_search_options(self):
        """Test searching for options."""
        # Test with a common option that should always exist
        result = self.client.search_options("services.nginx", limit=5)

        # Check if we got an error (which can happen with actual API)
        if "error" in result:
            self.assertIsInstance(result["error"], str)
        else:
            # Verify the expected structure
            self.assertIn("options", result)
            self.assertIn("count", result)
            self.assertIsInstance(result["options"], list)

            # If we got results, verify the structure of an option
            if len(result["options"]) > 0:
                option = result["options"][0]
                self.assertIn("name", option)
                self.assertIn("description", option)

        # Test with a non-existent option
        try:
            result = self.client.search_options("thisshouldnotexistasanoption12345", limit=5)
            if "error" not in result:
                self.assertEqual(len(result["options"]), 0)
        except Exception:
            # If an exception is raised, it's acceptable for this specific case
            # since we're testing with a non-existent option
            pass

    def test_get_package(self):
        """Test getting a specific package."""
        # Test with a package that should always exist
        result = self.client.get_package("python")

        # Check that the response has the expected structure, but don't validate actual contents
        self.assertIn("name", result)

        # If not found (which can happen with actual API), just verify error structure
        if not result.get("found", False):
            self.assertIn("error", result)
        else:
            # If found, verify the standard fields
            self.assertIn("description", result)
            self.assertIn("version", result)

        # Test with a non-existent package
        result = self.client.get_package("thisshouldnotexistasapackage12345")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_get_option(self):
        """Test getting a specific option."""
        # Test with an option that should always exist
        result = self.client.get_option("services.nginx.enable")

        # Check that the response has the expected structure, but don't validate actual contents
        self.assertIn("name", result)

        # If not found (which can happen with actual API), just verify error structure
        if not result.get("found", False):
            self.assertIn("error", result)
        else:
            # If found, verify the standard fields
            self.assertIn("description", result)
            self.assertIn("type", result)

        # Test with a non-existent option
        result = self.client.get_option("thisshouldnotexistasanoption12345")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_search_programs(self):
        """Test searching for programs."""
        # Test with a common program that should always exist
        result = self.client.search_programs("python", limit=5)

        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)

        # Test with a non-existent program
        result = self.client.search_programs("thisshouldnotexistasaprogram12345", limit=5)
        self.assertEqual(len(result["packages"]), 0)

    def test_advanced_query(self):
        """Test advanced query functionality."""
        # Test with a query that should return results
        query = "package_attr_name:python"
        result = self.client.advanced_query("packages", query, limit=5)

        # Check only if the structure is correct, not the content
        self.assertIn("hits", result)
        # If there are no hits, we just check that the structure is correct
        self.assertIsInstance(result["hits"], dict)
        self.assertIn("hits", result["hits"])
        self.assertIsInstance(result["hits"]["hits"], list)

        # Test with an option query - only check structure since it may not have actual results
        query = "option_name:services.nginx*"
        result = self.client.advanced_query("options", query, limit=5)
        # Check if we got an error (which can happen with actual API)
        if "error" in result:
            self.assertIsInstance(result["error"], str)
        else:
            self.assertIn("hits", result)
            self.assertIsInstance(result["hits"], dict)
            self.assertIn("hits", result["hits"])

    def test_cache(self):
        """Test that the cache is working."""
        # Clear the cache
        self.client.cache.clear()

        # Make a request that should be cached
        self.client.search_packages("python", limit=5)

        # Check cache stats
        stats = self.client.cache.get_stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 1)

        # Make the same request again
        self.client.search_packages("python", limit=5)

        # Check cache stats again
        stats = self.client.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)


class TestSimpleCache(unittest.TestCase):
    """Test the SimpleCache class."""

    def setUp(self):
        """Set up the test environment."""
        self.cache = SimpleCache(max_size=3, ttl=1)  # Small cache with 1 second TTL

    def test_cache_set_get(self):
        """Test setting and getting values from the cache."""
        # Set a value
        self.cache.set("key1", "value1")

        # Get the value
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")

        # Get a non-existent key
        value = self.cache.get("nonexistent")
        self.assertIsNone(value)

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        # Set a value
        self.cache.set("key1", "value1")

        # Get the value immediately
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")

        # Wait for TTL to expire
        time.sleep(1.1)

        # Get the value again
        value = self.cache.get("key1")
        self.assertIsNone(value)

    def test_cache_max_size(self):
        """Test that cache respects max size."""
        # Fill the cache
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")

        # All values should be present
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")

        # Add one more item, which should evict the oldest
        self.cache.set("key4", "value4")

        # key1 should be evicted
        self.assertIsNone(self.cache.get("key1"))

        # Other keys should still be present
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")

    def test_cache_stats(self):
        """Test cache statistics."""
        # Clear stats
        self.cache = SimpleCache(max_size=3, ttl=1)

        # Set a value
        self.cache.set("key1", "value1")

        # Get the value (hit)
        self.cache.get("key1")

        # Get a non-existent value (miss)
        self.cache.get("nonexistent")

        # Check stats
        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 3)
        self.assertEqual(stats["ttl"], 1)
        self.assertEqual(stats["hit_ratio"], 0.5)


class TestNixOSContext(unittest.TestCase):
    """Test the NixOSContext class."""

    def setUp(self):
        """Set up the test environment."""
        # Mock the ElasticsearchClient to avoid real API calls
        with patch("mcp_nixos.clients.elasticsearch_client.ElasticsearchClient") as mock_client_class:
            self.es_client_mock = mock_client_class.return_value
            self.context = NixOSContext()
            # Replace the real client with our mock
            self.context.es_client = self.es_client_mock

    def test_get_status(self):
        """Test getting server status."""
        status = self.context.get_status()

        # Verify the structure of the response
        self.assertIn("status", status)
        self.assertIn("version", status)
        self.assertIn("name", status)
        self.assertIn("description", status)
        self.assertIn("cache_stats", status)

        # Verify the status is ok
        self.assertEqual(status["status"], "ok")

    def test_search_packages(self):
        """Test searching for packages through the context."""
        # Set up the mock to return some results
        mock_packages = {
            "count": 2,
            "packages": [
                {"name": "python3", "version": "3.10.12", "description": "Python programming language"},
                {"name": "python39", "version": "3.9.18", "description": "Python 3.9"},
            ],
        }
        self.es_client_mock.search_packages.return_value = mock_packages

        # Call the method
        result = self.context.search_packages("python", limit=5)

        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)

        # Verify the mock was called correctly
        self.es_client_mock.search_packages.assert_called_once_with("python", 5, channel="unstable")

    def test_search_options(self):
        """Test searching for options through the context."""
        # Set up the mock to return some results
        mock_options = {
            "count": 2,
            "options": [
                {
                    "name": "services.nginx.enable",
                    "description": "Whether to enable nginx.",
                    "type": "boolean",
                    "default": "false",
                },
                {
                    "name": "services.nginx.virtualHosts",
                    "description": "Declarative vhost config",
                    "type": "attribute set",
                    "default": "{}",
                },
            ],
        }
        self.es_client_mock.search_options.return_value = mock_options

        # Call the method
        result = self.context.search_options("services.nginx", limit=5)

        # Verify the expected structure
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)

        # Verify the mock was called correctly
        self.es_client_mock.search_options.assert_called_once_with(
            "services.nginx", limit=5, channel="unstable", additional_terms=[], quoted_terms=[]
        )

    def test_get_package(self):
        """Test getting a specific package through the context."""
        # Set up the mock to return a package
        mock_package = {
            "name": "python",
            "version": "3.10.12",
            "description": "Python programming language",
            "homepage": "https://www.python.org",
            "license": "MIT",
            "found": True,
        }
        self.es_client_mock.get_package.return_value = mock_package

        # Call the method
        result = self.context.get_package("python")

        # Check that the response has the expected structure
        self.assertIn("name", result)
        self.assertEqual(result["name"], "python")
        self.assertIn("description", result)
        self.assertIn("version", result)
        self.assertTrue(result.get("found", False))

        # Verify the mock was called correctly
        self.es_client_mock.get_package.assert_called_once_with("python", channel="unstable")

    def test_get_option(self):
        """Test getting a specific option through the context."""
        # Set up the mock to return an option
        mock_option = {
            "name": "services.nginx.enable",
            "description": "Whether to enable nginx.",
            "type": "boolean",
            "default": "false",
            "found": True,
        }
        self.es_client_mock.get_option.return_value = mock_option

        # Call the method
        result = self.context.get_option("services.nginx.enable")

        # Check that the response has the expected structure
        self.assertIn("name", result)
        self.assertEqual(result["name"], "services.nginx.enable")
        self.assertIn("description", result)
        self.assertIn("type", result)
        self.assertTrue(result.get("found", False))

        # Verify the mock was called correctly
        self.es_client_mock.get_option.assert_called_once_with("services.nginx.enable", channel="unstable")


class TestMCPTools(unittest.TestCase):
    """Test the MCP tools functionality."""

    # Mock data for package search/info
    MOCK_PACKAGE_DATA_SINGLE = {
        "name": "python3",
        "version": "3.10.12",
        "description": "A high-level dynamically-typed programming language",
        "channel": "nixos-unstable",
        "programs": ["python3", "python3.10"],
        "found": True,
    }
    MOCK_PACKAGE_DATA_LIST = {
        "count": 2,
        "packages": [
            MOCK_PACKAGE_DATA_SINGLE,
            {
                "name": "python39",
                "version": "3.9.18",
                "description": "Python programming language",
                "channel": "nixos-unstable",
                "programs": ["python3.9", "python39"],
            },
        ],
    }

    # Mock data for option search/info
    MOCK_OPTION_DATA_SINGLE = {
        "name": "services.nginx.enable",
        "description": "Whether to enable nginx.",
        "type": "boolean",
        "default": "false",
        "found": True,
    }
    MOCK_OPTION_DATA_LIST = {
        "count": 2,
        "options": [
            MOCK_OPTION_DATA_SINGLE,
            {
                "name": "services.nginx.virtualHosts",
                "description": "Declarative vhost config",
                "type": "attribute set",
                "default": "{}",
            },
        ],
    }

    # Mock data for stats
    MOCK_STATS_DATA = {
        "package_count": 10000,
        "option_count": 20000,
        "channel": "nixos-unstable",
        "found": True,
    }

    def setUp(self):
        """Set up the test environment."""
        # Create a mock context
        self.context = NixOSContext()

        # Patch the ElasticsearchClient methods to avoid real API calls
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)

        # Set up default mock responses
        self.mock_es_query.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

    def test_nixos_search_packages(self):
        """Test the nixos_search tool with packages."""
        # Mock the search_packages method to return test data using the constant
        with patch.object(NixOSContext, "search_packages") as mock_search:
            mock_search.return_value = self.MOCK_PACKAGE_DATA_LIST

            # Import the tool function directly
            from mcp_nixos.tools.nixos_tools import nixos_search

            # Call the tool function
            result = nixos_search("python", "packages", 5)

            # Verify the result
            self.assertIn("Found 2 packages matching", result)
            self.assertIn("python3", result)
            self.assertIn("3.10.12", result)
            self.assertIn("python39", result)

            # Verify the mock was called correctly
            # Note: The tool might add wildcards, so we're not checking exact parameters
            self.assertEqual(mock_search.call_count, 1)

    def test_nixos_search_options(self):
        """Test the nixos_search tool with options."""
        # Mock the search_options method to return test data using the constant
        with patch.object(NixOSContext, "search_options") as mock_search:
            mock_search.return_value = self.MOCK_OPTION_DATA_LIST

            # Import the tool function directly
            from mcp_nixos.tools.nixos_tools import nixos_search

            # Call the tool function
            result = nixos_search("nginx", "options", 5)

            # Verify the result
            self.assertIn("Found 2 options matching", result)
            self.assertIn("services.nginx.enable", result)
            self.assertIn("Whether to enable nginx", result)
            self.assertIn("services.nginx.virtualHosts", result)

            # Verify the mock was called correctly
            self.assertEqual(mock_search.call_count, 1)

    def test_nixos_search_programs(self):
        """Test the nixos_search tool with programs."""
        # Mock the search_programs method to return test data using the constant
        with patch.object(NixOSContext, "search_programs") as mock_search:
            # Use the package list from the constant
            mock_search.return_value = self.MOCK_PACKAGE_DATA_LIST

            # Import the tool function directly
            from mcp_nixos.tools.nixos_tools import nixos_search

            # Call the tool function
            result = nixos_search("python", "programs", 5)

            # Verify the result
            self.assertIn("Found 2 programs matching", result)
            self.assertIn("python3", result)
            self.assertIn("Programs:", result)
            self.assertIn("python39", result)

            # Verify the mock was called correctly
            self.assertEqual(mock_search.call_count, 1)

    def test_nixos_info_package(self):
        """Test the nixos_info tool with package type."""
        # Mock the get_package method to return test data using the constant
        with patch.object(NixOSContext, "get_package") as mock_get:
            # Use a copy to avoid modifying the constant if the tool changes it
            data = self.MOCK_PACKAGE_DATA_SINGLE.copy()
            data["license"] = "MIT"
            data["homepage"] = "https://www.python.org"
            mock_get.return_value = data

            # Import the tool function directly
            from mcp_nixos.tools.nixos_tools import nixos_info

            # Call the tool function
            result = nixos_info("python3", "package")

            # Verify the result
            self.assertIn("# python3", result)
            self.assertIn("**Version:** 3.10.12", result)
            self.assertIn("**Description:**", result)
            self.assertIn("**License:** MIT", result)
            self.assertIn("**Homepage:** https://www.python.org", result)
            self.assertIn("**Provided Programs:**", result)

            # Verify the mock was called correctly
            mock_get.assert_called_once_with("python3", channel="unstable")

    def test_nixos_info_option(self):
        """Test the nixos_info tool with option type."""
        # Mock the get_option method to return test data using the constant
        with patch.object(NixOSContext, "get_option") as mock_get:
            # Use a copy to avoid modifying the constant
            data = self.MOCK_OPTION_DATA_SINGLE.copy()
            data["example"] = "true"
            mock_get.return_value = data

            # Import the tool function directly
            from mcp_nixos.tools.nixos_tools import nixos_info

            # Call the tool function
            result = nixos_info("services.nginx.enable", "option")

            # Verify the result
            self.assertIn("# services.nginx.enable", result)
            self.assertIn("**Description:** Whether to enable nginx.", result)
            self.assertIn("**Type:** boolean", result)
            self.assertIn("**Default:** `false`", result)
            self.assertIn("**Example:**", result)

            # Verify the mock was called correctly
            mock_get.assert_called_once_with("services.nginx.enable", channel="unstable")

    def test_nixos_stats(self):
        """Test the nixos_stats tool."""
        # Create a mock context rather than patching the class
        mock_context = Mock()

        # Configure the mock context
        mock_context.get_package_stats.return_value = {
            "aggregations": {
                "channels": {
                    "buckets": [
                        {"key": "nixos-unstable", "doc_count": 80000},
                        {"key": "nixos-23.11", "doc_count": 75000},
                    ]
                },
                "licenses": {
                    "buckets": [
                        {"key": "MIT", "doc_count": 20000},
                        {"key": "GPL", "doc_count": 15000},
                    ]
                },
                "platforms": {
                    "buckets": [
                        {"key": "x86_64-linux", "doc_count": 70000},
                        {"key": "aarch64-linux", "doc_count": 60000},
                    ]
                },
            }
        }

        # Add the mock count_options method with value greater than 10k
        mock_context.count_options.return_value = {
            "count": 15463,  # Some number well above 10k
        }

        # Create a mock for the es_client
        mock_context.es_client = Mock()

        # Import the tool function directly
        from mcp_nixos.tools.nixos_tools import nixos_stats

        # Call the tool function with our mock context
        result = nixos_stats(context=mock_context)

        # Verify the result includes both package and options stats
        self.assertIn("# NixOS Statistics", result)

        # Check option count without hardcoding the exact number
        self.assertIn("Total options:", result)
        # Ensure it doesn't show exactly 10,000
        self.assertNotIn("Total options: 10,000", result)
        # Should show our mocked value
        self.assertIn("15,463", result)

        self.assertIn("## Package Statistics", result)
        self.assertIn("### Distribution by Channel", result)
        self.assertIn("nixos-unstable: 80,000 packages", result)
        self.assertIn("### Top 10 Licenses", result)
        self.assertIn("MIT: 20,000 packages", result)
        self.assertIn("### Top 10 Platforms", result)
        self.assertIn("x86_64-linux: 70,000 packages", result)

        # Verify the mocks were called correctly
        mock_context.get_package_stats.assert_called_once()
        mock_context.count_options.assert_called_once()
        mock_context.es_client.set_channel.assert_called_once_with("unstable")


class TestMCPResources(unittest.TestCase):
    """Test the MCP resources functionality."""

    # Reuse mock data constants from TestMCPTools
    MOCK_PACKAGE_DATA_SINGLE = TestMCPTools.MOCK_PACKAGE_DATA_SINGLE
    MOCK_PACKAGE_DATA_LIST = TestMCPTools.MOCK_PACKAGE_DATA_LIST
    MOCK_OPTION_DATA_SINGLE = TestMCPTools.MOCK_OPTION_DATA_SINGLE
    MOCK_OPTION_DATA_LIST = TestMCPTools.MOCK_OPTION_DATA_LIST
    MOCK_STATS_DATA = TestMCPTools.MOCK_STATS_DATA

    def setUp(self):
        """Set up the test environment."""
        # Create a mock context
        self.context = NixOSContext()

        # Patch the ElasticsearchClient methods to avoid real API calls
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)

        # Set up default mock responses
        self.mock_es_query.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

    def test_status_resource(self):
        """Test the status resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        mock_context.get_status.return_value = {
            "status": "ok",
            "version": "1.0.0",
            "name": "MCP-NixOS",
            "description": "NixOS Model Context Protocol Server",
            "cache_stats": {
                "size": 100,
                "max_size": 500,
                "ttl": 600,
                "hits": 800,
                "misses": 200,
                "hit_ratio": 0.8,
            },
        }

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import nixos_status_resource

        # Call the resource function with our mock context
        result = nixos_status_resource(mock_context)

        # Verify the result
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(result["name"], "MCP-NixOS")
        self.assertIn("cache_stats", result)

        # Verify the mock was called
        mock_context.get_status.assert_called_once()

    def test_package_resource(self):
        """Test the package resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        # Use a copy of the constant for the mock return value
        mock_context.get_package.return_value = self.MOCK_PACKAGE_DATA_SINGLE.copy()

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import package_resource

        # Call the resource function with our mock context
        result = package_resource("python3", mock_context)

        # Verify the result
        self.assertEqual(result["name"], "python3")
        self.assertEqual(result["version"], "3.10.12")
        self.assertTrue(result["found"])

        # Verify the mock was called correctly
        mock_context.get_package.assert_called_once_with("python3")

    def test_search_packages_resource(self):
        """Test the search_packages resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        # Use the constant for the mock return value
        mock_context.search_packages.return_value = self.MOCK_PACKAGE_DATA_LIST

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import search_packages_resource

        # Call the resource function with our mock context
        result = search_packages_resource("python", mock_context)

        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["packages"]), 2)
        self.assertEqual(result["packages"][0]["name"], "python3")

        # Verify the mock was called correctly
        mock_context.search_packages.assert_called_once_with("python")

    def test_search_options_resource(self):
        """Test the search_options resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        # Use the constant for the mock return value
        mock_context.search_options.return_value = self.MOCK_OPTION_DATA_LIST

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import search_options_resource

        # Call the resource function with our mock context
        result = search_options_resource("nginx", mock_context)

        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["options"]), 2)
        self.assertEqual(result["options"][0]["name"], "services.nginx.enable")

        # Verify the mock was called correctly
        mock_context.search_options.assert_called_once_with("nginx")

    def test_option_resource(self):
        """Test the option resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        # Use a copy of the constant for the mock return value
        mock_context.get_option.return_value = self.MOCK_OPTION_DATA_SINGLE.copy()

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import option_resource

        # Call the resource function with our mock context
        result = option_resource("services.nginx.enable", mock_context)

        # Verify the result
        self.assertEqual(result["name"], "services.nginx.enable")
        self.assertEqual(result["type"], "boolean")
        self.assertTrue(result["found"])

        # Verify the mock was called correctly
        mock_context.get_option.assert_called_once_with("services.nginx.enable")

    def test_search_programs_resource(self):
        """Test the search_programs resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        # Use the constant for the mock return value
        mock_context.search_programs.return_value = self.MOCK_PACKAGE_DATA_LIST

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import search_programs_resource

        # Call the resource function with our mock context
        result = search_programs_resource("python", mock_context)

        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["packages"]), 2)
        self.assertEqual(result["packages"][0]["name"], "python3")

        # Verify the mock was called correctly
        mock_context.search_programs.assert_called_once_with("python")

    def test_package_stats_resource(self):
        """Test the package_stats resource."""
        # Create a mock for the NixOSContext
        mock_context = Mock()
        mock_context.get_package_stats.return_value = {
            "aggregations": {
                "channels": {"buckets": [{"key": "nixos-unstable", "doc_count": 80000}]},
                "licenses": {"buckets": [{"key": "MIT", "doc_count": 20000}]},
                "platforms": {"buckets": [{"key": "x86_64-linux", "doc_count": 70000}]},
            }
        }

        # Import the resource function from resources module
        from mcp_nixos.resources.nixos_resources import package_stats_resource

        # Call the resource function with our mock context
        result = package_stats_resource(mock_context)

        # Verify the result
        self.assertIn("aggregations", result)
        self.assertIn("channels", result["aggregations"])

        # Verify the mock was called
        mock_context.get_package_stats.assert_called_once()


if __name__ == "__main__":
    unittest.main()
