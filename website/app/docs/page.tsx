import CodeBlock from '@/components/CodeBlock';
import AnchorHeading from '@/components/AnchorHeading';

export default function DocsPage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <AnchorHeading level={1} className="text-4xl font-bold mb-8 text-nix-dark">Documentation</AnchorHeading>
        
        <div className="prose prose-lg max-w-none">
          <AnchorHeading level={2} className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2">Overview</AnchorHeading>
          
          <div className="bg-gradient-to-br from-nix-light to-white p-6 rounded-lg shadow-sm mb-8">
            <p className="text-gray-800 mb-6 leading-relaxed">
              MCP-NixOS provides a set of tools to search, explore, and retrieve information about NixOS packages, options, and configurations. 
              These tools are designed to make working with the Nix ecosystem more accessible and efficient through AI assistants and other interfaces.
            </p>
            
            <div className="flex flex-col space-y-6">
              {/* Why Use MCP-NixOS Section */}
              <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5">
                <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-nix-primary" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  Why Use MCP-NixOS?
                </h3>
                <p className="mb-3 text-gray-700">MCP-NixOS is built as a standard I/O (stdio) implementation using <a href="https://github.com/jlowin/fastmcp" target="_blank" rel="noopener noreferrer" className="text-nix-primary hover:underline">FastMCP</a>, the Pythonic framework for building Model Context Protocol servers. This allows seamless integration with AI assistants through the standardized MCP interface.</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">AI Integration</h4>
                    <p className="text-sm text-gray-700">Designed for AI assistants to provide accurate Nix information</p>
                  </div>
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">Unified Interface</h4>
                    <p className="text-sm text-gray-700">Consistent access to NixOS, Home Manager, and nix-darwin</p>
                  </div>
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">Rich Metadata</h4>
                    <p className="text-sm text-gray-700">Detailed information beyond what&apos;s available in standard documentation</p>
                  </div>
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">FastMCP Implementation</h4>
                    <p className="text-sm text-gray-700">Uses stdio communication for reliable tool execution and context sharing</p>
                  </div>
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">Fast Responses</h4>
                    <p className="text-sm text-gray-700">Optimized for quick retrieval with smart caching</p>
                  </div>
                  <div className="bg-nix-light bg-opacity-30 p-3 rounded">
                    <h4 className="font-semibold text-nix-primary mb-1">Markdown Formatting</h4>
                    <p className="text-sm text-gray-700">Human-readable responses that work well in chat interfaces</p>
                  </div>
                </div>
              </div>

              {/* v1.0.0 Architecture */}
              <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5 mt-6">
                <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-nix-primary" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                  </svg>
                  v1.0.0 - The Great Simplification
                </h3>
                
                <div className="mb-4">
                  <h4 className="font-semibold text-nix-primary mb-2">Major Changes</h4>
                  <p className="text-gray-700 mb-2">Version 1.0.0 represents a complete rewrite that drastically simplified the codebase:</p>
                  <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4 mb-3">
                    <li><span className="font-semibold">Dramatically Simplified</span> - Removed all unnecessary abstractions and complexity</li>
                    <li><span className="font-semibold">Stateless Operation</span> - No caching, no state management, just direct API calls</li>
                    <li><span className="font-semibold">Plain Text Output</span> - All responses now return human-readable text (no XML)</li>
                    <li><span className="font-semibold">Minimal Dependencies</span> - Reduced from 5 to 3 core dependencies</li>
                    <li><span className="font-semibold">Two-File Implementation</span> - Everything in just server.py and __main__.py</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="font-semibold text-nix-primary mb-2">New Features in v1.0.0</h4>
                  <p className="text-gray-700 mb-2">Despite the dramatic simplification, we added more functionality:</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                    <div className="bg-nix-light bg-opacity-20 p-3 rounded">
                      <h5 className="font-semibold text-nix-dark mb-1">NixHub Integration</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        <li>Package version history with commit hashes</li>
                        <li>Smart search for specific versions</li>
                        <li>Reproducible builds with exact commits</li>
                      </ul>
                    </div>
                    
                    <div className="bg-nix-light bg-opacity-20 p-3 rounded">
                      <h5 className="font-semibold text-nix-dark mb-1">Enhanced Features</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        <li>Dynamic channel discovery</li>
                        <li>Flake search with deduplication</li>
                        <li>Error messages with suggestions</li>
                        <li>Accurate statistics for all tools</li>
                        <li>100% test coverage</li>
                      </ul>
                    </div>
                  </div>
                  
                  <p className="text-gray-700 text-sm italic">Sometimes the best code is the code you delete. Less complexity = fewer bugs.</p>
                </div>

                <div className="mb-4">
                  <h4 className="font-semibold text-nix-primary mb-2">Data Sources</h4>
                  <p className="text-gray-700 mb-2">MCP-NixOS queries data directly from authoritative sources:</p>
                  <ul className="list-disc list-inside space-y-1 text-gray-700 ml-4">
                    <li><span className="font-semibold">NixOS Elasticsearch API</span> - Official search.nixos.org backend</li>
                    <li><span className="font-semibold">Home Manager HTML Docs</span> - Official documentation parsing</li>
                    <li><span className="font-semibold">nix-darwin HTML Docs</span> - macOS configuration documentation</li>
                    <li><span className="font-semibold">NixHub.io API</span> - Package version history (by Jetify)</li>
                  </ul>
                </div>

                <div className="mb-2">
                  <h4 className="font-semibold text-nix-primary mb-2">Configuration</h4>
                  <p className="text-gray-700 mb-2">Minimal configuration - only one optional environment variable:</p>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm text-gray-700">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left">Variable</th>
                          <th className="px-4 py-2 text-left">Description</th>
                          <th className="px-4 py-2 text-left">Default</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        <tr>
                          <td className="px-4 py-2 font-mono text-xs">ELASTICSEARCH_URL</td>
                          <td className="px-4 py-2">Custom NixOS Elasticsearch API URL</td>
                          <td className="px-4 py-2">https://search.nixos.org/backend</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* FastMCP Implementation */}
              <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-secondary p-5 mt-6">
                <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-nix-secondary" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                  FastMCP and STDIO Implementation
                </h3>
                
                <div className="mb-4">
                  <h4 className="font-semibold text-nix-secondary mb-2">JSON-based Communication Protocol</h4>
                  <p className="text-gray-700 mb-2">MCP-NixOS uses the Model Context Protocol (MCP) with a stdio implementation powered by FastMCP:</p>
                  
                  <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-3">
                    <h5 className="font-semibold text-gray-700 mb-2">Communication Flow</h5>
                    <ol className="list-decimal list-inside space-y-2 text-gray-700">
                      <li>
                        <span className="font-semibold">Request Handling</span>
                        <ul className="list-disc list-inside ml-5 mt-1 text-sm">
                          <li>Client sends JSON request via stdin</li>
                          <li>FastMCP server parses and validates request format</li>
                          <li>Request is routed to appropriate MCP resource handler</li>
                        </ul>
                      </li>
                      <li>
                        <span className="font-semibold">Resource Processing</span>
                        <ul className="list-disc list-inside ml-5 mt-1 text-sm">
                          <li>Resource handler executes the requested operation</li>
                          <li>Data is retrieved from cache or source as needed</li>
                          <li>Response is formatted according to MCP specifications</li>
                        </ul>
                      </li>
                      <li>
                        <span className="font-semibold">Response Delivery</span>
                        <ul className="list-disc list-inside ml-5 mt-1 text-sm">
                          <li>JSON response is serialized with proper formatting</li>
                          <li>Response is written to stdout for client consumption</li>
                          <li>Errors are handled gracefully with descriptive messages</li>
                        </ul>
                      </li>
                    </ol>
                  </div>
                </div>

                <div className="mb-4">
                  <h4 className="font-semibold text-nix-secondary mb-2">FastMCP Integration</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                    <div className="bg-nix-secondary bg-opacity-10 p-3 rounded">
                      <h5 className="font-semibold text-nix-dark mb-1">Server Features</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        <li>Asynchronous request processing</li>
                        <li>Thread-safe resource management</li>
                        <li>Graceful error handling and recovery</li>
                        <li>Comprehensive logging with configurable levels</li>
                        <li>Automatic context management and cleanup</li>
                      </ul>
                    </div>
                    
                    <div className="bg-nix-secondary bg-opacity-10 p-3 rounded">
                      <h5 className="font-semibold text-nix-dark mb-1">MCP Resources</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        <li>URL-based resource identification</li>
                        <li>Consistent scheme patterns (nixos://, home-manager://, darwin://)</li>
                        <li>Structured response formatting</li>
                        <li>Rich metadata with source information</li>
                        <li>Standardized error reporting</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Tool Categories */}
              <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="bg-nix-primary px-5 py-3 text-white">
                  <h3 className="text-lg font-semibold">Available Tools</h3>
                </div>
                
                <div className="divide-y divide-gray-100">
                  {/* NixOS Tools */}
                  <div className="p-5">
                    <div className="flex items-center mb-3">
                      <svg className="w-6 h-6 text-nix-primary mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                      </svg>
                      <h4 className="text-lg font-semibold text-nix-dark">NixOS Tools</h4>
                    </div>
                    <p className="text-gray-700 mb-3 pl-8">Access the vast NixOS ecosystem with tools for searching packages, exploring options, and retrieving detailed information.</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pl-8">
                      <a href="#nixos_search" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_search</code>
                        <span className="text-sm text-gray-600">Find packages, options, or programs</span>
                      </a>
                      <a href="#nixos_info" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_info</code>
                        <span className="text-sm text-gray-600">Get detailed information about specific items</span>
                      </a>
                      <a href="#nixos_stats" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_stats</code>
                        <span className="text-sm text-gray-600">View statistics about available packages and options</span>
                      </a>
                      <a href="#nixos_channels" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_channels</code>
                        <span className="text-sm text-gray-600">List available NixOS channels</span>
                      </a>
                      <a href="#nixos_flakes_search" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_flakes_search</code>
                        <span className="text-sm text-gray-600">Search community flakes</span>
                      </a>
                      <a href="#nixos_flakes_stats" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixos_flakes_stats</code>
                        <span className="text-sm text-gray-600">Flake ecosystem statistics</span>
                      </a>
                    </div>
                  </div>
                  
                  {/* Home Manager Tools */}
                  <div className="p-5">
                    <div className="flex items-center mb-3">
                      <svg className="w-6 h-6 text-nix-primary mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                      </svg>
                      <h4 className="text-lg font-semibold text-nix-dark">Home Manager Tools</h4>
                    </div>
                    <p className="text-gray-700 mb-3 pl-8">Configure and manage your user environment with tools specifically for Home Manager options and settings.</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pl-8">
                      <a href="#home_manager_search" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">home_manager_search</code>
                        <span className="text-sm text-gray-600">Search Home Manager options</span>
                      </a>
                      <a href="#home_manager_info" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">home_manager_info</code>
                        <span className="text-sm text-gray-600">Get details about specific options</span>
                      </a>
                      <a href="#home_manager_options_by_prefix" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">home_manager_options_by_prefix</code>
                        <span className="text-sm text-gray-600">Browse options by category</span>
                      </a>
                      <a href="#home_manager_stats" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">home_manager_stats</code>
                        <span className="text-sm text-gray-600">View statistics about available options</span>
                      </a>
                    </div>
                  </div>
                  
                  {/* nix-darwin Tools */}
                  <div className="p-5">
                    <div className="flex items-center mb-3">
                      <svg className="w-6 h-6 text-nix-primary mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                      <h4 className="text-lg font-semibold text-nix-dark">nix-darwin Tools</h4>
                    </div>
                    <p className="text-gray-700 mb-3 pl-8">Configure macOS systems with tools for exploring and understanding nix-darwin options and configurations.</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pl-8">
                      <a href="#darwin_search" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">darwin_search</code>
                        <span className="text-sm text-gray-600">Search nix-darwin options</span>
                      </a>
                      <a href="#darwin_info" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">darwin_info</code>
                        <span className="text-sm text-gray-600">Get details about specific options</span>
                      </a>
                      <a href="#darwin_list_options" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">darwin_list_options</code>
                        <span className="text-sm text-gray-600">View all top-level categories</span>
                      </a>
                      <a href="#darwin_options_by_prefix" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">darwin_options_by_prefix</code>
                        <span className="text-sm text-gray-600">Browse options by category</span>
                      </a>
                      <a href="#darwin_stats" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">darwin_stats</code>
                        <span className="text-sm text-gray-600">View statistics about available options</span>
                      </a>
                    </div>
                  </div>
                  
                  {/* NixHub Tools */}
                  <div className="p-5">
                    <div className="flex items-center mb-3">
                      <svg className="w-6 h-6 text-nix-primary mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <h4 className="text-lg font-semibold text-nix-dark">NixHub Version History</h4>
                    </div>
                    <p className="text-gray-700 mb-3 pl-8">Track package version history and find specific versions with nixpkgs commit hashes for reproducible builds.</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pl-8">
                      <a href="#nixhub_package_versions" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixhub_package_versions</code>
                        <span className="text-sm text-gray-600">Get package version history</span>
                      </a>
                      <a href="#nixhub_find_version" className="border border-gray-200 rounded p-3 hover:bg-nix-light hover:bg-opacity-20 transition-colors cursor-pointer no-underline">
                        <code className="font-mono text-nix-dark block mb-1">nixhub_find_version</code>
                        <span className="text-sm text-gray-600">Smart search for specific versions</span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <AnchorHeading level={2} className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2">API Reference</AnchorHeading>
          
          <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5 mb-6">
            <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
              <svg className="w-5 h-5 mr-2 text-nix-primary" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                <path fillRule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" clipRule="evenodd" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
              </svg>
              Response Format
            </h3>
            
            <p className="text-gray-700 mb-3">All MCP-NixOS responses are wrapped in a standardized JSON structure following the Model Context Protocol:</p>
            
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-3">
              <CodeBlock
                code={`{
  "result": "# Markdown or text content here...\n\nFormatted for AI consumption",
  "status": "success",
  "metadata": {
    "source": "nixos|home-manager|darwin",
    "timestamp": 1649267584,
    "cache_hit": true,
    "query_time_ms": 42
  }
}`}
                language="json"
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-nix-light bg-opacity-20 p-3 rounded">
                <h4 className="font-semibold text-nix-dark mb-1">Key Fields</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                  <li><span className="font-mono text-xs">result</span>: The main response content (markdown/text)</li>
                  <li><span className="font-mono text-xs">status</span>: Operation result (success/error)</li>
                  <li><span className="font-mono text-xs">metadata</span>: Additional context information</li>
                  <li><span className="font-mono text-xs">error</span>: Error message (if status is error)</li>
                </ul>
              </div>
              
              <div className="bg-nix-light bg-opacity-20 p-3 rounded">
                <h4 className="font-semibold text-nix-dark mb-1">Response Characteristics</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                  <li>Markdown formatting optimized for AI consumption</li>
                  <li>Consistent structure across all tools</li>
                  <li>Rich metadata for context awareness</li>
                  <li>Documentation examples show only the <span className="font-mono text-xs">result</span> field for clarity</li>
                </ul>
              </div>
            </div>
          </div>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">NixOS Resources & Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about NixOS packages, options, and programs.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">nixos_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for NixOS packages, options, or programs.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">type</code>: The type to search (&quot;packages&quot;, &quot;options&quot;, or &quot;programs&quot;) - default: &quot;packages&quot;</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <div className="flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                <h5 className="text-md font-semibold mb-2 text-nix-primary">
                  Example: Search for packages
                </h5>
              </div>
              <CodeBlock
                code={`{
  &quot;type&quot;: &quot;call&quot;,
  &quot;tool&quot;: &quot;nixos_search&quot;,
  &quot;params&quot;: {
    &quot;query&quot;: &quot;python&quot;,
    &quot;type&quot;: &quot;packages&quot;,
    &quot;limit&quot;: 10,
    &quot;channel&quot;: &quot;unstable&quot; 
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`Found 10 packages matching 'python':

- python2 (2.7.18.8)
  High-level dynamically-typed programming language

- python2Full (2.7.18.8)
  High-level dynamically-typed programming language

- python27Full (2.7.18.8)
  High-level dynamically-typed programming language

- python3Full (3.12.9)
  High-level dynamically-typed programming language

- python314 (3.14.0a6)
  High-level dynamically-typed programming language

- python39 (3.9.21)
  High-level dynamically-typed programming language

- python3Minimal (3.12.9)
  High-level dynamically-typed programming language

- python313Full (3.13.2)
  High-level dynamically-typed programming language

- python314Full (3.14.0a6)
  High-level dynamically-typed programming language

- texlivePackages.python (0.22)
  Embed Python code in LaTeX`}
                  language="text"

                />
              </div>
            </div>
            
            <div className="mt-4 mb-6">
              <div className="flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                <h5 className="text-md font-semibold mb-2 text-nix-primary">
                  Example: Search for options
                </h5>
              </div>
              <CodeBlock
                code={`{
  &quot;type&quot;: &quot;call&quot;,
  &quot;tool&quot;: &quot;nixos_search&quot;,
  &quot;params&quot;: {
    &quot;query&quot;: &quot;services.postgresql&quot;,
    &quot;type&quot;: &quot;options&quot;,
    &quot;channel&quot;: &quot;unstable&quot;
  }
}`}
                language="json"
              />
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a NixOS package or option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the package or option</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">type</code>: Either &quot;package&quot; or &quot;option&quot; - default: &quot;package&quot;</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get package info
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_info",
  "params": {
    "name": "python3Full",
    "type": "package",
    "channel": "unstable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# python3Full

**Version:** 3.12.9

**Description:** High-level dynamically-typed programming language

**Long Description:**
Python is a remarkably powerful dynamic programming language that is
used in a wide variety of application domains...

**Homepage:** https://www.python.org

**License:** Python Software Foundation License version 2

**Source:** [pkgs/development/interpreters/python/cpython/default.nix:803](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/interpreters/python/cpython/default.nix#L803)

**Maintainers:** Martin Weinelt, Tomoya Otabi

**Platforms:** mips64-linux, i686-freebsd, armv6l-linux, i686-cygwin, riscv64-linux, x86_64-darwin...

**Provided Programs:** 2to3, 2to3-3.12, idle, idle3, idle3.12, pydoc, pydoc3, pydoc3.12, python, python-config, python3, python3-config, python3.12, python3.12-config`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about available NixOS packages and options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get NixOS stats
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_stats",
  "params": {
    "channel": "unstable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# NixOS Statistics (Channel: unstable)

Total options: 21,496

## Package Statistics

### Top 10 Platforms
- x86_64-linux: 118,497 packages
- aarch64-linux: 116,467 packages
- i686-linux: 116,344 packages
- armv7l-linux: 115,540 packages
- armv6l-linux: 115,483 packages
- riscv64-linux: 115,469 packages
- powerpc64le-linux: 115,453 packages
- armv7a-linux: 115,365 packages
- armv5tel-linux: 115,362 packages
- s390x-linux: 115,344 packages`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_channels()</AnchorHeading>
            <p className="mb-3 text-gray-800">List available NixOS channels with their status.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: List channels
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_channels"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Available NixOS Channels

- unstable: ✓ Available
- stable: ✓ Available (currently 25.05)
- beta: → Redirects to stable
- 25.05: ✓ Available
- 24.11: ✓ Available
- 24.05: ✓ Available
- 23.11: ✓ Available
- 23.05: ✓ Available`}
                  language="text"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_flakes_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for community flakes in the NixOS ecosystem.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Search flakes
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_flakes_search",
  "params": {
    "query": "devenv",
    "limit": 10
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`Found 12 total matches (3 unique flakes) for 'devenv':

## github:cachix/devenv (5 packages)
Tools for creating developer environments

Packages: devenv, devenv-docs-generate, devenv-run-tests, generate-doc-options, mkdocs-scan

## github:cachix/devenv/latest (4 packages)
Tools for creating developer environments

Packages: devenv, devenv-run-tests, generate-doc-options, mkdocs-scan

## github:cachix/devenv/python-rewrite (3 packages)
Tools for creating developer environments

Packages: devenv, generate-doc-options, mkdocs-scan`}
                  language="text"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_flakes_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about available flakes in the NixOS ecosystem.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get flake stats
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_flakes_stats"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# NixOS Flakes Statistics

Available flakes: 894
Unique repositories: 6

## Flake Types
- github: 6 flakes (100.0%)

## Top Contributors
- NixOS: 523 packages
- nix-community: 194 packages
- numtide: 91 packages
- cachix: 50 packages
- DeterminateSystems: 36 packages`}
                  language="text"
                />
              </div>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">Home Manager Resources & Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about Home Manager options and configurations.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">home_manager_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for Home Manager options based on a query string.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <div className="flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                <h5 className="text-md font-semibold mb-2 text-nix-primary">
                  Example: Search for options
                </h5>
              </div>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_search",
  "params": {
    "query": "programs.neovim",
    "limit": 5
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Search Results for 'programs.neovim' (5 of 12 results)

## programs.neovim.enable

**Type**: boolean
**Default**: false
**Description**: Whether to enable Neovim.

## programs.neovim.defaultEditor

**Type**: boolean
**Default**: false
**Description**: Whether to configure the EDITOR environment variable to use Neovim.

## programs.neovim.package

**Type**: package
**Default**: pkgs.neovim
**Description**: The Neovim package to use.

## programs.neovim.viAlias

**Type**: boolean
**Default**: false
**Description**: Symlink 'vi' to 'nvim' binary.

## programs.neovim.vimAlias

**Type**: boolean
**Default**: false
**Description**: Symlink 'vim' to 'nvim' binary.`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a specific Home Manager option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the option</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get option info
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_info",
  "params": {
    "name": "programs.git.enable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# programs.git.enable

## Type
boolean

## Default
false

## Description
Whether to install and configure Git.

## Declared In
/nix/store/...-source/modules/programs/git.nix:15

## Defined In
/nix/store/...-source/modules/programs/git.nix:15

## Example
{
  programs.git.enable = true;
}

## Related Options
- programs.git.package
- programs.git.userName
- programs.git.userEmail
- programs.git.aliases
- programs.git.signing
- programs.git.extraConfig`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_list_options()</AnchorHeading>
            <p className="mb-3 text-gray-800">List all top-level Home Manager option categories with statistics.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: List option categories
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_list_options"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Top-Level Option Categories

Total categories: 25
Total options: 2456

## programs

- **Options count**: 500
- **Option types**:
  - boolean: 149
  - null or package: 39
  - list of string: 32
  - strings concatenated with &quot;\n&quot;: 28
  - package: 23
- **Enable options**: 70
  - abook: Whether to enable Abook..
  - aerc: Whether to enable aerc..
  - aerospace: Whether to enable AeroSpace window manager..
  - ...and 67 more`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_options_by_prefix()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get all Home Manager options under a specific prefix.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">option_prefix</code>: The option prefix to search for (e.g., &quot;programs&quot;, &quot;programs.git&quot;)</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get options by prefix
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_options_by_prefix",
  "params": {
    "option_prefix": "programs.git"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Options: programs.git

Found 67 options

## Direct Options

- **programs.git.aliases** (aliases) (attribute set of string)
  Git aliases to define.
- **programs.git.attributes** (attributes) (list of string)
  List of defining attributes set globally.
- **programs.git.enable** (enable) (boolean)
  Whether to enable Git.
- **programs.git.extraConfig** (extraConfig) (strings concatenated with "\n" or attribute set of attribute set of (string or boolean or signed integer or list of (string or boolean or signed integer) or attribute set of (string or boolean or signed integer or list of (string or boolean or signed integer))))
  Additional configuration to add. The use of string values is
deprecated and will be removed in the future.
- **programs.git.hooks** (hooks) (attribute set of absolute path)
  Configuration helper for Git hooks.
See https://git-scm.com/docs/githooks
for reference.
- **programs.git.ignores** (ignores) (list of string)
  List of paths that should be globally ignored.

## Option Groups

### cliff options (3)

To see all options in this group, use:
\`home_manager_options_by_prefix(option_prefix="programs.git.cliff")\`

- **enable** (boolean)
- **package** (null or package)
- **settings** (TOML value)

### signing options (4)

To see all options in this group, use:
\`home_manager_options_by_prefix(option_prefix="programs.git.signing")\`

- **format** (null or one of "openpgp", "ssh", "x509")
- **key** (null or string)
- **signByDefault** (null or boolean)
- **signer** (null or string)`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about Home Manager options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get Home Manager stats
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_stats"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Option Statistics

Total options: 3704
Categories: 4
Option types: 391

## Distribution by Source

- options: 3697 options
- nix-darwin-options: 7 options

## Top Categories

- Note: 1943 options
- Caution: 1264 options
- Uncategorized: 430 options
- Warning: 74 options

## Distribution by Type

- boolean: 936 options
- null or string: 300 options
- string: 282 options
- package: 239 options
- list of string: 175 options
- strings concatenated with "\n": 145 options
- null or boolean: 137 options
- null or package: 136 options
- null or signed integer: 82 options
- attribute set of string: 71 options

## Index Statistics

- Words indexed: 4382
- Prefix paths: 4432
- Hierarchical parts: 4403`}
                  language="markdown"
                />
              </div>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">nix-darwin Resources & Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about nix-darwin macOS options and configurations.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">darwin_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for nix-darwin options based on a query string.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Search for darwin options
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_search",
  "params": {
    "query": "keyboard",
    "limit": 5
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Search Results for 'keyboard' (5 of 15 results)

## system.keyboard.enableKeyMapping

**Type**: boolean
**Default**: false
**Description**: Whether to enable keyboard mapping.

## system.keyboard.remapCapsLockToControl

**Type**: boolean
**Default**: false
**Description**: Whether to remap the Caps Lock key to Control.

## system.keyboard.remapCapsLockToEscape

**Type**: boolean
**Default**: false
**Description**: Whether to remap the Caps Lock key to Escape.`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a specific nix-darwin option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the option</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get option info
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_info",
  "params": {
    "name": "homebrew.enable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## homebrew.enable
Whether to enable nix-darwin to manage installing/updating/upgrading Homebrew taps, formulae,
and casks, as well as Mac App Store apps and Docker containers, using Homebrew Bundle. Note that enabling this option does not install Homebrew, see the Homebrew website for installation instructions. Use the homebrew.brews , homebrew.casks , homebrew.masApps , and homebrew.whalebrews options
to list the Homebrew formulae, casks, Mac App Store apps, and Docker containers you'd like to
install. Use the homebrew.taps option, to make additional formula
repositories available to Homebrew. This module uses those options (along with the homebrew.caskArgs options) to generate a Brewfile that nix-darwin passes to the brew bundle command during
system activation.

**Type:** boolean
**Default:** false
**Example:** true
**Declared by:** <nix-darwin/modules/homebrew.nix>`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_list_options()</AnchorHeading>
            <p className="mb-3 text-gray-800">List all top-level nix-darwin option categories with statistics.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: List option categories
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_list_options"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin Option Categories
### _module
- **Options count:** 1
- **Usage:** \`darwin._module\`

### documentation
- **Options count:** 4
- **Usage:** \`darwin.documentation\`

### environment
- **Options count:** 34
- **Usage:** \`darwin.environment\`

### fonts
- **Options count:** 1
- **Usage:** \`darwin.fonts\`

### homebrew
- **Options count:** 49
- **Usage:** \`darwin.homebrew\`

### launchd
- **Options count:** 249
- **Usage:** \`darwin.launchd\`

### networking
- **Options count:** 26
- **Usage:** \`darwin.networking\`

### nix
- **Options count:** 55
- **Usage:** \`darwin.nix\`

### nixpkgs
- **Options count:** 10
- **Usage:** \`darwin.nixpkgs\`

### power
- **Options count:** 6
- **Usage:** \`darwin.power\`

### programs
- **Options count:** 69
- **Usage:** \`darwin.programs\`

### security
- **Options count:** 17
- **Usage:** \`darwin.security\`

### services
- **Options count:** 297
- **Usage:** \`darwin.services\`

### system
- **Options count:** 208
- **Usage:** \`darwin.system\`

### time
- **Options count:** 1
- **Usage:** \`darwin.time\`

### users
- **Options count:** 20
- **Usage:** \`darwin.users\`

To view options in a specific category, use the \`darwin_options_by_prefix\` tool with the category name.`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_options_by_prefix()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get all nix-darwin options under a specific prefix.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">option_prefix</code>: The option prefix to search for (e.g., &quot;homebrew&quot;, &quot;system&quot;)</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get options by prefix
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_options_by_prefix",
  "params": {
    "option_prefix": "homebrew"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin options with prefix 'homebrew'
Found 49 options.

### homebrew.brewPrefix
The path prefix where the brew executable is located. This will be set to
the correct value based...
**Type:** \`string\`

For more details, use \`darwin_info("homebrew.brewPrefix")\`

### homebrew.brews
List of Homebrew formulae to install. Formulae defined as strings, e.g., "imagemagick" , are a sh...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.brews")\`

### homebrew.brews._.args
Arguments flags to pass to brew install . Values should not include the
leading "--" . Type: null...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.args")\`

### homebrew.brews._.conflicts_with
List of formulae that should be unlinked and their services stopped (if they are
installed). Type...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.conflicts_with")\`

### homebrew.brews._.link
Whether to link the formula to the Homebrew prefix. When this option is null , Homebrew will use ...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.link")\`

### homebrew.brews._.name
The name of the formula to install. Type: string Declared by: <nix-darwin/modules/homebrew.nix>
**Type:** \`string\`

For more details, use \`darwin_info("homebrew.brews._.name")\`

### homebrew.taps
List of Homebrew formula repositories to tap. Taps defined as strings, e.g., "user/repo" , are a ...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.taps")\`

### homebrew.whalebrews
List of Docker images to install using whalebrew . When this option is used, "whalebrew" is autom...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.whalebrews")\`

[...and more options]`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about nix-darwin options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get Darwin stats
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_stats"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin Options Statistics
- **Total options:** 1048
- **Total categories:** 16
- **Last updated:** 2025-04-03T22:07:02.122217

### Top-level Categories
- **_module**: 1 options
- **documentation**: 4 options
- **environment**: 34 options
- **fonts**: 1 options
- **homebrew**: 49 options
- **launchd**: 249 options
- **networking**: 26 options
- **nix**: 55 options
- **nixpkgs**: 10 options
- **power**: 6 options
- **programs**: 69 options
- **security**: 17 options
- **services**: 297 options
- **system**: 208 options
- **time**: 1 options
- **users**: 20 options`}
                  language="markdown"
                />
              </div>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">NixHub Version History Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for tracking package version history and finding specific versions with nixpkgs commit hashes.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">nixhub_package_versions()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get version history for a specific package with nixpkgs commit hashes.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">package_name</code>: Name of the package to query</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of versions to return (1-50) - default: 10</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Get package versions
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixhub_package_versions",
  "params": {
    "package_name": "ruby",
    "limit": 15
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Package: ruby

Found 15 versions in NixHub:

## 3.3.6 (Latest)
- Date: 2025-05-07
- Platforms: aarch64-darwin, aarch64-linux, x86_64-darwin, x86_64-linux
- Commit: \`a7117efb3725e6c3d3113b574d8c5014f402e2b2\`
- Nix expression: \`nix build nixpkgs#ruby --override-input nixpkgs github:NixOS/nixpkgs/a7117efb3725e6c3d3113b574d8c5014f402e2b2\`

## 3.3.5
- Date: 2025-03-27
- Platforms: aarch64-darwin, aarch64-linux, x86_64-darwin, x86_64-linux
- Commit: \`5a237aecb57296f67d7aab035f77f9ef92ebb9c6\`
- Nix expression: \`nix build nixpkgs#ruby --override-input nixpkgs github:NixOS/nixpkgs/5a237aecb57296f67d7aab035f77f9ef92ebb9c6\`

## 2.7.8
- Date: 2024-11-28
- Platforms: aarch64-darwin, aarch64-linux, x86_64-darwin, x86_64-linux
- Attribute: ruby_2_7
- Commit: \`057f63143dc45e3b43d9325c4741c26479f4d25e\`
- Nix expression: \`nix build nixpkgs#ruby_2_7 --override-input nixpkgs github:NixOS/nixpkgs/057f63143dc45e3b43d9325c4741c26479f4d25e\`

[... more versions ...]`}
                  language="text"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixhub_find_version()</AnchorHeading>
            <p className="mb-3 text-gray-800">Smart search for a specific package version, automatically increasing search depth if needed.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">package_name</code>: Name of the package to query</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">version</code>: Specific version to find</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <h5 className="text-md font-semibold mb-2 text-nix-primary">
                <div className="flex items-center">
                  <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2 text-nix-primary" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                  </svg>
                  Example: Find specific version
                </div>
              </h5>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixhub_find_version",
  "params": {
    "package_name": "python",
    "version": "3.5.9"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Found python version 3.5.9!

## Version 3.5.9
- Date: 2020-04-18
- Platforms: x86_64-linux
- Attribute: python35
- Commit: \`e19054ab3cd5b7cc9a01d0efc71cc937bfb9ce0a\`

### Install with:
\`\`\`bash
nix build nixpkgs#python35 --override-input nixpkgs github:NixOS/nixpkgs/e19054ab3cd5b7cc9a01d0efc71cc937bfb9ce0a
\`\`\`

Note: Searched through 50 versions to find this exact match.`}
                  language="text"
                />
              </div>
            </div>
          </section>
          
          <AnchorHeading id="configuration" level={2} className="text-2xl font-bold mt-12 mb-6 text-nix-primary border-b border-nix-light pb-2">Configuration</AnchorHeading>
          <p className="mb-6 text-gray-800 font-medium">
            <strong>v1.0.0 Update:</strong> Configuration has been dramatically simplified. There&apos;s only one optional environment variable now:
          </p>
          
          <div className="overflow-x-auto mb-12 rounded-lg shadow-sm">
            <div className="min-w-full md:min-w-0">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-nix-primary">
                    <th className="px-3 sm:px-6 py-3 text-left text-white font-semibold">Variable</th>
                    <th className="px-3 sm:px-6 py-3 text-left text-white font-semibold">Description</th>
                    <th className="px-3 sm:px-6 py-3 text-left text-white font-semibold">Default Value</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all">ELASTICSEARCH_URL</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700">Custom NixOS Elasticsearch API URL <span className="text-xs text-gray-500 italic">(only needed for custom deployments)</span></td>
                    <td className="px-3 sm:px-6 py-4 text-sm font-mono text-gray-700">https://search.nixos.org/backend</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-secondary p-5 mb-12">
            <h3 className="text-lg font-semibold text-nix-dark mb-2 flex items-center">
              <svg className="w-5 h-5 mr-2 text-nix-secondary" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              What happened to all the configuration options?
            </h3>
            <p className="text-gray-700">
              In v1.0.0, we removed all caching and state management, which eliminated the need for configuration options like:
            </p>
            <ul className="list-disc list-inside mt-2 text-gray-700 space-y-1">
              <li>Cache directories and TTL settings (no more caching)</li>
              <li>Log levels and log files (simplified logging)</li>
              <li>Pre-cache options (stateless operation)</li>
              <li>Clean up settings (nothing to clean up)</li>
            </ul>
            <p className="text-gray-700 mt-2">
              The result? Zero configuration needed for 99% of users. Just install and use.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}