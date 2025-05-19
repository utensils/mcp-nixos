"""
MCP tools for NixOS. Provides search, info, and stats functionalities.
"""

import logging
from typing import Any, Dict, List, Optional  # Add List

# Import utility functions
from mcp_nixos.utils.helpers import parse_multi_word_query

# Import get_nixos_context from server
# Import get_nixos_context from utils to avoid circular imports
import importlib

# Get logger
logger = logging.getLogger("mcp_nixos")

# Import channel constants from elasticsearch_client
from mcp_nixos.clients.elasticsearch_client import AVAILABLE_CHANNELS, DEFAULT_CHANNEL

# Define channel constants
CHANNEL_UNSTABLE = DEFAULT_CHANNEL
CHANNEL_STABLE = "stable"  # Alias for stable channel
VALID_CHANNELS = list(AVAILABLE_CHANNELS.keys())  # Central list of valid channels


def get_valid_channels() -> List[str]:
    """Returns a list of valid NixOS channels."""
    return VALID_CHANNELS.copy()  # Return a copy to prevent modification


# --- Helper Functions ---


def _setup_context_and_channel(context: Optional[Any], channel: str) -> Any:
    """Gets the NixOS context and sets the specified channel.

    This function handles the conversion of various context types into a consistent
    context object with channel settings.

    Args:
        context: Can be a NixOSContext instance, string ID, or None
        channel: The channel to use (e.g., "unstable", "stable", "24.11")

    Returns:
        A properly configured context object or None if unavailable
    """
    # Case 1: Context is None - get from server
    if context is None:
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_nixos_context = getattr(server_module, "get_nixos_context")
            ctx = get_nixos_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_nixos_context: {e}")
            return None
    # Case 2: Context is a string ID (from MCP) - treat as None and get from server
    elif isinstance(context, str):
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_nixos_context = getattr(server_module, "get_nixos_context")
            ctx = get_nixos_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_nixos_context: {e}")
            return None
    # Case 3: Context is an object (NixOSContext or request context)
    else:
        ctx = context

    # Validate the context object
    if ctx is None:
        logger.warning("Failed to get NixOS context")
        return None

    # Extract the es_client from the context (handle various context types)
    es_client = None
    if hasattr(ctx, "es_client") and ctx.es_client is not None:
        # Direct NixOSContext
        es_client = ctx.es_client
    elif hasattr(ctx, "request_context") and hasattr(ctx.request_context, "lifespan_context"):
        # FastMCP request context
        nixos_ctx = ctx.request_context.lifespan_context.get("nixos_context")
        if nixos_ctx and hasattr(nixos_ctx, "es_client"):
            es_client = nixos_ctx.es_client

    # Set the channel on the client
    if es_client is not None and hasattr(es_client, "set_channel"):
        # Client will handle "stable" -> "24.11" conversion and validation internally
        es_client.set_channel(channel)
        logger.info(f"Successfully set channel to: {channel}")
    else:
        logger.warning("Unable to set channel: context structure not recognized")

    return ctx


def _format_search_results(results: Dict[str, Any], query: str, search_type: str) -> str:
    """Formats search results for packages, options, or programs."""
    # Note: 'programs' search actually returns packages with program info
    items_key = "options" if search_type == "options" else "packages"
    items = results.get(items_key, [])

    # Prioritize exact matches for better search relevance
    exact_matches = []
    close_matches = []
    other_matches = []

    for item in items:
        name = item.get("name", "Unknown")
        if name.lower() == query.lower():
            exact_matches.append(item)
        elif name.lower().startswith(query.lower()):
            close_matches.append(item)
        else:
            other_matches.append(item)

    sorted_items = exact_matches + close_matches + other_matches
    count = len(sorted_items)

    if count == 0:
        if search_type == "options" and query.startswith("services."):
            return f"No options found for '{query}'"  # Specific message handled later
        return f"No {search_type} found matching '{query}'."

    if search_type == "options" and query.startswith("services."):
        output_lines = [f"Found {count} options for '{query}':", ""]
    else:
        output_lines = [f"Found {count} {search_type} matching '{query}':", ""]

    for item in sorted_items:
        name = item.get("name", "Unknown")
        version = item.get("version")
        desc = item.get("description")
        item_type = item.get("type")  # For options
        programs = item.get("programs")  # For programs search (within package item)

        line1 = f"- {name}"
        if version:
            line1 += f" ({version})"
        output_lines.append(line1)

        if search_type == "options" and item_type:
            output_lines.append(f"  Type: {item_type}")
        elif search_type == "programs" and programs:
            output_lines.append(f"  Programs: {', '.join(programs)}")

        if desc:
            # Handle simple HTML tags
            if "<" in desc and ">" in desc:  # Basic check for HTML
                desc = _simple_html_to_markdown(desc)

            desc_short = (desc[:250] + "...") if len(desc) > 253 else desc
            output_lines.append(f"  {desc_short}")

        output_lines.append("")

    return "\n".join(output_lines)


def _format_package_info(info: Dict[str, Any]) -> str:
    """Formats detailed package information."""
    output_lines = [f"# {info.get('name', 'Unknown Package')}", ""]

    version = info.get("version", "Not available")
    output_lines.append(f"**Version:** {version}")

    if desc := info.get("description"):
        output_lines.extend(["", f"**Description:** {_simple_html_to_markdown(desc)}"])  # Format desc

    if long_desc := info.get("longDescription"):
        output_lines.extend(["", "**Long Description:**", _simple_html_to_markdown(long_desc)])  # Format long desc

    if homepage := info.get("homepage"):
        output_lines.append("")
        urls = homepage if isinstance(homepage, list) else [homepage]
        if len(urls) == 1:
            output_lines.append(f"**Homepage:** {urls[0]}")
        elif len(urls) > 1:
            output_lines.append("**Homepages:**")
            output_lines.extend([f"- {url}" for url in urls])

    if license_info := info.get("license"):
        license_str = _format_license(license_info)
        output_lines.extend(["", f"**License:** {license_str}"])

    if position := info.get("position"):
        github_url = _create_github_link(position)
        output_lines.extend(["", f"**Source:** [{position}]({github_url})"])

    if maintainers_list := info.get("maintainers"):
        maintainer_names = _format_maintainers(maintainers_list)
        if maintainer_names:
            output_lines.extend(["", f"**Maintainers:** {maintainer_names}"])

    if platforms := info.get("platforms"):
        if isinstance(platforms, list) and platforms:
            output_lines.extend(["", f"**Platforms:** {', '.join(platforms)}"])

    if programs := info.get("programs"):
        if isinstance(programs, list) and programs:
            programs_str = ", ".join(sorted(programs))
            output_lines.extend(["", f"**Provided Programs:** {programs_str}"])

    return "\n".join(output_lines)


def _format_license(license_info: Any) -> str:
    """Formats license information into a string."""
    if isinstance(license_info, list) and license_info:
        if isinstance(license_info[0], dict) and "fullName" in license_info[0]:
            names = [lic.get("fullName", "") for lic in license_info if lic.get("fullName")]
            return ", ".join(filter(None, names))
        else:
            return ", ".join(map(str, license_info))
    elif isinstance(license_info, dict) and "fullName" in license_info:
        return license_info["fullName"]
    elif isinstance(license_info, str):
        return license_info
    return "Unknown"


def _format_maintainers(maintainers_list: Any) -> str:
    """Formats maintainer list into a comma-separated string."""
    names = []
    if isinstance(maintainers_list, list):
        for m in maintainers_list:
            if isinstance(m, dict) and (name := m.get("name")):
                names.append(name)
            elif isinstance(m, str) and m:
                names.append(m)
    return ", ".join(names)


def _create_github_link(position: str) -> str:
    """Creates a GitHub source link from a position string."""
    base_url = "https://github.com/NixOS/nixpkgs/blob/master/"
    if ":" in position:
        file_path, line_num = position.rsplit(":", 1)
        return f"{base_url}{file_path}#L{line_num}"
    else:
        return f"{base_url}{position}"


# Import re only if needed within formatting helpers
import re


def _simple_html_to_markdown(html_content: str) -> str:
    """Converts simple HTML tags in descriptions to Markdown."""
    if not isinstance(html_content, str) or "<" not in html_content:
        return html_content  # No HTML detected, return as is

    desc = html_content
    # Handle links first
    if "<a href" in desc:
        desc = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"[\2](\1)", desc)
        desc = re.sub(r"<a href='([^']+)'>([^<]+)</a>", r"[\2](\1)", desc)

    # Remove container tag if present
    desc = desc.replace("<rendered-html>", "").replace("</rendered-html>", "")

    # Convert common tags
    desc = desc.replace("<p>", "").replace("</p>", "\n\n")
    desc = desc.replace("<code>", "`").replace("</code>", "`")
    desc = desc.replace("<ul>", "\n").replace("</ul>", "\n")
    desc = desc.replace("<ol>", "\n").replace("</ol>", "\n")  # Handle ordered lists
    desc = desc.replace("<li>", "- ").replace("</li>", "\n")
    desc = desc.replace("<strong>", "**").replace("</strong>", "**")  # Bold
    desc = desc.replace("<em>", "*").replace("</em>", "*")  # Italics

    # Remove any remaining tags
    desc = re.sub(r"<[^>]*>", "", desc)

    # Clean up whitespace and normalize line breaks
    lines = [line.strip() for line in desc.split("\n")]
    # Filter out empty lines, then join with double newline for paragraphs
    non_empty_lines = [line for line in lines if line]
    desc = "\n\n".join(non_empty_lines)
    # Ensure single newline between list items if they were joined too aggressively
    desc = desc.replace("\n\n- ", "\n- ")

    return desc.strip()


def _get_service_suggestion(service_name: str, channel: str) -> str:
    """Generates helpful suggestions for a service path."""
    output = "\n## Common Options for Services\n\n"
    output += f"## Common option patterns for '{service_name}' service\n\n"
    output += f"To find options for the '{service_name}' service, try these searches:\n\n"
    output += f"- `services.{service_name}.enable` - Enable the service (boolean)\n"
    output += f"- `services.{service_name}.package` - The package to use for the service\n"
    output += f"- `services.{service_name}.user`/`group` - Service user/group\n"
    output += f"- `services.{service_name}.settings.*` - Configuration settings\n\n"

    output += "Or try a more specific option path like:\n"
    output += f"- `services.{service_name}.port` - Network port configuration\n"
    output += f"- `services.{service_name}.dataDir` - Data directory location\n\n"

    output += "## Example NixOS Configuration\n\n"
    output += "```nix\n"
    output += "# /etc/nixos/configuration.nix\n"
    output += "{ config, pkgs, ... }:\n"
    output += "{\n"
    output += f"  # Enable {service_name} service\n"
    output += f"  services.{service_name} = {{\n"
    output += "    enable = true;\n"
    output += "    # Add other configuration options here\n"
    output += "  };\n"
    output += "}\n"
    output += "```\n"
    output += "\nTry searching for all options with:\n"
    output += f'`nixos_search(query="services.{service_name}", type="options", channel="{channel}")`'
    return output


def _format_option_info(info: Dict[str, Any], channel: str) -> str:
    """Formats detailed option information."""
    name = info.get("name", "Unknown Option")
    output_lines = [f"# {name}", ""]

    if desc := info.get("description"):
        output_lines.extend(["", f"**Description:** {_simple_html_to_markdown(desc)}", ""])  # Format desc

    if opt_type := info.get("type"):
        output_lines.append(f"**Type:** {opt_type}")
    if intro_ver := info.get("introduced_version"):
        output_lines.append(f"**Introduced in:** NixOS {intro_ver}")
    if dep_ver := info.get("deprecated_version"):
        output_lines.append(f"**Deprecated in:** NixOS {dep_ver}")

    default_val = info.get("default", None)
    if default_val is not None:
        default_str = str(default_val)
        if isinstance(default_val, str) and ("\n" in default_val or len(default_val) > 80):
            output_lines.extend(["**Default:**", "```nix", default_str, "```"])
        else:
            output_lines.append(f"**Default:** `{default_str}`")

    if man_url := info.get("manual_url"):
        output_lines.append(f"**Manual:** [{man_url}]({man_url})")

    # Use the 'example' field provided in the option data for the main example block
    if example := info.get("example"):
        output_lines.extend(["", "**Example:**", "```nix", str(example), "```"])

    # Add example in context if nested
    if "." in name:
        parts = name.split(".")
        # Ensure it's a reasonably nested option (e.g., at least service.foo.option)
        if len(parts) > 1:
            leaf_name = parts[-1]
            example_context_lines = [
                "",
                "**Example in context:**",
                "```nix",
                "# /etc/nixos/configuration.nix",
                "{ config, pkgs, ... }:",
                "{",
            ]
            indent = "  "
            structure = []
            # Build the nested structure string
            for i, part in enumerate(parts[:-1]):
                # Add structure line
                line = f"{indent}{part} = " + "{"
                structure.append(line)
                indent += "  "
            example_context_lines.extend(structure)

            # Determine the example value to display based on type and provided 'example'
            option_type = info.get("type", "").lower()
            provided_example = info.get("example")  # Use the actual example from data

            example_value_str = "..."  # Default placeholder

            if option_type == "boolean":
                # Prefer example if it exists and is true, otherwise default to true for example
                example_value_str = "true" if (provided_example == "true" or provided_example is True) else "true"
            elif option_type == "int" or option_type == "integer":
                # Prefer example if numeric, else use placeholder
                try:
                    example_value_str = str(int(provided_example)) if provided_example is not None else "1234"
                except (ValueError, TypeError):
                    example_value_str = "1234"  # Fallback placeholder
            elif option_type == "string":
                # Use example if present, ensuring quotes. Otherwise use placeholder.
                if provided_example and isinstance(provided_example, str):
                    # Check if already quoted in the example field itself
                    if provided_example.startswith('"') and provided_example.endswith('"'):
                        example_value_str = provided_example
                    # Handle common Nix expressions that shouldn't be quoted
                    elif (
                        provided_example.startswith("pkgs.")
                        or "/" in provided_example
                        or provided_example.startswith(".")
                    ):
                        example_value_str = provided_example
                    else:  # Add quotes if needed
                        example_value_str = f'"{provided_example}"'
                else:
                    example_value_str = '"/path/or/value"'  # Generic string placeholder
            else:
                # For other types (lists, attr sets), use the example field directly if present
                example_value_str = str(provided_example) if provided_example is not None else "{ /* ... */ }"

            # Add the line with the leaf name and example value
            example_context_lines.append(f"{indent}{leaf_name} = {example_value_str};")

            # Close the nested structure
            for _ in range(len(parts) - 1):
                indent = indent[:-2]
                example_context_lines.append(f"{indent}" + "};")
            example_context_lines.append("}")  # Close outer block
            example_context_lines.append("```")
            output_lines.extend(example_context_lines)

    # Add related options if this was detected as a service path
    if info.get("is_service_path") and (related := info.get("related_options")):
        service_name = info.get("service_name", "")
        output_lines.extend(["", f"## Related Options for {service_name} Service", ""])

        related_groups = {}
        for opt in related:
            opt_name = opt.get("name", "")
            group = "_other"  # Default group
            if "." in opt_name:
                prefix = f"services.{service_name}."
                if opt_name.startswith(prefix):
                    remainder = opt_name[len(prefix) :]
                    group = remainder.split(".")[0] if "." in remainder else "_direct"
            if group not in related_groups:
                related_groups[group] = []
            related_groups[group].append(opt)

        # Show direct options first
        if "_direct" in related_groups:
            for opt in related_groups["_direct"]:
                line = f"- `{opt.get('name', '')}`"
                if opt_type := opt.get("type"):
                    line += f" ({opt_type})"
                output_lines.append(line)
                if desc := opt.get("description"):
                    output_lines.append(f"  {_simple_html_to_markdown(desc)}")
            del related_groups["_direct"]

        # Then show groups
        for group, opts in sorted(related_groups.items()):
            if group == "_other" or not opts:
                continue
            output_lines.append(f"\n### {group} options ({len(opts)})")
            for i, opt in enumerate(opts[:5]):  # Show first 5
                line = f"- `{opt.get('name', '')}`"
                if opt_type := opt.get("type"):
                    line += f" ({opt_type})"
                output_lines.append(line)
            if len(opts) > 5:
                output_lines.append(f"- ...and {len(opts) - 5} more")

        # Add full service example suggestion at the end of related options
        output_lines.append(_get_service_suggestion(service_name, channel))

    return "\n".join(output_lines)


# --- Main Tool Functions ---


def nixos_search(
    query: str, type: str = "packages", limit: int = 20, channel: str = CHANNEL_UNSTABLE, context=None
) -> str:
    """Search for NixOS packages, options, or programs.

    Args:
        query: The search term
        type: The type to search (packages, options, or programs)
        limit: Maximum number of results to return (default: 20)
        channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)
        context: Optional context object (used internally)

    Returns:
        Formatted search results as text
    """
    logger.info(f"Searching NixOS '{channel}' for {type} matching '{query}' (limit {limit})")
    search_type = type.lower()
    valid_types = ["packages", "options", "programs"]
    if search_type not in valid_types:
        return f"Error: Invalid type '{type}'. Must be one of: {', '.join(valid_types)}"

    try:
        ctx = _setup_context_and_channel(context, channel)
        if ctx is None:
            return "Error: NixOS context not available"

        search_query = query
        search_args = {"limit": limit, "channel": channel}
        multi_word_info = {}

        if search_type == "options":
            multi_word_info = parse_multi_word_query(query)
            search_query = multi_word_info["main_path"] or query
            search_args["additional_terms"] = multi_word_info["terms"]
            search_args["quoted_terms"] = multi_word_info["quoted_terms"]
            logger.info(
                f"Options search: path='{search_query}', terms={search_args['additional_terms']}, "
                f"quoted={search_args['quoted_terms']}"
            )
        # Wildcard logic removed - handled by ElasticsearchClient query builders

        # Perform the search
        if search_type == "packages":
            results = ctx.search_packages(search_query, **search_args)
        elif search_type == "options":
            results = ctx.search_options(search_query, **search_args)
        else:  # programs
            results = ctx.search_programs(search_query, **search_args)

        # Check for errors from the context methods
        if error_msg := results.get("error"):
            logger.error(f"Error during {search_type} search for '{query}': {error_msg}")
            # Return a user-friendly error, maybe include suggestions if applicable
            check_path = multi_word_info.get("main_path") or query
            if search_type == "options" and check_path.startswith("services."):
                parts = check_path.split(".", 2)
                if len(parts) > 1 and (service_name := parts[1]):
                    return f"Error searching options for '{query}': {error_msg}\n" + _get_service_suggestion(
                        service_name, channel
                    )
            return f"Error searching {search_type} for '{query}': {error_msg}"

        # Format results
        output = _format_search_results(results, query, search_type)  # Pass original query

        # Add service suggestions if no results found for a service path
        items_key = "options" if search_type == "options" else "packages"
        if not results.get(items_key):
            check_path = multi_word_info.get("main_path") or query
            if search_type == "options" and check_path.startswith("services."):
                parts = check_path.split(".", 2)
                if len(parts) > 1 and (service_name := parts[1]):
                    # Append suggestions only if output indicates no results
                    if f"No options found for '{query}'" in output:
                        output += _get_service_suggestion(service_name, channel)

        return output

    except Exception as e:
        logger.error(f"Error in nixos_search (query='{query}', type='{type}'): {e}", exc_info=True)
        return f"Error performing search: {str(e)}"


def nixos_info(name: str, type: str = "package", channel: str = CHANNEL_UNSTABLE, context=None) -> str:
    """Get detailed information about a NixOS package or option.

    Args:
        name: The name of the package or option
        type: Either "package" or "option"
        channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)
        context: Optional context object (used internally)

    Returns:
        Detailed information about the package or option
    """
    logger.info(f"Getting NixOS '{channel}' {type} info for: {name}")
    info_type = type.lower()
    if info_type not in ["package", "option"]:
        return "Error: 'type' must be 'package' or 'option'"

    try:
        ctx = _setup_context_and_channel(context, channel)
        if ctx is None:
            return "Error: NixOS context not available"

        if info_type == "package":
            info = ctx.get_package(name, channel=channel)
            if not info.get("found", False):
                return (
                    f"Package '{name}' not found in channel '{channel}'. Error: {info.get('error', 'Unknown reason')}"
                )
            return _format_package_info(info)
        else:  # option
            info = ctx.get_option(name, channel=channel)
            if not info.get("found", False):
                # Handle service path suggestions for not found options
                if info.get("is_service_path"):
                    service_name = info.get("service_name", "")
                    prefix_msg = f"# Option '{name}' not found"
                    suggestion = _get_service_suggestion(service_name, channel)
                    return f"{prefix_msg}\n{suggestion}"
                else:
                    return (
                        f"Option '{name}' not found in channel '{channel}'. "
                        f"Error: {info.get('error', 'Unknown reason')}"
                    )
            return _format_option_info(info, channel)

    except Exception as e:
        logger.error(f"Error in nixos_info (name='{name}', type='{type}'): {e}", exc_info=True)
        return f"Error retrieving information: {str(e)}"


def nixos_stats(channel: str = CHANNEL_UNSTABLE, context=None) -> str:
    """Get statistics about available NixOS packages and options.

    Args:
        channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)
        context: Optional context object (used internally)

    Returns:
        Statistics about packages and options
    """
    logger.info(f"Getting NixOS statistics for channel '{channel}'")

    try:
        ctx = _setup_context_and_channel(context, channel)
        if ctx is None:
            return "Error: NixOS context not available"

        package_stats = ctx.get_package_stats(channel=channel)
        options_stats = ctx.count_options(channel=channel)

        pkg_err = package_stats.get("error")
        opt_err = options_stats.get("error")
        if pkg_err or opt_err:
            logger.error(f"Error getting stats. Packages: {pkg_err or 'OK'}, Options: {opt_err or 'OK'}")
            return f"Error retrieving statistics (Packages: {pkg_err or 'OK'}, Options: {opt_err or 'OK'})"

        options_count = options_stats.get("count", 0)
        aggregations = package_stats.get("aggregations", {})

        if not aggregations and options_count == 0:
            return f"No statistics available for channel '{channel}'."

        output_lines = [f"# NixOS Statistics (Channel: {channel})", ""]
        output_lines.append(f"Total options: {options_count:,}")
        output_lines.extend(["", "## Package Statistics", ""])

        # Helper to format aggregation buckets
        def format_buckets(
            title: str, buckets: Optional[List[Dict]], key_name: str = "key", count_name: str = "doc_count"
        ) -> List[str]:
            lines = []
            if buckets:
                lines.append(f"### {title}")
                # Wrap long lines if necessary
                lines.extend([f"- {b.get(key_name, 'Unknown')}: {b.get(count_name, 0):,} packages" for b in buckets])
                lines.append("")
            return lines

        output_lines.extend(format_buckets("Distribution by Channel", aggregations.get("channels", {}).get("buckets")))
        output_lines.extend(format_buckets("Top 10 Licenses", aggregations.get("licenses", {}).get("buckets")))
        output_lines.extend(format_buckets("Top 10 Platforms", aggregations.get("platforms", {}).get("buckets")))

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Error getting NixOS statistics: {e}", exc_info=True)
        return f"Error retrieving statistics: {str(e)}"


def check_request_ready(ctx) -> bool:
    """Check if the server is ready to handle requests.

    Args:
        ctx: The request context or context string from MCP

    Returns:
        True if ready, False if not
    """
    # Handle case where ctx is a string (from MCP tool interface)
    if isinstance(ctx, str):
        return True  # Always ready when called from MCP outside server

    # Handle case where ctx is a request context (from our server)
    if hasattr(ctx, "request_context"):
        return ctx.request_context.lifespan_context.get("is_ready", False)

    # Default to ready if we can't determine
    logger.warning("Unknown context type, assuming ready")
    return True


def register_nixos_tools(mcp) -> None:
    """Register all NixOS tools with the MCP server."""
    logger.info("Registering NixOS MCP tools...")

    @mcp.tool()
    async def nixos_search(ctx, query: str, type: str = "packages", limit: int = 20, channel: str = "unstable") -> str:
        """Search for NixOS packages, options, or programs.

        Args:
            query: The search term
            type: The type to search (packages, options, or programs)
            limit: Maximum number of results to return (default: 20)
            channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)

        Returns:
            Results formatted as text
        """
        logger.info(f"NixOS search request: query='{query}', type='{type}', limit={limit}, channel='{channel}'")

        # Check if the server is ready for requests
        if not check_request_ready(ctx):
            error_msg = "The server is still initializing. Please try again in a few seconds."
            logger.warning(f"Request blocked - server not ready: {error_msg}")
            return error_msg

        # Get context
        try:
            # Import get_nixos_context dynamically to avoid circular imports
            from mcp_nixos.server import get_nixos_context

            nixos_context = get_nixos_context()

            # Validate channel input
            valid_channels = get_valid_channels()
            if channel.lower() not in valid_channels:
                error_msg = f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}"
                logger.error(error_msg)
                return error_msg

            # Call the undecorated function directly
            from mcp_nixos.tools.nixos_tools import nixos_search as search_func

            result = search_func(query, type, limit, channel, nixos_context)
            return result
        except Exception as e:
            error_msg = f"Error during NixOS search: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def nixos_info(ctx, name: str, type: str = "package", channel: str = "unstable") -> str:
        """Get detailed information about a NixOS package or option.

        Args:
            name: The name of the package or option
            type: Either "package" or "option"
            channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)

        Returns:
            Detailed information about the package or option
        """
        logger.info(f"NixOS info request: name='{name}', type='{type}', channel='{channel}'")

        # Check if the server is ready for requests
        if not check_request_ready(ctx):
            error_msg = "The server is still initializing. Please try again in a few seconds."
            logger.warning(f"Request blocked - server not ready: {error_msg}")
            return error_msg

        # Get context
        try:
            # Import get_nixos_context dynamically to avoid circular imports
            from mcp_nixos.server import get_nixos_context

            nixos_context = get_nixos_context()

            # Validate channel input
            valid_channels = get_valid_channels()
            if channel.lower() not in valid_channels:
                error_msg = f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}"
                logger.error(error_msg)
                return error_msg

            # Call the undecorated function directly
            from mcp_nixos.tools.nixos_tools import nixos_info as info_func

            result = info_func(name, type, channel, nixos_context)
            return result
        except Exception as e:
            error_msg = f"Error during NixOS info: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def nixos_stats(ctx, channel: str = "unstable") -> str:
        """Get statistics about available NixOS packages and options.

        Args:
            channel: NixOS channel to use (default: unstable, options: unstable, 24.11, 25.05, beta, stable)

        Returns:
            Statistics about packages and options
        """
        logger.info(f"NixOS stats request: channel='{channel}'")

        # Check if the server is ready for requests
        if not check_request_ready(ctx):
            error_msg = "The server is still initializing. Please try again in a few seconds."
            logger.warning(f"Request blocked - server not ready: {error_msg}")
            return error_msg

        # Get context
        try:
            # Import get_nixos_context dynamically to avoid circular imports
            from mcp_nixos.server import get_nixos_context

            nixos_context = get_nixos_context()

            # Validate channel input
            valid_channels = get_valid_channels()
            if channel.lower() not in valid_channels:
                error_msg = f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}"
                logger.error(error_msg)
                return error_msg

            # Call the undecorated function directly
            from mcp_nixos.tools.nixos_tools import nixos_stats as stats_func

            result = stats_func(channel, nixos_context)
            return result
        except Exception as e:
            error_msg = f"Error during NixOS stats: {str(e)}"
            logger.error(error_msg)
            return error_msg

    logger.info("NixOS MCP tools registered with request gating.")
