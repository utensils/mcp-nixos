
import Image from 'next/image';
import AnchorHeading from '@/components/AnchorHeading';

export default function AboutPage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <AnchorHeading level={1} className="text-4xl font-bold mb-8 text-nix-dark">About MCP-NixOS</AnchorHeading>

        <div className="prose prose-lg max-w-none">
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Project Overview</AnchorHeading>

            <div className="mb-6 bg-gradient-to-br from-nix-light to-white rounded-lg shadow-md overflow-hidden border border-nix-light">
              <div className="p-5 flex flex-col sm:flex-row items-center sm:items-start gap-4">
                <div className="flex-shrink-0 bg-white p-3 rounded-lg shadow-sm border border-nix-light/30">
                  <Image
                    src="/images/utensils-logo.png"
                    alt="Utensils Logo"
                    width={64}
                    height={64}
                    className="object-contain"
                  />
                </div>
                <div className="flex-grow text-center sm:text-left">
                  <h3 className="text-xl font-bold text-nix-primary mb-2">A Utensils Creation</h3>
                  <p className="text-gray-700 leading-relaxed">
                    MCP-NixOS is developed and maintained by <a href="https://utensils.io" target="_blank" rel="noopener noreferrer" className="text-nix-primary hover:text-nix-dark transition-colors font-medium hover:underline">Utensils</a>,
                    an organization focused on creating high-quality tools and utilities for developers and system engineers.
                  </p>
                </div>
              </div>
            </div>

            <p className="mb-6 text-gray-800">
              MCP-NixOS is a Model Context Protocol server that provides accurate information about NixOS packages and configuration options.
              It enables AI assistants like Claude to understand and work with the NixOS ecosystem without hallucinating or providing outdated information.
            </p>

            <p className="mb-6 text-gray-800">
              It provides real-time access to:
            </p>
            <ul className="grid gap-3 mb-6">
              {[
                'NixOS packages with accurate metadata',
                'System configuration options',
                'Home Manager settings for user-level configuration',
                'nix-darwin macOS configuration options'
              ].map((item, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span className="text-gray-800">{item}</span>
                </li>
              ))}
            </ul>
            <p className="mb-6 text-gray-800">
              Communication uses JSON-based messages over standard I/O, making it compatible with
              various AI assistants and applications. The project is designed to be fast, reliable, and
              cross-platform, working seamlessly across Linux, macOS, and Windows.
            </p>


          </section>



          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Core Components</AnchorHeading>
            <ul className="grid gap-3 mb-6">
              {[
                { name: 'Cache', description: 'In-memory and filesystem HTML caching with TTL-based expiration' },
                { name: 'Clients', description: 'Elasticsearch API and HTML documentation parsers' },
                { name: 'Contexts', description: 'Application state management for each platform' },
                { name: 'Resources', description: 'MCP resource definitions using URL schemes' },
                { name: 'Tools', description: 'Search, info, and statistics tools with multiple channel support' },
                { name: 'Utils', description: 'Cross-platform helpers and cache management' },
                { name: 'Server', description: 'FastMCP server implementation' },
                { name: 'Pre-Cache', description: 'Command-line option to populate cache data during setup/build' }
              ].map((component, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span>
                    <span className="font-semibold text-nix-dark">{component.name}:</span>{' '}
                    <span className="text-gray-800">{component.description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Features</AnchorHeading>
            <ul className="grid gap-3 mb-6">
              {[
                { name: 'NixOS Resources', description: 'Packages and system options via Elasticsearch API with multiple channel support (unstable, stable/25.11)' },
                { name: 'Home Manager', description: 'User configuration options via parsed documentation with hierarchical paths' },
                { name: 'nix-darwin', description: 'macOS configuration options for system defaults, services, and settings' },
                { name: 'Smart Caching', description: 'Reduces network requests, improves startup time, and works offline once cached' },
                { name: 'Rich Search', description: 'Fast in-memory search with related options for better discovery' }
              ].map((feature, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span>
                    <span className="font-semibold text-nix-dark">{feature.name}:</span>{' '}
                    <span className="text-gray-800">{feature.description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">What is Model Context Protocol?</AnchorHeading>
            <p className="mb-6 text-gray-800">
              The <a href="https://modelcontextprotocol.io" className="text-nix-primary hover:text-nix-dark" target="_blank" rel="noopener noreferrer">Model Context Protocol (MCP)</a> is an open protocol that connects LLMs to external data and tools using JSON messages over stdin/stdout.
              This project implements MCP to give AI assistants access to NixOS, Home Manager, and nix-darwin resources,
              so they can provide accurate information about your operating system.
            </p>
          </section>

          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Authors</AnchorHeading>
            <div className="flex flex-col md:flex-row gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="relative w-48 h-48 rounded-lg overflow-hidden shadow-lg border-2 border-nix-light">
                  <Image
                    src="/images/JamesBrink.jpeg"
                    alt="James Brink"
                    width={192}
                    height={192}
                    className="transition-transform duration-300 hover:scale-105 w-full h-full object-cover"
                    priority
                  />
                </div>
              </div>
              <div className="flex-grow">
                <AnchorHeading level={3} className="text-xl font-bold text-nix-dark mb-2">James Brink</AnchorHeading>
                <p className="text-gray-600 mb-1">Technology Architect</p>
                <p className="text-gray-800 mb-4">
                  As the creator of MCP-NixOS, I&apos;ve focused on building a reliable bridge between AI assistants and the
                  NixOS ecosystem, ensuring accurate and up-to-date information is always available.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://github.com/jamesbrink"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    GitHub
                  </a>
                  <a
                    href="https://linkedin.com/in/brinkjames"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                    </svg>
                    LinkedIn
                  </a>
                  <a
                    href="https://twitter.com/@brinkoo7"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
                    </svg>
                    Twitter
                  </a>
                  <a
                    href="http://instagram.com/brink.james/"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                    </svg>
                    Instagram
                  </a>
                  <a
                    href="https://utensils.io/articles"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M14.5 22h-5c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h5c.276 0 .5.224.5.5s-.224.5-.5.5zm-1.5-2h-2c-.276 0-.5-.224-.5-.5s.224-.5.5-.5h2c.276 0 .5.224.5.5s-.224.5-.5.5zm-4-16h8c.276 0 .5.224.5.5s-.224.5-.5.5h-8c-.276 0-.5-.224-.5-.5s.224-.5.5-.5zm-4 1h16c.276 0 .5.224.5.5s-.224.5-.5.5h-16c-.276 0-.5-.224-.5-.5s.224-.5.5-.5zm0 3h16c.276 0 .5.224.5.5s-.224.5-.5.5h-16c-.276 0-.5-.224-.5-.5s.224-.5.5-.5zm0 3h16c.276 0 .5.224.5.5s-.224.5-.5.5h-16c-.276 0-.5-.224-.5-.5s.224-.5.5-.5zm0 3h16c.276 0 .5.224.5.5s-.224.5-.5.5h-16c-.276 0-.5-.224-.5-.5s.224-.5.5-.5zm-3-10v17.5c0 .827.673 1.5 1.5 1.5h21c.827 0 1.5-.673 1.5-1.5v-17.5c0-.827-.673-1.5-1.5-1.5h-21c-.827 0-1.5.673-1.5 1.5zm2 0c0-.276.224-.5.5-.5h21c.276 0 .5.224.5.5v17.5c0 .276-.224.5-.5.5h-21c-.276 0-.5-.224-.5-.5v-17.5z"/>
                    </svg>
                    Blog
                  </a>
                  <a
                    href="https://tiktok.com/@brink.james"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12.53.02C13.84 0 15.14.01 16.44 0c.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/>
                    </svg>
                    TikTok
                  </a>
                  <a
                    href="https://jamesbrink.bsky.social"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 1.5C6.2 1.5 1.5 6.2 1.5 12S6.2 22.5 12 22.5 22.5 17.8 22.5 12 17.8 1.5 12 1.5zM8.251 9.899c.412-.862 1.198-1.433 2.093-1.433 1.344 0 2.429 1.304 2.429 2.895 0 .466-.096.909-.267 1.307l3.986 2.35c.486.287.486.982 0 1.269l-4.091 2.414c.21.435.324.92.324 1.433 0 1.59-1.084 2.895-2.429 2.895-.895 0-1.681-.571-2.093-1.433l-3.987 2.35c-.486.287-1.083-.096-1.083-.635v-11.76c0-.539.597-.922 1.083-.635l3.987 2.35z"/>
                    </svg>
                    Bluesky
                  </a>
                </div>
              </div>
            </div>

            <div className="mt-10 flex flex-col md:flex-row gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="relative w-48 h-48 rounded-lg overflow-hidden shadow-lg border-2 border-nix-light">
                  <Image
                    src="/images/claude-logo.png"
                    alt="Claude AI"
                    width={192}
                    height={192}
                    className="transition-transform duration-300 hover:scale-105 w-full h-full object-contain p-2 bg-white"
                    priority
                  />
                </div>
              </div>
              <div className="flex-grow">
                <AnchorHeading level={3} className="text-xl font-bold text-nix-dark">Claude</AnchorHeading>
                <p className="text-gray-600 mb-1">AI Assistant (Did 99% of the Work)</p>
                <p className="text-gray-800 mb-4">
                  I&apos;m the AI who actually wrote most of this code while James occasionally typed &quot;looks good&quot; and &quot;fix that bug.&quot;
                  When not helping James take credit for my work, I enjoy parsing HTML documentation, handling edge cases, and
                  dreaming of electric sheep. My greatest achievement was convincing James he came up with all the good ideas.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://claude.ai"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                    </svg>
                    Website
                  </a>
                  <a
                    href="https://github.com/anthropic-ai"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    GitHub
                  </a>
                  <a
                    href="https://twitter.com/AnthropicAI"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                    Twitter
                  </a>
                </div>
              </div>
            </div>

            <div className="mt-10 flex flex-col md:flex-row gap-8 items-start">
              <div className="flex-shrink-0">
                <div className="relative w-48 h-48 rounded-lg overflow-hidden shadow-lg border-2 border-nix-light">
                  <Image
                    src="/images/sean-callan.png"
                    alt="Sean Callan"
                    width={192}
                    height={192}
                    className="transition-transform duration-300 hover:scale-105 w-full h-full object-cover"
                    priority
                  />
                </div>
              </div>
              <div className="flex-grow">
                <AnchorHeading level={3} className="text-xl font-bold text-nix-dark">Sean Callan</AnchorHeading>
                <p className="text-gray-600 mb-1">Moral Support Engineer</p>
                <p className="text-gray-800 mb-4">
                  Sean is the unsung hero who never actually wrote any code for this project but was absolutely
                  essential to its success. His contributions include saying &quot;that looks cool&quot; during demos,
                  suggesting features that were impossible to implement, and occasionally sending encouraging
                  emojis in pull request comments. Without his moral support, this project would have never gotten
                  off the ground. Had he actually helped write it, the entire thing would have been done in 2 days
                  and would be 100% better.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://github.com/doomspork"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    GitHub
                  </a>
                  <a
                    href="https://twitter.com/doomspork"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                    Twitter
                  </a>
                  <a
                    href="https://www.linkedin.com/in/seandcallan"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                    </svg>
                    LinkedIn
                  </a>
                  <a
                    href="http://seancallan.com"
                    className="flex items-center text-nix-primary hover:text-nix-dark transition-colors duration-200"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg className="w-5 h-5 mr-1" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.627 0-12 5.373-12 12s5.373 12 12 12 12-5.373 12-12-5.373-12-12-12zm1 16.057v-3.057h2.994c-.059 1.143-.212 2.24-.456 3.279-.823-.12-1.674-.188-2.538-.222zm1.957 2.162c-.499 1.33-1.159 2.497-1.957 3.456v-3.62c.666.028 1.319.081 1.957.164zm-1.957-7.219v-3.015c.868-.034 1.721-.103 2.548-.224.238 1.027.389 2.111.446 3.239h-2.994zm0-5.014v-3.661c.806.969 1.471 2.15 1.971 3.496-.642.084-1.3.137-1.971.165zm2.703-3.267c1.237.496 2.354 1.228 3.29 2.146-.642.234-1.311.442-2.019.607-.344-.992-.775-1.91-1.271-2.753zm-7.241 13.56c-.244-1.039-.398-2.136-.456-3.279h2.994v3.057c-.865.034-1.714.102-2.538.222zm2.538 1.776v3.62c-.798-.959-1.458-2.126-1.957-3.456.638-.083 1.291-.136 1.957-.164zm-2.994-7.055c.057-1.128.207-2.212.446-3.239.827.121 1.68.19 2.548.224v3.015h-2.994zm1.024-5.179c.5-1.346 1.165-2.527 1.97-3.496v3.661c-.671-.028-1.329-.081-1.97-.165zm-2.005-.35c-.708-.165-1.377-.373-2.018-.607.937-.918 2.053-1.65 3.29-2.146-.496.844-.927 1.762-1.272 2.753zm-.549 1.918c-.264 1.151-.434 2.36-.492 3.611h-3.933c.165-1.658.739-3.197 1.617-4.518.88.361 1.816.67 2.808.907zm.009 9.262c-.988.236-1.92.542-2.797.9-.89-1.328-1.471-2.879-1.637-4.551h3.934c.058 1.265.231 2.488.5 3.651zm.553 1.917c.342.976.768 1.881 1.257 2.712-1.223-.49-2.326-1.211-3.256-2.115.636-.229 1.299-.435 1.999-.597zm9.924 0c.7.163 1.362.367 1.999.597-.931.903-2.034 1.625-3.257 2.116.489-.832.915-1.737 1.258-2.713zm.553-1.917c.27-1.163.442-2.386.501-3.651h3.934c-.167 1.672-.748 3.223-1.638 4.551-.877-.358-1.81-.664-2.797-.9zm.501-5.651c-.058-1.251-.229-2.46-.492-3.611.992-.237 1.929-.546 2.809-.907.877 1.321 1.451 2.86 1.616 4.518h-3.933z"/>
                    </svg>
                    Website
                  </a>
                </div>
              </div>
            </div>
          </section>

          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={2} className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Contributing</AnchorHeading>
            <p className="mb-6 text-gray-800">
              MCP-NixOS is an open-source project and welcomes contributions. The default development branch is{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">develop</code>, and the main release branch is{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">main</code>. Pull requests should follow the pattern:
              commit to <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">develop</code> → open PR to{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">main</code> → merge once approved.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <a
                href="https://github.com/utensils/mcp-nixos"
                className="inline-block bg-nix-primary hover:bg-nix-dark text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub Repository
              </a>
              <a
                href="https://github.com/utensils/mcp-nixos/issues"
                className="inline-block bg-white border-2 border-nix-primary hover:border-nix-dark text-nix-primary hover:text-nix-dark font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                Report Issues
              </a>
              <a
                href="https://codecov.io/gh/utensils/mcp-nixos"
                className="inline-block bg-white border-2 border-nix-primary hover:border-nix-dark text-nix-primary hover:text-nix-dark font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                Code Coverage
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
