# Example flake.nix for using MCP-NixOS declaratively
# Copy this to your system configuration and adjust as needed

{
  description = "Example system configuration with MCP-NixOS";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    
    # Add MCP-NixOS as an input
    mcp-nixos = {
      url = "github:utensils/mcp-nixos";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    
    # Optional: Add Home Manager if you use it
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    
    # Optional: Add nix-darwin for macOS
    darwin = {
      url = "github:LnL7/nix-darwin";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, mcp-nixos, home-manager, darwin, ... }@inputs: {
    
    # Example NixOS system configuration
    nixosConfigurations = {
      my-nixos-system = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./hardware-configuration.nix
          ./configuration.nix
          
          # Add MCP-NixOS to system packages
          ({ pkgs, ... }: {
            environment.systemPackages = [
              mcp-nixos.packages.${pkgs.system}.default
            ];
          })
        ];
      };
    };
    
    # Example Home Manager configuration
    homeConfigurations = {
      "myuser@hostname" = home-manager.lib.homeManagerConfiguration {
        pkgs = nixpkgs.legacyPackages.x86_64-linux;
        
        modules = [
          ./home.nix
          
          # Add MCP-NixOS to user packages
          ({ pkgs, ... }: {
            home.packages = [
              mcp-nixos.packages.${pkgs.system}.default
            ];
            
            # Optional: Configure MCP client settings
            home.file.".config/claude/claude_desktop_config.json".text = ''
              {
                "mcpServers": {
                  "nixos": {
                    "command": "${mcp-nixos.packages.${pkgs.system}.default}/bin/mcp-nixos"
                  }
                }
              }
            '';
          })
        ];
      };
    };
    
    # Example nix-darwin (macOS) configuration
    darwinConfigurations = {
      "my-mac" = darwin.lib.darwinSystem {
        system = "aarch64-darwin"; # or "x86_64-darwin" for Intel Macs
        
        modules = [
          ./darwin-configuration.nix
          
          # Add MCP-NixOS to system packages
          ({ pkgs, ... }: {
            environment.systemPackages = [
              mcp-nixos.packages.${pkgs.system}.default
            ];
            
            # Optional: Configure for all users
            environment.etc."claude/claude_desktop_config.json".text = ''
              {
                "mcpServers": {
                  "nixos": {
                    "command": "${mcp-nixos.packages.${pkgs.system}.default}/bin/mcp-nixos"
                  }
                }
              }
            '';
          })
        ];
      };
    };
    
    # Development shell with MCP-NixOS available
    devShells = nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        default = pkgs.mkShell {
          buildInputs = [
            mcp-nixos.packages.${system}.default
          ];
          
          shellHook = ''
            echo "MCP-NixOS is available in this shell"
            echo "Run 'mcp-nixos' to start the server"
          '';
        };
      }
    );
  };
}