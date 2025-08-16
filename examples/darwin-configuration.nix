# Example nix-darwin configuration with MCP-NixOS for macOS
# Add this to your darwin-configuration.nix or create a separate module

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

  # Configure Claude Desktop for all users
  # Note: Adjust path based on where Claude Desktop stores config on macOS
  environment.etc."claude/claude_desktop_config.json" = {
    text = builtins.toJSON {
      mcpServers = {
        nixos = {
          command = "${mcp-nixos}/bin/mcp-nixos";
          args = [];
        };
      };
    };
  };

  # Create launchd service for MCP-NixOS (macOS equivalent of systemd)
  launchd.user.agents.mcp-nixos = {
    command = "${mcp-nixos}/bin/mcp-nixos";
    
    serviceConfig = {
      Label = "org.nixos.mcp-nixos";
      RunAtLoad = false; # Don't start automatically
      KeepAlive = false; # Don't restart if it crashes
      StandardErrorPath = "/tmp/mcp-nixos.err";
      StandardOutPath = "/tmp/mcp-nixos.out";
    };
  };

  # Add shell aliases for convenience
  programs.bash.interactiveShellInit = ''
    alias mcp-nixos-test='${mcp-nixos}/bin/mcp-nixos'
  '';
  
  programs.zsh.interactiveShellInit = ''
    alias mcp-nixos-test='${mcp-nixos}/bin/mcp-nixos'
  '';

  # Optional: Configure for Cursor on macOS
  # This assumes Cursor config is in the user's home directory
  system.activationScripts.postUserActivation.text = ''
    # Create Cursor MCP config for all users
    for user_home in /Users/*; do
      if [ -d "$user_home" ]; then
        cursor_config_dir="$user_home/.cursor"
        if [ ! -d "$cursor_config_dir" ]; then
          mkdir -p "$cursor_config_dir"
        fi
        
        cat > "$cursor_config_dir/mcp.json" <<EOF
    {
      "mcpServers": {
        "nixos": {
          "command": "${mcp-nixos}/bin/mcp-nixos",
          "args": []
        }
      }
    }
    EOF
      fi
    done
  '';

  # Set environment variable for easy reference
  environment.variables = {
    MCP_NIXOS_PATH = "${mcp-nixos}/bin/mcp-nixos";
  };
}