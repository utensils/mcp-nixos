"use client";

import Link from 'next/link';
import FeatureCard from '@/components/FeatureCard';
import CodeBlock from '@/components/CodeBlock';
import AnchorHeading from '@/components/AnchorHeading';

export default function Home() {
  const scrollToSection = (elementId: string) => {
    const element = document.getElementById(elementId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-nix-primary to-nix-dark text-white py-20 shadow-lg">
        <div className="container-custom text-center">
          <h1 className="text-4xl md:text-6xl font-bold mb-6">MCP-NixOS</h1>
          <div className="mb-4">
            <span className="inline-block bg-nix-secondary text-white px-4 py-2 rounded-full text-sm font-semibold">
              🎉 v1.0.0 - The Great Simplification
            </span>
          </div>
          <div className="mb-8 max-w-3xl mx-auto">
            <p className="text-xl md:text-2xl font-medium mb-2">
              <span className="font-bold tracking-wide">Model Context Protocol</span>
            </p>
            <div className="flex flex-wrap justify-center items-center gap-3 md:gap-4 py-2">
              <a 
                href="https://nixos.org/manual/nixos/stable/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="px-4 py-1 bg-white/10 backdrop-blur-sm rounded-full border border-white/20 shadow-lg font-semibold text-nix-secondary flex items-center hover:bg-white/20 transition-colors duration-200"
              >
                <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 4L20 8V16L12 20L4 16V8L12 4Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                NixOS
              </a>
              <a 
                href="https://nix-community.github.io/home-manager/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="px-4 py-1 bg-white/10 backdrop-blur-sm rounded-full border border-white/20 shadow-lg font-semibold text-nix-secondary flex items-center hover:bg-white/20 transition-colors duration-200"
              >
                <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Home Manager
              </a>
              <a 
                href="https://daiderd.com/nix-darwin/" 
                target="_blank" 
                rel="noopener noreferrer" 
                className="px-4 py-1 bg-white/10 backdrop-blur-sm rounded-full border border-white/20 shadow-lg font-semibold text-nix-secondary flex items-center hover:bg-white/20 transition-colors duration-200"
              >
                <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 3C16.9706 3 21 7.02944 21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M12 8L12 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 12L16 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                nix-darwin
              </a>
            </div>
          </div>
          <div className="flex flex-col md:flex-row gap-4 justify-center">
            <button 
              onClick={() => scrollToSection('getting-started')} 
              className="btn-primary bg-white text-nix-primary hover:bg-nix-light"
            >
              Get Started
            </button>
            <Link href="https://github.com/utensils/mcp-nixos" className="btn-secondary bg-transparent text-white border-white hover:bg-white/10">
              GitHub
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="container-custom">
          <AnchorHeading level={2} className="text-3xl font-bold text-center mb-12 text-nix-dark">Key Features</AnchorHeading>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard 
              title="NixOS Packages & Options" 
              description="Search and retrieve detailed information about NixOS packages and system options."
              iconName="package"
            />
            <FeatureCard 
              title="Home Manager Integration" 
              description="Comprehensive support for Home Manager configuration options and hierarchical searches."
              iconName="home"
            />
            <FeatureCard 
              title="nix-darwin Support" 
              description="Access to nix-darwin macOS configuration options and resources."
              iconName="apple"
            />
            <FeatureCard 
              title="Fast & Stateless" 
              description="Direct API calls with no caching complexity. Simple, reliable, and maintainable."
              iconName="bolt"
            />
            <FeatureCard 
              title="Cross-Platform" 
              description="Works seamlessly across Linux, macOS, and Windows environments."
              iconName="globe"
            />
            <FeatureCard 
              title="Claude Integration" 
              description="Perfect compatibility with Claude and other AI assistants via the MCP protocol."
              iconName="robot"
            />
            <FeatureCard 
              title="Version History" 
              description="Package version tracking with nixpkgs commit hashes via NixHub.io integration."
              iconName="history"
            />
            <FeatureCard 
              title="Plain Text Output" 
              description="Human-readable responses with no XML parsing needed. Just clear, formatted text."
              iconName="document"
            />
          </div>
        </div>
      </section>

      {/* Getting Started Section */}
      <section id="getting-started" className="py-16 bg-nix-light">
        <div className="container-custom">
          <AnchorHeading level={2} className="text-3xl font-bold text-center mb-12 text-nix-dark">Getting Started</AnchorHeading>
          <div className="max-w-2xl mx-auto">
            <AnchorHeading level={3} className="text-2xl font-bold mb-4 text-nix-primary">Configuration</AnchorHeading>
            <p className="mb-6 text-gray-800 font-medium">
              Add to your MCP configuration file:
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
            <p className="mt-6 text-gray-800 font-medium">
              Start leveraging NixOS package information and configuration options in your workflow! For additional configuration options, see the <Link href="/docs#configuration" className="text-nix-primary hover:text-nix-dark underline transition-colors">configuration documentation</Link>.
            </p>
            <div className="text-center mt-12">
              <Link href="/docs" className="btn-primary">
                View Full Documentation
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}