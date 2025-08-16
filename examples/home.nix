# Example Home Manager configuration with MCP-NixOS
# Add this to your home.nix or create a separate module

{ config, pkgs, lib, ... }:

let
  # For non-flake users: fetch MCP-NixOS from GitHub
  mcp-nixos-src = pkgs.fetchFromGitHub {
    owner = "utensils";
    repo = "mcp-nixos";
    rev = "main"; # Pin to a specific commit for reproducibility
    # To get the correct sha256:
    # nix-prefetch-github utensils mcp-nixos
    sha256 = lib.fakeSha256; # Replace with actual sha256
  };
  
  # Build the package
  mcp-nixos = pkgs.callPackage "${mcp-nixos-src}/default.nix" { };
in
{
  # Add MCP-NixOS to user packages
  home.packages = [
    mcp-nixos
  ];

  # Configure Claude Desktop to use MCP-NixOS
  # Adjust the path based on your Claude installation
  home.file.".config/claude/claude_desktop_config.json" = {
    text = builtins.toJSON {
      mcpServers = {
        nixos = {
          command = "${mcp-nixos}/bin/mcp-nixos";
          args = [];
        };
      };
    };
  };

  # Alternative: For Cursor users
  home.file.".cursor/mcp.json" = {
    text = builtins.toJSON {
      mcpServers = {
        nixos = {
          command = "${mcp-nixos}/bin/mcp-nixos";
          args = [];
        };
      };
    };
  };

  # Optional: Create a shell alias for quick access
  programs.bash.shellAliases = {
    mcp-nixos-test = "${mcp-nixos}/bin/mcp-nixos";
  };
  
  programs.zsh.shellAliases = {
    mcp-nixos-test = "${mcp-nixos}/bin/mcp-nixos";
  };

  # Optional: Create a systemd user service to run MCP-NixOS as a daemon
  # (Only useful if your MCP client supports network connections)
  systemd.user.services.mcp-nixos = {
    Unit = {
      Description = "MCP-NixOS Server";
      After = [ "network.target" ];
    };
    Service = {
      Type = "simple";
      ExecStart = "${mcp-nixos}/bin/mcp-nixos";
      Restart = "on-failure";
      RestartSec = 5;
      # Uncomment if you want it to start automatically
      # WantedBy = [ "default.target" ];
    };
  };
}