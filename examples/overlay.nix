# Example Nix overlay for MCP-NixOS
# Save this as ~/.config/nixpkgs/overlays/mcp-nixos.nix
# or include it in your overlays list

self: super: {
  mcp-nixos = super.callPackage (super.fetchFromGitHub {
    owner = "utensils";
    repo = "mcp-nixos";
    rev = "main"; # Pin to a specific commit for reproducibility
    # To get the correct sha256:
    # nix-prefetch-github utensils mcp-nixos
    sha256 = "0000000000000000000000000000000000000000000000000000"; # Replace with actual sha256
  } + "/default.nix") { };
}

# After adding this overlay, you can use mcp-nixos in any Nix expression:
#
# With Home Manager:
#   home.packages = [ pkgs.mcp-nixos ];
#
# With NixOS:
#   environment.systemPackages = [ pkgs.mcp-nixos ];
#
# With nix-darwin:
#   environment.systemPackages = [ pkgs.mcp-nixos ];
#
# In a shell:
#   nix-shell -p mcp-nixos
#
# Or directly:
#   nix run nixpkgs#mcp-nixos