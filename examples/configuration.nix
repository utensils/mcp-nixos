# Example NixOS system configuration with MCP-NixOS
# Add this to your /etc/nixos/configuration.nix or create a separate module

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
  # Add MCP-NixOS to system-wide packages
  environment.systemPackages = with pkgs; [
    mcp-nixos
    # Other packages...
  ];

  # Optional: Configure MCP-NixOS for all users
  # This creates a system-wide configuration file
  environment.etc."claude/claude_desktop_config.json" = {
    text = builtins.toJSON {
      mcpServers = {
        nixos = {
          command = "${mcp-nixos}/bin/mcp-nixos";
          args = [];
        };
      };
    };
    # Make it readable by all users
    mode = "0644";
  };

  # Optional: Create a systemd service to run MCP-NixOS as a system daemon
  # (Only useful if your MCP client supports network connections)
  systemd.services.mcp-nixos = {
    description = "MCP-NixOS Server";
    after = [ "network.target" ];
    wantedBy = [ "multi-user.target" ];
    
    serviceConfig = {
      Type = "simple";
      ExecStart = "${mcp-nixos}/bin/mcp-nixos";
      Restart = "on-failure";
      RestartSec = 5;
      # Run as a non-privileged user
      User = "nobody";
      Group = "nogroup";
      # Security hardening
      PrivateTmp = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      NoNewPrivileges = true;
    };
    
    # Disable by default - users can enable if needed
    enable = false;
  };

  # Optional: Create a shell alias for all users
  programs.bash.shellAliases = {
    mcp-nixos-test = "${mcp-nixos}/bin/mcp-nixos";
  };

  # Optional: Add to the system path
  environment.variables = {
    MCP_NIXOS_PATH = "${mcp-nixos}/bin/mcp-nixos";
  };
}