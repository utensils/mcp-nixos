"""
Elasticsearch client for accessing NixOS package and option data via search.nixos.org API.
"""

import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Import SimpleCache and HTTP helper
from mcp_nixos.cache.simple_cache import SimpleCache
from mcp_nixos.utils.helpers import make_http_request

# Get logger
logger = logging.getLogger("mcp_nixos")

# --- Constants ---
# Default connection settings
DEFAULT_ES_URL = "https://search.nixos.org/backend"
DEFAULT_ES_USER = "aWVSALXpZv"
DEFAULT_ES_PASSWORD = "X8gPHnzL52wFEekuxsfQ9cSh"
DEFAULT_CACHE_TTL = 600  # 10 minutes
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_CONNECT_TIMEOUT = 3.0
DEFAULT_READ_TIMEOUT = 10.0

# Channel to Index mapping
AVAILABLE_CHANNELS = {
    "unstable": "latest-43-nixos-unstable",
    "25.05": "latest-43-nixos-25.05",  # Beta channel
    "beta": "latest-43-nixos-25.05",  # Alias for beta
    "24.11": "latest-43-nixos-24.11",
    "stable": "latest-43-nixos-24.11",  # Alias for stable
}
DEFAULT_CHANNEL = "unstable"

# Elasticsearch Field Names
FIELD_PKG_NAME = "package_attr_name"
FIELD_PKG_PNAME = "package_pname"
FIELD_PKG_VERSION = "package_version"
FIELD_PKG_DESC = "package_description"
FIELD_PKG_LONG_DESC = "package_longDescription"
FIELD_PKG_PROGRAMS = "package_programs"
FIELD_PKG_LICENSE = "package_license"
FIELD_PKG_HOMEPAGE = "package_homepage"
FIELD_PKG_MAINTAINERS = "package_maintainers"
FIELD_PKG_PLATFORMS = "package_platforms"
FIELD_PKG_POSITION = "package_position"
FIELD_PKG_OUTPUTS = "package_outputs"
FIELD_PKG_CHANNEL = "package_channel"  # Added for parsing

FIELD_OPT_NAME = "option_name"
FIELD_OPT_DESC = "option_description"
FIELD_OPT_TYPE = "option_type"
FIELD_OPT_DEFAULT = "option_default"
FIELD_OPT_EXAMPLE = "option_example"
FIELD_OPT_DECL = "option_declarations"
FIELD_OPT_READONLY = "option_readOnly"
FIELD_OPT_MANUAL_URL = "option_manual_url"
FIELD_OPT_ADDED_IN = "option_added_in"
FIELD_OPT_DEPRECATED_IN = "option_deprecated_in"

FIELD_TYPE = "type"  # Used for filtering options vs packages

# Boost Constants
BOOST_PKG_NAME = 10.0
BOOST_PKG_PNAME = 8.0
BOOST_PKG_PREFIX_NAME = 7.0
BOOST_PKG_PREFIX_PNAME = 6.0
BOOST_PKG_WILDCARD_NAME = 5.0
BOOST_PKG_WILDCARD_PNAME = 4.0
BOOST_PKG_DESC = 3.0
BOOST_PKG_PROGRAMS = 6.0

BOOST_OPT_NAME_EXACT = 10.0
BOOST_OPT_NAME_PREFIX = 8.0
BOOST_OPT_NAME_WILDCARD = 6.0
BOOST_OPT_DESC_TERM = 4.0
BOOST_OPT_DESC_PHRASE = 6.0
BOOST_OPT_SERVICE_DESC = 2.0

BOOST_PROG_TERM = 10.0
BOOST_PROG_PREFIX = 5.0
BOOST_PROG_WILDCARD = 3.0


# --- Elasticsearch Client Class ---


class ElasticsearchClient:
    """Client for querying NixOS data via the search.nixos.org Elasticsearch API."""

    def __init__(self):
        """Initialize the Elasticsearch client with caching and authentication."""
        self.es_base_url: str = os.environ.get("ELASTICSEARCH_URL", DEFAULT_ES_URL)
        es_user: str = os.environ.get("ELASTICSEARCH_USER", DEFAULT_ES_USER)
        es_password: str = os.environ.get("ELASTICSEARCH_PASSWORD", DEFAULT_ES_PASSWORD)
        self.es_auth: Tuple[str, str] = (es_user, es_password)

        # Give this client instance a unique ID for debugging
        self.instance_id = str(uuid.uuid4())[:8]

        self.available_channels: Dict[str, str] = AVAILABLE_CHANNELS
        # Add channel versioning to the cache to ensure old entries are properly invalidated
        cache_version = "channel_aware_v1.2"
        self.cache: SimpleCache = SimpleCache(max_size=500, ttl=DEFAULT_CACHE_TTL, version=cache_version)

        # Timeouts and Retries
        self.connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
        self.read_timeout: float = DEFAULT_READ_TIMEOUT
        self.max_retries: int = DEFAULT_MAX_RETRIES
        self.retry_delay: float = DEFAULT_RETRY_DELAY

        # Set default channel and URLs - initialize with empty strings
        self._current_channel_id: str = ""  # Internal state for current index
        self.es_packages_url: str = ""
        self.es_options_url: str = ""

        # Call set_channel to initialize the URLs with the default channel
        self.set_channel(DEFAULT_CHANNEL)  # Initialize URLs

        logger.info(
            f"Elasticsearch client initialized (id={self.instance_id}) for {self.es_base_url} "
            f"with channel={DEFAULT_CHANNEL}"
        )

    def set_channel(self, channel: str) -> None:
        """Set the NixOS channel (Elasticsearch index) to use for queries."""
        # Normalize channel name to lowercase
        ch_lower = channel.lower()

        # First check if we need to handle aliases
        if ch_lower == "stable":
            logger.debug("Converting 'stable' alias to actual channel name: 24.11")
            ch_lower = "24.11"  # Always convert stable to the actual version
        elif ch_lower == "beta":
            logger.debug("Converting 'beta' alias to actual channel name: 25.05")
            ch_lower = "25.05"  # Always convert beta to the actual version

        # Then check if the channel is valid
        if ch_lower not in self.available_channels:
            logger.warning(f"Unknown channel '{channel}', falling back to '{DEFAULT_CHANNEL}'")
            ch_lower = DEFAULT_CHANNEL

        # Get the actual Elasticsearch index ID for this channel
        channel_id = self.available_channels[ch_lower]

        # Check if we're actually changing the channel
        is_channel_change = channel_id != self._current_channel_id

        # Always update the internal state
        self._current_channel_id = channel_id

        # Always update the URLs for consistent behavior
        self.es_packages_url = f"{self.es_base_url}/{channel_id}/_search"
        self.es_options_url = f"{self.es_base_url}/{channel_id}/_search"

        # Only clear the cache when actually changing channels
        if is_channel_change:
            logger.info(f"Channel changed to '{ch_lower}' (index: {channel_id})")
            if hasattr(self, "cache") and self.cache is not None:
                logger.info("Clearing cache due to channel change")
                self.cache.clear()
        else:
            logger.debug(f"Channel already set to '{ch_lower}' (index: {channel_id})")

    def safe_elasticsearch_query(self, endpoint: str, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an Elasticsearch query with HTTP handling, retries, and caching."""
        # Use the shared HTTP utility function which includes caching and retries
        result = make_http_request(
            url=endpoint,
            method="POST",
            json_data=query_data,
            auth=self.es_auth,
            timeout=(self.connect_timeout, self.read_timeout),
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            cache=self.cache,  # Pass the client's cache instance
        )

        # If there's an error property in the result, handle it properly
        if "error" in result:
            error_details = result["error"]
            error_message = f"Elasticsearch request failed: {error_details}"  # Default

            # Pass through the error directly if it's a simple string
            if isinstance(error_details, str):
                if "authentication failed" in error_details.lower() or "unauthorized" in error_details.lower():
                    error_message = f"Authentication failed: {error_details}"
                elif "timed out" in error_details.lower() or "timeout" in error_details.lower():
                    error_message = f"Request timed out: {error_details}"
                elif "connect" in error_details.lower():
                    error_message = f"Connection error: {error_details}"
                elif "server error" in error_details.lower() or "500" in error_details:
                    error_message = f"Server error: {error_details}"
                elif "invalid query" in error_details.lower() or "400" in error_details:
                    error_message = f"Invalid query: {error_details}"
            # Handle ES-specific error object structure
            elif isinstance(error_details, dict) and (es_error := error_details.get("error", {})):
                if isinstance(es_error, dict) and (reason := es_error.get("reason")):
                    error_message = f"Elasticsearch error: {reason}"
                elif isinstance(es_error, str):
                    error_message = f"Elasticsearch error: {es_error}"
                else:
                    error_message = "Unknown Elasticsearch error format"
            else:
                error_message = "Unknown error during Elasticsearch query"

            result["error_message"] = error_message
            # Ensure hits are removed on error
            if "hits" in result:
                del result["hits"]

        return result

    def _parse_hits(self, hits: List[Dict[str, Any]], result_type: str = "package") -> List[Dict[str, Any]]:
        """Parse Elasticsearch hits into a list of package or option dictionaries."""
        parsed_items = []
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0.0)

            if result_type == "package":
                version = source.get(FIELD_PKG_VERSION, source.get("package_pversion", ""))
                item = {
                    "name": source.get(FIELD_PKG_NAME, ""),
                    "pname": source.get(FIELD_PKG_PNAME, ""),
                    "version": version,
                    "description": source.get(FIELD_PKG_DESC, ""),
                    "channel": source.get(FIELD_PKG_CHANNEL, ""),
                    "score": score,
                    "programs": source.get(FIELD_PKG_PROGRAMS, []),
                    "longDescription": source.get(FIELD_PKG_LONG_DESC, ""),
                    "license": source.get(FIELD_PKG_LICENSE, ""),
                    "homepage": source.get(FIELD_PKG_HOMEPAGE, ""),
                    "maintainers": source.get(FIELD_PKG_MAINTAINERS, []),
                    "platforms": source.get(FIELD_PKG_PLATFORMS, []),
                    "position": source.get(FIELD_PKG_POSITION, ""),
                    "outputs": source.get(FIELD_PKG_OUTPUTS, []),
                }
                parsed_items.append(item)
            elif result_type == "option":
                if source.get(FIELD_TYPE) == "option":
                    item = {
                        "name": source.get(FIELD_OPT_NAME, ""),
                        "description": source.get(FIELD_OPT_DESC, ""),
                        "type": source.get(FIELD_OPT_TYPE, ""),
                        "default": source.get(FIELD_OPT_DEFAULT, None),
                        "example": source.get(FIELD_OPT_EXAMPLE, None),
                        "score": score,
                        "declarations": source.get(FIELD_OPT_DECL, []),
                        "readOnly": source.get(FIELD_OPT_READONLY, False),
                        "manual_url": source.get(FIELD_OPT_MANUAL_URL, ""),
                        "introduced_version": source.get(FIELD_OPT_ADDED_IN, ""),
                        "deprecated_version": source.get(FIELD_OPT_DEPRECATED_IN, ""),
                    }
                    parsed_items.append(item)

        return parsed_items

    def _build_term_phrase_queries(self, terms: List[str], phrases: List[str]) -> List[Dict[str, Any]]:
        """Build ES 'should' clauses for matching terms/phrases in option descriptions."""
        clauses = []
        for term in terms:
            clauses.append({"match": {FIELD_OPT_DESC: {"query": term, "boost": BOOST_OPT_DESC_TERM}}})
        for phrase in phrases:
            clauses.append({"match_phrase": {FIELD_OPT_DESC: {"query": phrase, "boost": BOOST_OPT_DESC_PHRASE}}})
        return clauses

    def _build_package_query_dsl(self, query: str) -> Dict[str, Any]:
        """Builds the core Elasticsearch query DSL for packages."""
        should_clauses = [
            {"term": {FIELD_PKG_NAME: {"value": query, "boost": BOOST_PKG_NAME}}},
            {"term": {FIELD_PKG_PNAME: {"value": query, "boost": BOOST_PKG_PNAME}}},
            {"prefix": {FIELD_PKG_NAME: {"value": query, "boost": BOOST_PKG_PREFIX_NAME}}},
            {"prefix": {FIELD_PKG_PNAME: {"value": query, "boost": BOOST_PKG_PREFIX_PNAME}}},
            {"wildcard": {FIELD_PKG_NAME: {"value": f"*{query}*", "boost": BOOST_PKG_WILDCARD_NAME}}},
            {"wildcard": {FIELD_PKG_PNAME: {"value": f"*{query}*", "boost": BOOST_PKG_WILDCARD_PNAME}}},
            {"match": {FIELD_PKG_DESC: {"query": query, "boost": BOOST_PKG_DESC}}},
            {"match": {FIELD_PKG_PROGRAMS: {"query": query, "boost": BOOST_PKG_PROGRAMS}}},
        ]
        return {"bool": {"should": should_clauses, "minimum_should_match": 1}}

    def _build_option_name_clauses(self, query: str) -> List[Dict[str, Any]]:
        """Builds clauses for matching the option name based on query structure."""
        should_clauses = []
        if "*" in query:  # Explicit wildcard query
            should_clauses.append(
                {
                    "wildcard": {
                        FIELD_OPT_NAME: {"value": query, "case_insensitive": True, "boost": BOOST_OPT_NAME_WILDCARD}
                    }
                }
            )
        elif "." in query:  # Hierarchical path query
            should_clauses.append({"prefix": {FIELD_OPT_NAME: {"value": query, "boost": BOOST_OPT_NAME_EXACT}}})
            should_clauses.append(
                {
                    "wildcard": {
                        FIELD_OPT_NAME: {
                            "value": f"{query}.*",
                            "case_insensitive": True,
                            "boost": BOOST_OPT_NAME_PREFIX,
                        }
                    }
                }
            )
            should_clauses.append(
                {
                    "wildcard": {
                        FIELD_OPT_NAME: {
                            "value": f"{query}*",
                            "case_insensitive": True,
                            "boost": BOOST_OPT_NAME_WILDCARD,
                        }
                    }
                }
            )
        else:  # Simple term query
            should_clauses.extend(
                [
                    {"term": {FIELD_OPT_NAME: {"value": query, "boost": BOOST_OPT_NAME_EXACT}}},
                    {"prefix": {FIELD_OPT_NAME: {"value": query, "boost": BOOST_OPT_NAME_PREFIX}}},
                    {
                        "wildcard": {
                            FIELD_OPT_NAME: {
                                "value": f"*{query}*",
                                "case_insensitive": True,
                                "boost": BOOST_OPT_NAME_WILDCARD,
                            }
                        }
                    },
                    {"match": {FIELD_OPT_DESC: {"query": query, "boost": BOOST_OPT_DESC_TERM}}},
                ]
            )
        return should_clauses

    def _build_option_query_dsl(
        self, query: str, additional_terms: List[str], quoted_terms: List[str]
    ) -> Dict[str, Any]:
        """Builds the core Elasticsearch query DSL for options."""
        is_service_path = query.startswith("services.")
        service_name = query.split(".", 2)[1] if is_service_path and len(query.split(".")) > 1 else ""

        # Build clauses for matching the option name
        name_clauses = self._build_option_name_clauses(query)

        # Build clauses for description matching
        desc_clauses = self._build_term_phrase_queries(additional_terms, quoted_terms)

        # Combine all clauses
        should_clauses = name_clauses + desc_clauses

        # Boost matches mentioning the service name in description for service paths
        if is_service_path and service_name:
            should_clauses.append({"match": {FIELD_OPT_DESC: {"query": service_name, "boost": BOOST_OPT_SERVICE_DESC}}})

        # Use dis_max for combining different types of matches effectively
        # The outer bool/must structure is kept to align with test expectations
        query_part = {"dis_max": {"queries": should_clauses}}
        return {"bool": {"must": [query_part]}}

    def _build_program_query_dsl(self, query: str) -> Dict[str, Any]:
        """Builds the core Elasticsearch query DSL for programs."""
        should_clauses = [
            {"term": {FIELD_PKG_PROGRAMS: {"value": query, "boost": BOOST_PROG_TERM}}},
            {"prefix": {FIELD_PKG_PROGRAMS: {"value": query, "boost": BOOST_PROG_PREFIX}}},
            {"wildcard": {FIELD_PKG_PROGRAMS: {"value": f"*{query}*", "boost": BOOST_PROG_WILDCARD}}},
        ]
        return {"bool": {"should": should_clauses, "minimum_should_match": 1}}

    def _build_search_query(
        self, query: str, search_type: str, additional_terms: List[str] = [], quoted_terms: List[str] = []
    ) -> Dict[str, Any]:
        """Builds the full Elasticsearch query including filters."""
        base_filter = []
        if search_type == "option":
            base_filter.append({"term": {FIELD_TYPE: "option"}})
        # Add other base filters if needed

        query_dsl: Dict[str, Any] = {}
        if search_type == "package":
            query_dsl = self._build_package_query_dsl(query)
        elif search_type == "option":
            query_dsl = self._build_option_query_dsl(query, additional_terms, quoted_terms)
        elif search_type == "program":
            query_dsl = self._build_program_query_dsl(query)
        else:
            logger.error(f"Invalid search_type '{search_type}' passed to _build_search_query")
            return {"match_none": {}}

        # Combine the generated DSL with the base filter
        if "bool" in query_dsl:
            # Merge the base filter into the existing bool query's filter clause
            query_dsl["bool"]["filter"] = query_dsl["bool"].get("filter", []) + base_filter
        else:
            # If the DSL is not already a bool query, wrap it
            query_dsl = {"bool": {"must": [query_dsl], "filter": base_filter}}

        return query_dsl

    # --- Public Search Methods ---

    def search_packages(
        self, query: str, limit: int = 50, offset: int = 0, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Search for NixOS packages."""
        logger.info(f"Searching packages: query='{query}', limit={limit}, channel={channel}")
        self.set_channel(channel)

        # Log channel details for debugging
        ch_lower = channel.lower()
        channel_id = self.available_channels.get(ch_lower, self.available_channels[DEFAULT_CHANNEL])
        logger.debug(f"Package search using channel='{ch_lower}', index='{channel_id}', URL={self.es_packages_url}")

        match = re.match(r"([a-zA-Z0-9_-]+?)([\d.]+)?Packages\.(.*)", query)
        if match:
            base_pkg, _, sub_pkg = match.groups()
            logger.debug(f"Query resembles specific package version: {base_pkg}, {sub_pkg}")

        es_query = self._build_search_query(query, search_type="package")
        request_data = {"from": offset, "size": limit, "query": es_query, "sort": [{"_score": "desc"}]}
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        if error_msg := data.get("error_message") or data.get("error"):
            return {"count": 0, "packages": [], "error": error_msg}

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        packages = self._parse_hits(hits, "package")

        return {"count": total, "packages": packages}

    def search_options(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        channel: str = "unstable",
        additional_terms: Optional[List[str]] = None,
        quoted_terms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search for NixOS options."""
        add_terms = additional_terms or []
        q_terms = quoted_terms or []
        logger.info(
            f"Searching options: query='{query}', add_terms={add_terms}, "
            f"quoted={q_terms}, limit={limit}, channel={channel}"
        )
        self.set_channel(channel)

        es_query = self._build_search_query(
            query, search_type="option", additional_terms=add_terms, quoted_terms=q_terms
        )
        request_data = {
            "from": offset,
            "size": limit,
            "query": es_query,
            "sort": [{"_score": "desc", FIELD_OPT_NAME: "asc"}],
        }
        data = self.safe_elasticsearch_query(self.es_options_url, request_data)

        if error_msg := data.get("error_message") or data.get("error"):
            return {"count": 0, "options": [], "error": error_msg}

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        options = self._parse_hits(hits, "option")

        return {"count": total, "options": options}

    def search_programs(
        self, program: str, limit: int = 50, offset: int = 0, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Search for packages providing a specific program."""
        logger.info(f"Searching packages providing program: '{program}', limit={limit}, channel={channel}")
        self.set_channel(channel)

        es_query = self._build_search_query(program, search_type="program")
        request_data = {"from": offset, "size": limit, "query": es_query}
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        if error_msg := data.get("error_message") or data.get("error"):
            return {"count": 0, "packages": [], "error": error_msg}

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        packages = self._parse_hits(hits, "package")

        # Post-filter programs list
        program_lower = program.lower()
        filtered_packages = []
        for pkg in packages:
            all_programs = pkg.get("programs", [])
            if not isinstance(all_programs, list):
                continue

            matching_programs = [p for p in all_programs if program_lower in p.lower()]

            if matching_programs:
                pkg["programs"] = matching_programs
                filtered_packages.append(pkg)

        return {"count": total, "packages": filtered_packages}  # Return ES total, but filtered packages

    # --- Get Specific Item Methods ---

    def get_package(self, package_name: str, channel: str = "unstable") -> Dict[str, Any]:
        """Get detailed information for a specific package."""
        logger.info(f"Getting package details for: {package_name}, channel={channel}")
        self.set_channel(channel)
        request_data = {"size": 1, "query": {"term": {FIELD_PKG_NAME: {"value": package_name}}}}
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        if error_msg := data.get("error_message") or data.get("error"):
            return {"name": package_name, "error": error_msg, "found": False}

        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            return {"name": package_name, "error": "Package not found", "found": False}

        packages = self._parse_hits(hits, "package")
        if not packages:
            return {"name": package_name, "error": "Failed to parse package data", "found": False}

        result = packages[0]
        result["found"] = True
        return result

    def get_option(self, option_name: str, channel: str = "unstable") -> Dict[str, Any]:
        """Get detailed information for a specific NixOS option."""
        logger.info(f"Getting option details for: {option_name}, channel={channel}")
        self.set_channel(channel)

        # Query for exact option name, filtering by type:option
        request_data = {
            "size": 1,
            "query": {
                "bool": {
                    "must": [{"term": {FIELD_OPT_NAME: {"value": option_name}}}],
                    "filter": [{"term": {FIELD_TYPE: "option"}}],
                }
            },
        }
        data = self.safe_elasticsearch_query(self.es_options_url, request_data)
        hits = data.get("hits", {}).get("hits", [])

        if not hits and "." in option_name:  # Try prefix search if exact match failed
            logger.debug(f"Option '{option_name}' not found with exact match, trying prefix search.")
            prefix_request_data = {
                "size": 1,
                "query": {
                    "bool": {
                        "must": [{"prefix": {FIELD_OPT_NAME: {"value": option_name}}}],
                        "filter": [{"term": {FIELD_TYPE: "option"}}],
                    }
                },
            }
            prefix_data = self.safe_elasticsearch_query(self.es_options_url, prefix_request_data)
            hits = prefix_data.get("hits", {}).get("hits", [])

        if not hits:
            error_msg = "Option not found"
            not_found_result = {"name": option_name, "error": error_msg, "found": False}
            if option_name.startswith("services."):
                parts = option_name.split(".", 2)
                if len(parts) > 1:
                    service_name = parts[1]
                    not_found_result["error"] = f"Option not found. Try common patterns for '{service_name}' service."
                    not_found_result["is_service_path"] = True
                    not_found_result["service_name"] = service_name
            return not_found_result

        # Parse the found option
        options = self._parse_hits(hits, "option")
        if not options:
            return {"name": option_name, "error": "Failed to parse option data", "found": False}

        result = options[0]
        result["found"] = True

        # Fetch related options ONLY if it's a service path
        is_service_path = result["name"].startswith("services.")
        if is_service_path:
            parts = result["name"].split(".", 2)
            if len(parts) > 1:
                service_name = parts[1]
                service_prefix = f"services.{service_name}."
                logger.debug(f"Fetching related options for service prefix: {service_prefix}")
                related_query = {
                    "size": 5,
                    "query": {
                        "bool": {
                            "must": [{"prefix": {FIELD_OPT_NAME: service_prefix}}],
                            "must_not": [{"term": {FIELD_OPT_NAME: result["name"]}}],
                            "filter": [{"term": {FIELD_TYPE: "option"}}],
                        }
                    },
                }
                related_data = self.safe_elasticsearch_query(self.es_options_url, related_query)
                related_hits = related_data.get("hits", {}).get("hits", [])
                related_options = self._parse_hits(related_hits, "option")

                result["is_service_path"] = True
                result["service_name"] = service_name
                result["related_options"] = related_options

        return result

    # --- Stats Methods ---

    def get_package_stats(self, channel: str = "unstable") -> Dict[str, Any]:
        """Get statistics about NixOS packages."""
        logger.info(f"Getting package statistics for channel: {channel}")
        self.set_channel(channel)
        request_data = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "channels": {"terms": {"field": FIELD_PKG_CHANNEL, "size": 10}},
                "licenses": {"terms": {"field": FIELD_PKG_LICENSE, "size": 10}},
                "platforms": {"terms": {"field": FIELD_PKG_PLATFORMS, "size": 10}},
            },
        }
        return self.safe_elasticsearch_query(self.es_packages_url, request_data)

    def count_options(self, channel: str = "unstable") -> Dict[str, Any]:
        """Get an accurate count of NixOS options using the count API."""
        logger.info(f"Getting options count for channel: {channel}")
        self.set_channel(channel)
        count_endpoint = self.es_options_url.replace("/_search", "/_count")
        request_data = {"query": {"term": {FIELD_TYPE: "option"}}}

        result = self.safe_elasticsearch_query(count_endpoint, request_data)
        if error_msg := result.get("error_message") or result.get("error"):
            return {"count": 0, "error": error_msg}

        return {"count": result.get("count", 0)}

    def search_packages_with_version(
        self, query: str, version_pattern: str, limit: int = 50, offset: int = 0, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Search for packages with a specific version pattern."""
        logger.info(
            f"Searching packages with version pattern: query='{query}', version='{version_pattern}', channel={channel}"
        )
        results = self.search_packages(query, limit=limit * 2, offset=offset, channel=channel)  # Fetch more initially

        if "error" in results:
            return results

        packages = results.get("packages", [])
        filtered_packages = [pkg for pkg in packages if version_pattern in pkg.get("version", "")][:limit]

        return {"count": len(filtered_packages), "packages": filtered_packages}

    # --- Advanced/Other Methods ---

    def advanced_query(
        self, index_type: str, query_string: str, limit: int = 50, offset: int = 0, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Execute a raw query directly using Lucene syntax."""
        logger.info(f"Running advanced query on {index_type}: {query_string}, channel={channel}")
        self.set_channel(channel)

        if index_type not in ["packages", "options"]:
            return {"error": f"Invalid index type: {index_type}. Must be 'packages' or 'options'"}

        endpoint = self.es_packages_url if index_type == "packages" else self.es_options_url
        request_data = {"from": offset, "size": limit, "query": {"query_string": {"query": query_string}}}
        return self.safe_elasticsearch_query(endpoint, request_data)
