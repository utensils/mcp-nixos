import CodeBlock from '@/components/CodeBlock';

export default function UsagePage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8 text-nix-dark">Usage</h1>

        <div className="prose prose-lg max-w-none">
          <div className="bg-gradient-to-br from-nix-light to-white p-6 rounded-lg shadow-sm mb-8">
            <p className="text-gray-800 mb-6 leading-relaxed text-xl">
              Pick your poison. We&apos;ve got three ways to run this thing.
              They all do the same thing, so just choose based on what tools you already have installed.
              Or be a rebel and try all three. We don&apos;t judge.
            </p>

            <p className="text-gray-700 mb-4 font-semibold">
              🚨 <strong>No Nix/NixOS Required!</strong> This tool works on any system - Windows, macOS, Linux. You&apos;re just querying web APIs. Yes, even you, Windows users.
            </p>
          </div>

          <div className="space-y-8">
            {/* Option 1 */}
            <div className="bg-white rounded-lg shadow-md border-l-4 border-nix-primary p-6">
              <h2 className="text-2xl font-bold text-nix-dark mb-4">
                Option 1: Using uvx (Recommended for most humans)
              </h2>
              <p className="text-gray-700 mb-4">
                The civilized approach. If you&apos;ve got Python and can install things like a normal person, this is for you.
              </p>
              <CodeBlock
                code={`{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"]
    }
  }
}`}
                language="json"
              />
              <p className="text-sm text-gray-600 mt-3">
                Pro tip: This installs nothing permanently. It&apos;s like a one-night stand with software.
              </p>
            </div>

            {/* Option 2 */}
            <div className="bg-white rounded-lg shadow-md border-l-4 border-nix-secondary p-6">
              <h2 className="text-2xl font-bold text-nix-dark mb-4">
                Option 2: Using Nix (For the enlightened)
              </h2>
              <p className="text-gray-700 mb-4">
                You&apos;re already using Nix, so you probably think you&apos;re better than everyone else.
                And you know what? You might be right.
              </p>
              <CodeBlock
                code={`{
  "mcpServers": {
    "nixos": {
      "command": "nix",
      "args": ["run", "github:utensils/mcp-nixos", "--"]
    }
  }
}`}
                language="json"
              />
              <p className="text-sm text-gray-600 mt-3">
                Bonus: This method makes you feel superior at developer meetups.
              </p>
            </div>

            {/* Option 2b - Declarative */}
            <div className="bg-white rounded-lg shadow-md border-l-4 border-nix-secondary p-6">
              <h2 className="text-2xl font-bold text-nix-dark mb-4">
                Option 2b: Declarative Nix (The true Nix way)
              </h2>
              <p className="text-gray-700 mb-4">
                mcp-nixos is in <a href="https://search.nixos.org/packages?channel=unstable&show=mcp-nixos&query=mcp-nixos" target="_blank" rel="noopener noreferrer" className="text-nix-primary hover:underline font-semibold">nixpkgs</a>.
                Add it to your config like everything else you&apos;ve spent 400 hours perfecting.
              </p>
              <CodeBlock
                code={`# NixOS (configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];

# Home Manager (home.nix)
home.packages = [ pkgs.mcp-nixos ];

# nix-darwin (darwin-configuration.nix)
environment.systemPackages = [ pkgs.mcp-nixos ];`}
                language="nix"
              />
              <p className="text-gray-700 mt-4 mb-2">
                Or use the flake directly with the overlay:
              </p>
              <CodeBlock
                code={`# flake.nix
{
  inputs.mcp-nixos.url = "github:utensils/mcp-nixos";

  outputs = { nixpkgs, mcp-nixos, ... }: {
    nixpkgs.overlays = [ mcp-nixos.overlays.default ];
    # Then use pkgs.mcp-nixos anywhere
  };
}`}
                language="nix"
              />
              <p className="text-sm text-gray-600 mt-3">
                Finally, a package that fits into your 3000-line flake.nix without drama.
              </p>
            </div>

            {/* Option 3 */}
            <div className="bg-white rounded-lg shadow-md border-l-4 border-nix-primary p-6">
              <h2 className="text-2xl font-bold text-nix-dark mb-4">
                Option 3: Using Docker (Container enthusiasts unite)
              </h2>
              <p className="text-gray-700 mb-4">
                Because why install software directly when you can wrap it in 17 layers of abstraction?
                At least it&apos;s reproducible... probably.
              </p>
              <CodeBlock
                code={`{
  "mcpServers": {
    "nixos": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/utensils/mcp-nixos"]
    }
  }
}`}
                language="json"
              />
              <p className="text-sm text-gray-600 mt-3">
                Warning: May consume 500MB of disk space for a 10MB Python script. But hey, it&apos;s &quot;isolated&quot;!
              </p>
            </div>
          </div>

          <div className="bg-nix-light bg-opacity-30 p-6 rounded-lg mt-12">
            <h2 className="text-2xl font-bold text-nix-dark mb-4">What Happens Next?</h2>
            <p className="text-gray-700 mb-4">
              Once you&apos;ve picked your configuration method and added it to your MCP client:
            </p>
            <ul className="list-disc list-inside text-gray-700 space-y-2">
              <li>Your AI assistant stops making up NixOS package names</li>
              <li>You get actual, real-time information about 130K+ packages</li>
              <li>Configuration options that actually exist (shocking, we know)</li>
              <li>Version history that helps you find that one specific Ruby version from 2019</li>
            </ul>
            <p className="text-gray-700 mt-4 italic">
              That&apos;s it. No complex setup. No 47-step installation guide. No sacrificing a USB stick to the Nix gods.
              Just paste, reload, and enjoy an AI that actually knows what it&apos;s talking about.
            </p>
          </div>

          <div className="text-center mt-12">
            <p className="text-xl text-gray-700 font-semibold">
              Still confused? Good news: that&apos;s what the AI is for. Just ask it.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
