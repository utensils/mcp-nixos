"""
Helper functions for MCP-NixOS.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

import requests

# Import version for user agent
from mcp_nixos import __version__

# Get logger
logger = logging.getLogger("mcp_nixos")

# Type variables for better type annotations
T = TypeVar("T")


def create_wildcard_query(query: str) -> str:
    """Create a wildcard query from a regular query string.

    Args:
        query: The original query string

    Returns:
        A query string with wildcards added
    """
    if " " in query:
        # For multi-word queries, add wildcards around each word
        words = query.split()
        wildcard_terms = [f"*{word}*" for word in words]
        return " ".join(wildcard_terms)
    else:
        # For single word queries, just wrap with wildcards
        return f"*{query}*"


def extract_hierarchical_paths(query: str) -> tuple[list[str], list[str]]:
    """Extract hierarchical paths (containing dots) from a multi-word query.

    Args:
        query: The original multi-word query string

    Returns:
        A tuple containing (hierarchical_parts, non_hierarchical_parts)
    """
    words = query.split()
    hierarchical_parts = [word for word in words if "." in word]
    non_hierarchical_parts = [word for word in words if "." not in word]

    return hierarchical_parts, non_hierarchical_parts


def parse_multi_word_query(query: str) -> dict:
    """Parse a multi-word query into structured components for better search.

    This function handles complex queries with:
    - Hierarchical paths (dot-notation)
    - Space-separated terms
    - Quoted phrases

    Args:
        query: The original query string

    Returns:
        A dictionary with:
        - main_path: The primary hierarchical path (if any)
        - additional_paths: Other hierarchical paths
        - terms: Regular search terms
        - quoted_terms: Terms that should be searched exactly as provided
        - original: The original query
    """
    # Initialize result
    result = {"main_path": None, "additional_paths": [], "terms": [], "quoted_terms": [], "original": query}

    # Extract quoted terms first
    quoted_terms = []
    unquoted_query = query

    # Simple quote handling (doesn't handle escaped quotes yet)
    quote_positions = []
    in_quote = False
    start_pos = -1

    for i, char in enumerate(query):
        if char == '"' and (i == 0 or query[i - 1] != "\\"):
            if not in_quote:
                start_pos = i
                in_quote = True
            else:
                quote_positions.append((start_pos, i))
                in_quote = False

    # Extract quoted sections
    for start, end in sorted(quote_positions, reverse=True):
        quoted_term = query[start + 1 : end]  # Remove the quotes
        quoted_terms.append(quoted_term)
        # Remove the quoted section from the unquoted query
        unquoted_query = unquoted_query[:start] + " " + unquoted_query[end + 1 :]

    result["quoted_terms"] = quoted_terms

    # Process the remaining unquoted parts
    hierarchical_parts, non_hierarchical_parts = extract_hierarchical_paths(unquoted_query)

    # Set the main hierarchical path if exists
    if hierarchical_parts:
        result["main_path"] = hierarchical_parts[0]
        result["additional_paths"] = hierarchical_parts[1:]

    # Add regular terms
    result["terms"] = non_hierarchical_parts

    return result


def get_context_or_fallback(context: Optional[T], context_name: str) -> Optional[T]:
    """Get the provided context or fall back to global context.

    Args:
        context: The context passed to the function, potentially None
        context_name: The name of the context to retrieve from server if not provided

    Returns:
        The provided context or the global context from the server, or None if not found
    """
    if context is None:
        # Import here to avoid circular imports
        import mcp_nixos.server

        # Handle various context types
        if hasattr(mcp_nixos.server, context_name):
            return getattr(mcp_nixos.server, context_name)
        else:
            logger.warning(f"Context '{context_name}' not found in server")
            return None

    return context


def check_loading_status(func: Callable) -> Callable:
    """Decorator that checks if Home Manager client is loaded before executing a method.

    This decorator is intended for HomeManagerContext methods to avoid duplicating the
    loading status check code across multiple methods.

    Args:
        func: The function to decorate

    Returns:
        A wrapped function that checks loading status before executing
    """

    def wrapper(self, *args, **kwargs):
        # Get the default response values based on the method name
        method_name = func.__name__
        default_values = {}

        # Add method-specific default values
        if method_name == "search_options":
            default_values = {"count": 0, "options": []}
        elif method_name == "get_option" and args:
            default_values = {"name": args[0]}  # First arg should be option_name
        elif method_name == "get_stats":
            default_values = {"total_options": 0}

        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                response = {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                }
                response.update(default_values)
                return response

            # If loading failed, report the error
            if self.hm_client.loading_error:
                response = {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                }
                response.update(default_values)
                return response

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            response = {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
            }
            response.update(default_values)
            return response

        # If we get here, the client is loaded and ready, so call the original function
        return func(self, *args, **kwargs)

    return wrapper


def make_http_request(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    auth: Optional[Tuple[str, str]] = None,
    timeout: Tuple[float, float] = (5.0, 15.0),
    max_retries: int = 3,
    retry_delay: float = 1.0,
    cache: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make an HTTP request with robust error handling and retries.

    This is a common utility function to standardize HTTP requests across the codebase.
    It handles retries with exponential backoff, caching, error handling, and logging.

    Args:
        url: The URL to request
        method: HTTP method (GET or POST)
        json_data: JSON data to send (for POST requests)
        auth: Optional authentication tuple (username, password)
        timeout: Tuple of (connect_timeout, read_timeout) in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        cache: Optional cache instance (must have get/set methods)
        headers: Optional custom headers to include in the request

    Returns:
        Dict containing either the JSON response or an error message
    """
    # Check if result is in cache
    cache_key = None
    if cache is not None:
        method_key = method.lower()

        # Extract channel information from URL for ES requests to ensure proper cache separation
        channel_key = ""
        if "latest-43-nixos" in url:
            if "unstable" in url:
                channel_info = "unstable"
            elif "24.11" in url:
                channel_info = "24.11"
            else:
                channel_info = "unknown"
            channel_key = f":channel={channel_info}"
            logger.debug(f"Making request to {channel_info} channel index: {url}")

        # Include channel in the cache key to prevent cross-channel cache contamination
        data_key = "" if json_data is None else f":{str(json_data)}"
        cache_key = f"{method_key}:{url}{channel_key}{data_key}"

        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for request: {cache_key[:100]}...")
            return cached_result
        logger.debug(f"Cache miss for request: {cache_key[:100]}...")

    # Common headers
    default_headers = {
        "User-Agent": f"MCP-NixOS/{__version__}",
        "Accept-Encoding": "gzip, deflate",
    }

    # Add content-type for JSON requests
    if json_data is not None:
        default_headers["Content-Type"] = "application/json"

    # Merge default headers with custom headers if provided
    request_headers = headers if headers is not None else {}
    for key, value in default_headers.items():
        if key not in request_headers:
            request_headers[key] = value

    for attempt in range(max_retries):
        try:
            # Make the request
            if method.upper() == "POST":
                response = requests.post(url, json=json_data, auth=auth, headers=request_headers, timeout=timeout)
            else:  # Default to GET
                response = requests.get(url, auth=auth, headers=request_headers, timeout=timeout)

            # Handle 4xx client errors
            if 400 <= response.status_code < 500:
                logger.warning(f"Client error ({response.status_code}) for URL: {url}")
                error_result = {"error": f"Request failed with status {response.status_code}"}

                # For 401/403, provide authentication error
                if response.status_code in (401, 403):
                    error_result["error"] = "Authentication failed"

                # For 400 bad request, try to include response body for more details
                if response.status_code == 400:
                    try:
                        error_result["details"] = response.json()
                    except Exception:
                        pass

                return error_result

            # Handle 5xx server errors with retry
            if response.status_code >= 500:
                logger.error(f"Server error ({response.status_code}) for URL: {url}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                return {"error": f"Server error ({response.status_code})"}

            # Handle successful responses
            response.raise_for_status()  # Raise for any other error codes

            # Try to parse JSON response
            try:
                result = response.json()
                # Cache successful result if cache is available
                if cache is not None and cache_key is not None:
                    cache.set(cache_key, result)
                return result
            except (ValueError, AttributeError):
                # If not JSON, return text content
                return {"text": response.text}

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for URL: {url}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                time.sleep(wait_time)
                continue
            return {"error": "Failed to connect to server"}

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                time.sleep(wait_time)
                continue
            return {"error": "Request timed out"}

        except Exception as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            return {"error": f"Request error: {str(e)}"}

    # We should never reach here, but just in case
    return {"error": f"Request failed after {max_retries} attempts"}
