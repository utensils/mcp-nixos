# MCP-NixOS: v0.5.0 Release Notes

## Overview

MCP-NixOS v0.5.0 introduces support for the NixOS 25.05 Beta channel, enhancing the flexibility and forward compatibility of the tool. This release adds the ability to search and query packages and options from the upcoming NixOS 25.05 release while maintaining backward compatibility with existing channels.

## Changes in v0.5.0

### 🚀 Major Enhancements

- **NixOS 25.05 Beta Channel Support**: Added support for the upcoming NixOS 25.05 release
- **New "beta" Alias**: Added a "beta" alias that maps to the current beta channel (currently 25.05)
- **Comprehensive Channel Documentation**: Updated all docstrings to include information about the new beta channel
- **Enhanced Testing**: Added extensive tests to ensure proper channel functionality

### 🛠️ Implementation Details

- **Channel Validation**: Extended channel validation to include the new 25.05 Beta channel
- **Cache Management**: Ensured cache clearing behavior works correctly with the new channel
- **Alias Handling**: Implemented proper handling of the "beta" alias similar to the "stable" alias
- **Testing**: Comprehensive test suite to verify all aspects of channel switching and alias resolution

## Technical Details

The release implements the following key improvements:

1. **25.05 Beta Channel**: Added the Elasticsearch index mapping for the upcoming NixOS 25.05 release using the index name pattern `latest-42-nixos-25.05`

2. **Beta Alias**: Implemented a "beta" alias that will always point to the current beta channel, similar to how the "stable" alias points to the current stable release

3. **Extended Documentation**: Updated all function and parameter docstrings to include the new channel options, ensuring users know about the full range of available channels

4. **Future-Proofing**: Designed the implementation to make it easy to add new channels in the future when new NixOS releases are in development

## Installation

```bash
# Install with pip
pip install mcp-nixos==0.5.0

# Install with uv
uv pip install mcp-nixos==0.5.0

# Install with uvx
uvx mcp-nixos==0.5.0
```

## Usage

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

### Available Channels

The following channels are now available for all NixOS tools:

- `unstable` - The NixOS unstable development branch
- `25.05` - The NixOS 25.05 Beta release (upcoming)
- `beta` - Alias for the current beta channel (currently 25.05)
- `24.11` - The current stable NixOS release
- `stable` - Alias for the current stable release (currently 24.11)

Example usage:
```python
# Search packages in the beta channel
nixos_search(query="nginx", channel="beta")

# Get information about a package in the 25.05 channel
nixos_info(name="python3", type="package", channel="25.05")
```

## Contributors

- James Brink (@utensils)
- Sean Callan (Moral Support)