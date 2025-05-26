import AnchorHeading from '@/components/AnchorHeading';
import CodeBlock from '@/components/CodeBlock';
import CollapsibleSection from '@/components/CollapsibleSection';
import Link from 'next/link';

export default function UsagePage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8 text-nix-dark">
          Usage Examples
        </h1>

        <div className="prose prose-lg max-w-none">
          <AnchorHeading
            level={2}
            className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2"
          >
            Overview
          </AnchorHeading>

          <div className="bg-gradient-to-br from-nix-light to-white p-6 rounded-lg shadow-sm mb-8">
            <p className="text-gray-800 mb-6 leading-relaxed">
              These examples demonstrate how to use MCP-NixOS tools to solve common Nix ecosystem
              tasks. Each example shows the JSON request format and the corresponding response,
              helping you understand how to effectively leverage MCP-NixOS in your workflows.
            </p>
            
            <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5 mb-2">
              <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
                <span className="flex items-center">
                  <svg className="w-5 h-5 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Configuration
                </span>
              </AnchorHeading>
              <p className="mb-4 text-gray-700">
                Before using these examples, you&apos;ll need to configure your MCP server. Add one of the following to your MCP configuration file:
              </p>
              
              <div className="mb-4">
                <h4 className="font-semibold text-nix-dark mb-2">Option 1: Using uvx (Recommended for most users)</h4>
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
              </div>
              
              <div className="mb-4">
                <h4 className="font-semibold text-nix-dark mb-2">Option 2: Using Nix (For Nix users)</h4>
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
              </div>
              
              <p className="mt-4 text-gray-700 text-sm">
                <strong>Note:</strong> No Nix/NixOS installation required! This tool works on any system (Windows, macOS, Linux) as it just queries web APIs. Choose the method that matches your existing tooling.
              </p>
              <p className="mt-2 text-gray-700 text-sm">
                This configuration enables your AI assistant to access NixOS package information and configuration options through the MCP protocol. For additional configuration options, see the <Link href="/docs#configuration" className="text-nix-primary hover:text-nix-dark underline transition-colors">configuration documentation</Link>.
              </p>
            </div>
          </div>

          <AnchorHeading
            level={2}
            className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2"
          >
            Example Scenarios
          </AnchorHeading>

          <div className="space-y-8">
            <p className="text-gray-700 mb-6 leading-relaxed">
              These examples demonstrate practical use cases for MCP-NixOS tools and the type of
              information they provide. Each example shows the complete workflow from user question to AI response.
            </p>
            
            <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
              <span className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 1: PostgreSQL Versions and Configuration
              </span>
            </AnchorHeading>

            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;What PostgreSQL versions are available in NixOS, and what are the
                configuration options?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for PostgreSQL Packages">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS search for packages",
  "type": "packages",
  "limit": 10,
  "query": "postgresql"
}
Found 10 packages matching 'postgresql':

- postgresql_13 (13.14)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_14 (14.10)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_15 (15.5)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_16 (16.1)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_17 (17.0)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql (16.1)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql-unit (7.11.0)
  SI Units for PostgreSQL

- postgresql_jdbc (42.6.1)
  JDBC driver for PostgreSQL allowing Java programs to connect to a PostgreSQL database

- postgresql17JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications

- postgresql14JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get PostgreSQL Service Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS info for option",
  "type": "option",
  "name": "services.postgresql"
}
# services.postgresql

**Description:** PostgreSQL database server.

**Type:** option set

**Declared by:**
- nixpkgs/nixos/modules/services/databases/postgresql.nix

**Default value:** {}

**Example:**
\`\`\`nix
{
  services.postgresql = {
    enable = true;
    package = pkgs.postgresql_14;
    enableTCPIP = true;
    authentication = pkgs.lib.mkOverride 10 ''
      local all all trust
      host all all 127.0.0.1/32 trust
      host all all ::1/128 trust
    '';
    initialScript = pkgs.writeText "backend-initScript" ''
      CREATE ROLE nixcloud WITH LOGIN PASSWORD 'nixcloud' CREATEDB;
      CREATE DATABASE nixcloud;
      GRANT ALL PRIVILEGES ON DATABASE nixcloud TO nixcloud;
    '';
  };
}
\`\`\`

**Option: services.postgresql.authentication** (strings concatenated with "\\n")
Defines how users authenticate when connecting to the database. See the
documentation for pg_hba.conf for details on the expected format of
this option. By default, peer based authentication will be used for
users connecting via the Unix socket, and md5 password authentication
will be used for users connecting via TCP. Any added rules will be
inserted above the default rules. If you'd like to replace the default
rules entirely, you can use \`lib.mkForce\` in your module.

**Type:** strings concatenated with "\\n"

**Option: services.postgresql.dataDir** (absolute path)
  The data directory for PostgreSQL.
**Option: services.postgresql.enable** (boolean)
  Whether to enable PostgreSQL Server.
**Option: services.postgresql.enableJIT** (boolean)
  Whether to enable JIT support.
**Option: services.postgresql.enableTCPIP** (boolean)
  Whether PostgreSQL should listen on all network interfaces.`}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  NixOS provides multiple versions of PostgreSQL:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>PostgreSQL 13 (13.14)</li>
                  <li>PostgreSQL 14 (14.10)</li>
                  <li>PostgreSQL 15 (15.5)</li>
                  <li>PostgreSQL 16 (16.1) - This is the default version</li>
                  <li>PostgreSQL 17 (17.0) - Latest version</li>
                </ul>
                <p className="text-gray-700 mt-2">
                  For configuration, you can use the <code className="font-mono text-xs">services.postgresql</code> module with these key options:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    <code className="font-mono text-xs">enable</code> - Enable the PostgreSQL server
                  </li>
                  <li>
                    <code className="font-mono text-xs">package</code> - Select which PostgreSQL version to use
                  </li>
                  <li>
                    <code className="font-mono text-xs">authentication</code> - Configure client authentication methods
                  </li>
                  <li>
                    <code className="font-mono text-xs">enableTCPIP</code> - Allow network connections (not just local socket)
                  </li>
                  <li>
                    <code className="font-mono text-xs">dataDir</code> - Specify where to store the database files
                  </li>
                </ul>
                <p className="text-gray-700 mt-2">
                  This information helps system administrators choose the appropriate
                  PostgreSQL version and configure it according to their specific
                  requirements.
                </p>
              </div>
            </div>

            <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
              <span className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 2: Checking Package Availability
              </span>
            </AnchorHeading>
            
            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;Is the tldr package available in NixOS, and what variants exist?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for tldr Package">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS search for packages",
  "type": "packages",
  "limit": 10,
  "query": "tldr"
}
Found 6 packages matching 'tldr':

- tldr (3.3.0)
  Simplified and community-driven man pages

- haskellPackages.tldr (0.9.2)
  Haskell tldr client

- tlrc (1.11.0)
  Official tldr client written in Rust

- tealdeer (1.7.2)
  Very fast implementation of tldr in Rust

- emacsPackages.tldr (20230301.136)

- rPackages.tldr (0.4.0)`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get Detailed Package Information">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS info for package",
  "type": "package",
  "name": "tldr"
}
# tldr

**Version:** 3.3.0

**Description:** Simplified and community-driven man pages

**Long Description:**
tldr pages gives common use cases for commands, so you don't need to
hunt through a man page for the correct flags.

**Homepage:** https://tldr.sh

**License:** MIT License

**Maintainers:** Taeer Bar-Yam, Carlos D'Agostino, K.B.Dharun Krishna

**Platforms:** Multiple platforms including Linux, macOS, Windows, and more

**Provided Programs:** tldr`}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  NixOS provides several implementations of the tldr client:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    The main Python-based <code className="font-mono text-xs">tldr</code>{' '}
                    package
                  </li>
                  <li>
                    Rust implementations: <code className="font-mono text-xs">tlrc</code>{' '}
                    (official) and <code className="font-mono text-xs">tealdeer</code>{' '}
                    (optimized for speed)
                  </li>
                  <li>Language-specific implementations for Haskell, Emacs Lisp, and R</li>
                </ul>
                <p className="text-gray-700 mt-2">
                  The main package is available across multiple platforms and provides a
                  simple command-line interface for accessing community-maintained
                  simplified documentation. This is particularly useful for quickly finding
                  common usage examples without having to read through comprehensive man
                  pages.
                </p>
              </div>
            </div>

            <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
              <span className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 3: Validating NixOS Configuration
              </span>
            </AnchorHeading>
            
            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;Can you validate this Nginx configuration for me?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for Nginx Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS options for nginx configuration",
  "type": "options",
  "limit": 20,
  "query": "services.nginx"
}
Found 20 options matching 'services.nginx':

- services.nginx.enable (boolean)
  Whether to enable the nginx web server.

- services.nginx.recommendedGzipSettings (boolean)
  Whether to enable recommended gzip settings.

- services.nginx.recommendedOptimisation (boolean)
  Whether to enable recommended optimisation settings.

- services.nginx.recommendedProxySettings (boolean)
  Whether to enable recommended proxy settings.

- services.nginx.recommendedTlsSettings (boolean)
  Whether to enable recommended TLS settings.

- services.nginx.statusPage (boolean)
  Whether to enable status page.

- services.nginx.virtualHosts (attribute set of attribute sets)
  Declarative vhost config.

- services.nginx.package (package)
  Nginx package to use.

- services.nginx.appendConfig (strings concatenated with "\n")
  Configuration lines appended to the generated Nginx configuration.

- services.nginx.appendHttpConfig (strings concatenated with "\n")
  Configuration lines to be appended to the main http block.`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get Detailed Nginx Module Information">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS info for nginx options",
  "type": "option",
  "name": "services.nginx"
}
# services.nginx

**Description:** Configuration for nginx.

**Type:** option set

**Declared by:**
- nixpkgs/nixos/modules/services/web-servers/nginx/default.nix

**Default value:** {}

**Example:**
\`\`\`nix
{
  services.nginx = {
    enable = true;
    virtualHosts."example.com" = {
      enableACME = true;
      forceSSL = true;
      locations."/" = {
        root = "/var/www/example.com";
      };
    };
  };
}
\`\`\`

**Option: services.nginx.addSSL** (boolean)
  Whether to add a default SSL virtual host.

**Option: services.nginx.appendConfig** (strings concatenated with "\n")
  Configuration lines appended to the generated Nginx configuration.

**Option: services.nginx.appendHttpConfig** (strings concatenated with "\n")
  Configuration lines to be appended to the main http block.

**Option: services.nginx.clientMaxBodySize** (string)
  Set nginx's client_max_body_size.

**Option: services.nginx.commonHttpConfig** (strings concatenated with "\n")
  Configuration lines to be appended to the http block.`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 3: Check Worker Process Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS options for nginx worker processes",
  "type": "options",
  "limit": 5,
  "query": "services.nginx worker"
}
Found 2 options matching 'services.nginx worker':

- services.nginx.workerProcesses (string or positive integer)
  Number of worker processes to use. The default is "auto", which lets nginx determine the number of worker processes based on the number of CPU cores.

- services.nginx.eventsConfig (strings concatenated with "\n")
  Configuration lines to be appended to the events block.`}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  I&apos;ve analyzed your Nginx configuration and found several issues that need to be corrected:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    <code className="font-mono text-xs">fastReload</code>, <code className="font-mono text-xs">cacheStrategy</code>, <code className="font-mono text-xs">compressionLevel</code>, <code className="font-mono text-xs">timeoutMs</code>, <code className="font-mono text-xs">requestRateLimiting</code>, and <code className="font-mono text-xs">tlsSettings</code> are not valid NixOS options
                  </li>
                  <li>
                    <code className="font-mono text-xs">workerProcesses</code> should be <code className="font-mono text-xs">&quot;auto&quot;</code> not <code className="font-mono text-xs">&quot;optimal&quot;</code>
                  </li>
                  <li>
                    Custom settings should use <code className="font-mono text-xs">extraConfig</code> and <code className="font-mono text-xs">appendHttpConfig</code>
                  </li>
                </ul>
                <p className="text-gray-700 mt-2">
                  Here&apos;s the corrected configuration:
                </p>
                <CodeBlock
                  code={`{ config, pkgs, ... }:

{
  services.nginx = {
    enable = true;
    # fastReload is not a valid option, removed
    
    virtualHosts."example.com" = {
      enableACME = true;
      forceSSL = true;
      root = "/var/www/example.com";
      
      locations."/" = {
        index = "index.html";
        # cacheStrategy is not a valid option
        # You can use extraConfig to add caching directives:
        extraConfig = ''
          expires max;
          add_header Cache-Control "public, immutable";
        '';
      };
      
      locations."/api" = {
        proxyPass = "http://localhost:8080";
        # compressionLevel is not a valid option
        # timeoutMs is not a valid option
        # Use extraConfig for these custom settings:
        extraConfig = ''
          proxy_read_timeout 5s;
          gzip on;
          gzip_comp_level 9;
        '';
      };
    };
    
    workerProcesses = "auto"; # "optimal" is not valid, use "auto"
    
    # requestRateLimiting is not a valid option block
    # Use recommendedProxySettings and limit_req_zone in httpConfig
    recommendedProxySettings = true;
    appendHttpConfig = ''
      limit_req_zone $binary_remote_addr zone=limit:10m rate=100r/s;
      limit_req zone=limit burst=20 nodelay;
    '';
    
    # tlsSettings is not a valid option block
    # Use recommendedTlsSettings instead
    recommendedTlsSettings = true;
    # For additional TLS settings, use sslCiphers and sslProtocols
    sslCiphers = "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
    sslProtocols = "TLSv1.2 TLSv1.3";
  };
}`}
                  language="nix"
                />
                <p className="text-gray-700 mt-2">
                  This corrected configuration follows NixOS best practices for Nginx setup, using standard options and proper syntax for custom settings. The configuration enables HTTPS with ACME (Let&apos;s Encrypt), sets up a static file server with caching, configures an API proxy with compression, implements rate limiting, and applies recommended security settings.                  
                </p>
              </div>
            </div>

            <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
              <span className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 4: Checking Cross-Platform Package Availability
              </span>
            </AnchorHeading>
            
            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;Is codename goose available in nix packages for mac?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for Goose Packages">
                <CodeBlock
                  code={`{
  "ctx": "Checking if codename goose is available in NixOS packages",
  "type": "packages",
  "limit": 10,
  "query": "goose"
}
Found 5 packages matching 'goose':

- goose (3.24.2)
  Database migration tool which supports SQL migrations and Go functions

- goose-lang (0.9.2)
  Goose converts a small subset of Go to Coq

- goose-cli (1.0.15)
  Open-source, extensible AI agent that goes beyond code suggestions - install, execute, edit, and test with any LLM

- emacsPackages.goose-theme (20160828.1245)

- mongoose (3.3.4)
  Graph Coarsening and Partitioning Library`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get Detailed Information About goose-cli">
                <CodeBlock
                  code={`{
  "ctx": "Checking detailed information about goose-cli",
  "type": "package",
  "name": "goose-cli"
}
# goose-cli

**Version:** 1.0.15

**Description:** Open-source, extensible AI agent that goes beyond code suggestions - install, execute, edit, and test with any LLM

**Homepage:** https://github.com/block/goose

**License:** Apache License 2.0

**Source:** [pkgs/by-name/go/goose-cli/package.nix:75](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/go/goose-cli/package.nix#L75)

**Maintainers:** cloudripper

**Platforms:** armv7a-linux, riscv32-linux, i686-linux, i686-darwin, powerpc64le-linux, riscv64-linux, x86_64-darwin, m68k-linux, aarch64-darwin, mipsel-linux, loongarch64-linux, armv6l-linux, s390x-linux, mips64-linux, armv7a-darwin, aarch64-linux, armv7l-linux, powerpc64-linux, mips-linux, x86_64-linux, mips64el-linux, armv5tel-linux`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 3: Search for Exact Package Name">
                <CodeBlock
                  code={`{
  "ctx": "Checking for a package named 'codename goose'",
  "type": "packages",
  "limit": 5,
  "query": "codename goose"
}
Found 1 packages matching 'codename goose':

- goose-lang (0.9.2)
  Goose converts a small subset of Go to Coq`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 4: Check Platform Compatibility for goose-lang">
                <CodeBlock
                  code={`{
  "ctx": "Checking detailed information about goose-lang",
  "type": "package",
  "name": "goose-lang"
}
# goose-lang

**Version:** 0.9.2

**Description:** Goose converts a small subset of Go to Coq

**Homepage:** https://github.com/goose-lang/goose

**License:** MIT License

**Source:** [pkgs/by-name/go/goose-lang/package.nix:26](https://github.com/NixOS/nixpkgs/blob/master/pkgs/by-name/go/goose-lang/package.nix#L26)

**Maintainers:** Yifei Sun

**Platforms:** wasm32-wasi, armv7l-linux, microblazeel-linux, i686-freebsd, s390x-linux, riscv64-linux, riscv32-linux, armv7a-darwin, i686-linux, armv7a-linux, x86_64-darwin, m68k-linux, mips-linux, s390-linux, x86_64-freebsd, mips64el-linux, mips64-linux, aarch64-linux, loongarch64-linux, mipsel-linux, i686-darwin, x86_64-linux, aarch64-freebsd, microblaze-linux, powerpc64le-linux, aarch64-darwin, armv5tel-linux, powerpc64-linux, wasm64-wasi, armv6l-linux

**Provided Programs:** goose, test_gen`}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  While there isn&apos;t a package specifically named &quot;codename goose&quot;, I found two relevant packages that might match what you&apos;re looking for:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    <code className="font-mono text-xs">goose-cli</code> (v1.0.15) - An open-source AI agent for coding tasks
                  </li>
                  <li>
                    <code className="font-mono text-xs">goose-lang</code> (v0.9.2) - A tool that converts Go code to Coq
                  </li>
                </ul>
                <p className="text-gray-700 mt-2">
                  Both packages are available for macOS, as indicated by the platform identifiers in their metadata:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    <code className="font-mono text-xs">x86_64-darwin</code> - Intel-based Macs
                  </li>
                  <li>
                    <code className="font-mono text-xs">aarch64-darwin</code> - Apple Silicon Macs (M1/M2/M3)
                  </li>
                </ul>
                <p className="text-gray-700 mt-2">
                  If you&apos;re looking for the AI coding assistant called &quot;Goose&quot;, the <code className="font-mono text-xs">goose-cli</code> package is likely what you want. You can install it on your Mac using:
                </p>
                <CodeBlock
                  code={`nix-env -iA nixpkgs.goose-cli  # For global installation

# Or in a development shell
nix-shell -p goose-cli`}
                  language="bash"
                />
              </div>
            </div>

            <AnchorHeading level={3} className="text-xl font-semibold text-nix-dark mb-3">
              <span className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 5: macOS Configuration with nix-darwin
              </span>
            </AnchorHeading>
            
            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;What all can be configured on macOS when using nix?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: List nix-darwin Option Categories">
                <CodeBlock
                  code={`{
  "ctx": "Exploring nix-darwin configuration options"
}
## nix-darwin Option Categories
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
- **Usage:** \`darwin.users\``}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Explore System Defaults Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking system defaults configuration options",
  "option_prefix": "system.defaults"
}
## nix-darwin options with prefix 'system.defaults'
Found 183 options.

### system.defaults.ActivityMonitor.IconType
Change the icon in the dock when running. 0: Application Icon 2: Network Usage 3: Disk Activity 5...
**Type:** \`null\`

### system.defaults.CustomSystemPreferences
Sets custom system preferences Type: plist value Default: { } Example: {
  NSGlobalDomain = {
   ...
**Type:** \`plist\`

### system.defaults.LaunchServices.LSQuarantine
Whether to enable quarantine for downloaded applications.  The default is true. Type: null or boo...
**Type:** \`null\`

### system.defaults.NSGlobalDomain.AppleHighlightColor
Highlight color as a string in the format of red green blue alpha (all between 0.0 and 1.0). Type...
**Type:** \`null\`

### system.defaults.NSGlobalDomain.AppleInterfaceStyle
Sets interface style to Dark or null for not set/Light. Type: null or string Default: null Examp...
**Type:** \`null\`

### system.defaults.NSGlobalDomain.AppleKeyboardUIMode
Enables full keyboard control of UI.  Mode 3 enables Tab to navigate to all controls. Mode 2 is T...
**Type:** \`null\`

### system.defaults.dock.autohide
Whether to automatically hide and show the dock.  The default is false. Type: null or boolean De...
**Type:** \`null\`

### system.defaults.dock.orientation
Position of the dock on screen.  The default is "bottom". Type: null or string Default: null Exa...
**Type:** \`null\`

### system.defaults.finder.AppleShowAllExtensions
Whether to always show file extensions.  The default is false. Type: null or boolean Default: nu...
**Type:** \`null\`

### system.defaults.finder.ShowPathbar
Whether to show path bar.  The default is false. Type: null or boolean Default: null Declared by...
**Type:** \`null\`

### system.defaults.trackpad.Clicking
Whether to enable tap to click.  The default is false. Type: null or boolean Default: null Decla...
**Type:** \`null\`

### system.defaults.trackpad.TrackpadThreeFingerDrag
Whether to enable three finger drag.  The default is false. Type: null or boolean Default: null ...
**Type:** \`null\`

### system.defaults.universalaccess.reduceTransparency
Disable transparency in the menu bar and elsewhere.
The default is false. Type: null or boolean D...
**Type:** \`null\``}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 3: Explore Homebrew Integration Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking Homebrew integration options",
  "option_prefix": "homebrew"
}
## nix-darwin options with prefix 'homebrew'
Found 49 options.

### homebrew.brewPrefix
The path prefix where the brew executable is located. This will be set to
the correct value based...
**Type:** \`string\`

### homebrew.brews
List of Homebrew formulae to install. Formulae defined as strings, e.g., "imagemagick" , are a sh...
**Type:** \`list\`

### homebrew.casks
List of Homebrew casks to install. Casks defined as strings, e.g., "firefox" , are a shorthand fo...
**Type:** \`list\`

### homebrew.enable
Whether to enable Homebrew integration. This option only has an effect on macOS. Type: boolean De...
**Type:** \`boolean\`

### homebrew.global.brewfile
Whether to generate a global Brewfile at /etc/brewfile. Type: boolean Default: true Declared by:...
**Type:** \`boolean\`

### homebrew.masApps
List of Mac App Store apps to install. The app IDs can be found in the URL of the app in the Mac ...
**Type:** \`attribute\`

### homebrew.onActivation.autoUpdate
Whether to enable Homebrew to auto-update itself and all formulae during nix-darwin system activa...
**Type:** \`boolean\`

### homebrew.onActivation.cleanup
This option manages what happens to formulae installed by Homebrew, that aren't present in
the Br...
**Type:** \`one\`

### homebrew.taps
List of Homebrew formula repositories to tap. Taps defined as strings, e.g., "user/repo" , are a ...
**Type:** \`list\``}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 4: Explore Window Manager and Services Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking window manager and services options",
  "option_prefix": "services"
}
## nix-darwin options with prefix 'services'
Found 297 options.

### services.aerospace.enable
Whether to enable AeroSpace window manager. Type: boolean Default: false Example: true Declared b...
**Type:** \`boolean\`

### services.aerospace.settings
AeroSpace configuration, see
<link xlink:href="https://nikitabobko.github.io/AeroSpace/guide#conf...
**Type:** \`TOML\`

### services.karabiner.enable
Whether to enable Karabiner-Elements. Type: boolean Default: false Declared by: <nix-darwin/modu...
**Type:** \`boolean\`

### services.postgresql.enable
Whether to enable PostgreSQL Server. Type: boolean Default: false Declared by: <nix-darwin/modul...
**Type:** \`boolean\`

### services.postgresql.package
Postgres package to use. Type: package Default: pkgs.postgresql_15 Example: pkgs.postgresql_14 De...
**Type:** \`package\`

### services.redis.enable
Whether to enable Redis server. Type: boolean Default: false Declared by: <nix-darwin/modules/se...
**Type:** \`boolean\`

### services.sketchybar.enable
Whether to enable the sketchybar status bar. Type: boolean Default: false Declared by: <nix-darw...
**Type:** \`boolean\`

### services.skhd.enable
Whether to enable the skhd hotkey daemon. Type: boolean Default: false Declared by: <nix-darwin/...
**Type:** \`boolean\`

### services.yabai.enable
Whether to enable the yabai window manager. Type: boolean Default: false Declared by: <nix-darwin...
**Type:** \`boolean\`

### services.yabai.enableScriptingAddition
Whether to enable yabai's scripting-addition.
SIP must be disabled for this to work. Type: boolea...
**Type:** \`boolean\``}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  nix-darwin provides extensive configuration options for macOS, allowing you to manage your system declaratively. Here&apos;s a comprehensive overview of what you can configure:
                </p>
                
                <h6 className="font-semibold text-nix-dark mt-3 mb-1">System Configuration</h6>
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                  <li>
                    <strong>System Defaults</strong>: Appearance (dark mode, accent colors), Dock behavior, Mission Control, keyboard/trackpad settings, Finder preferences, security settings
                  </li>
                  <li>
                    <strong>Window Managers</strong>: Configure tiling window managers like yabai, AeroSpace, and Amethyst
                  </li>
                  <li>
                    <strong>Networking</strong>: Hostname, DNS settings, WireGuard interfaces, firewall rules
                  </li>
                </ul>

                <h6 className="font-semibold text-nix-dark mt-3 mb-1">Package Management</h6>
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                  <li>
                    <strong>Homebrew Integration</strong>: Install command-line tools (<code className="font-mono text-xs">brews</code>), GUI applications (<code className="font-mono text-xs">casks</code>), App Store apps (<code className="font-mono text-xs">masApps</code>)
                  </li>
                  <li>
                    <strong>Nix Packages</strong>: System-wide and per-user packages, package overlays
                  </li>
                </ul>

                <h6 className="font-semibold text-nix-dark mt-3 mb-1">Shell Environment</h6>
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                  <li>
                    <strong>Shell Configuration</strong>: Bash, Zsh, Fish with customizations for prompts, completions, and plugins
                  </li>
                  <li>
                    <strong>Environment Variables</strong>: System-wide and shell-specific variables, PATH modifications
                  </li>
                </ul>

                <h6 className="font-semibold text-nix-dark mt-3 mb-1">System Services</h6>
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                  <li>
                    <strong>Application Services</strong>: Databases (PostgreSQL, MySQL, Redis), web servers, development tools
                  </li>
                  <li>
                    <strong>macOS Specific</strong>: Fonts, launchd services, Spotlight configuration, Time Machine settings
                  </li>
                </ul>

                <p className="text-gray-700 mt-3">
                  Here&apos;s a simple example configuration for customizing macOS with nix-darwin:
                </p>

                <CodeBlock
                  code={`{ config, pkgs, ... }:

{
  # System defaults
  system.defaults.NSGlobalDomain = {
    AppleInterfaceStyle = "Dark";       # Enable dark mode
    AppleShowScrollBars = "Always";    # Always show scrollbars
    NSAutomaticSpellingCorrectionEnabled = false;
  };
  
  system.defaults.dock = {
    autohide = true;                   # Auto-hide the dock
    orientation = "left";              # Position dock on the left
    tilesize = 48;                     # Icon size
  };
  
  # Homebrew packages
  homebrew = {
    enable = true;
    onActivation.autoUpdate = true;
    casks = [ "firefox" "visual-studio-code" "iterm2" ];
    brews = [ "ripgrep" "fd" "jq" ];
  };
  
  # Shell configuration
  programs.zsh = {
    enable = true;
    enableCompletion = true;
    enableSyntaxHighlighting = true;
  };
  
  # System packages
  environment.systemPackages = with pkgs; [
    git
    neovim
    tmux
    htop
  ];
  
  # Window manager
  services.yabai = {
    enable = true;
    config = {
      layout = "bsp";
      window_gap = 10;
    };
  };
}`}
                  language="nix"
                />
                
                <p className="text-gray-700 mt-3">
                  This configuration can be applied by adding it to your <code className="font-mono text-xs">~/.nixpkgs/darwin-configuration.nix</code> file and running <code className="font-mono text-xs">darwin-rebuild switch</code>. The changes will be applied immediately and persist across reboots, giving you a consistent, reproducible macOS environment.
                </p>
              </div>
            </div>
          </div>
          
          {/* Finding Package Versions Example */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <div className="flex items-center mb-4">
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                className="h-6 w-6 mr-2 text-nix-primary" 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <AnchorHeading 
                level={3} 
                className="text-xl font-bold text-nix-dark"
              >
                Finding Specific Package Versions
              </AnchorHeading>
            </div>
            
            <div className="flex items-center mb-3">
              <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
              </svg>
              <p className="text-md font-semibold text-nix-primary">User Request</p>
            </div>
            
            <p className="text-gray-700 pl-6 mb-4">
              I need to install Ruby 2.6.7 for a legacy project. Can you help me find the right nixpkgs commit?
            </p>
            
            <CollapsibleSection
              title="Tool Calls"
            >
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixhub_find_version",
  "params": {
    "package_name": "ruby",
    "version": "2.6.7"
  }
}`}
                language="json"
              />
            </CollapsibleSection>
            
            <CollapsibleSection
              title="Response"
            >
              <div className="text-gray-700">
                <p className="mb-3">
                  I found Ruby 2.6.7 for you! Here&apos;s how to install it:
                </p>
                
                <CodeBlock
                  code={`# Install Ruby 2.6.7 using the specific nixpkgs commit
nix build nixpkgs#ruby_2_6 --override-input nixpkgs github:NixOS/nixpkgs/86752e44440dfcd17f53d08fc117bd96c8bac144

# Or add to your flake.nix:
{
  inputs.nixpkgs-ruby26.url = "github:NixOS/nixpkgs/86752e44440dfcd17f53d08fc117bd96c8bac144";
  
  # Then use it as:
  # nixpkgs-ruby26.legacyPackages.\${system}.ruby_2_6
}`}
                  language="bash"
                />
                
                <p className="mt-3">
                  <strong>Version Details:</strong>
                </p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Version: 2.6.7</li>
                  <li>Date: 2021-04-09</li>
                  <li>Platforms: aarch64-linux, i686-linux, x86_64-darwin, x86_64-linux</li>
                  <li>Attribute: ruby_2_6</li>
                  <li>Commit: <code className="font-mono text-xs">86752e44440dfcd17f53d08fc117bd96c8bac144</code></li>
                </ul>
                
                <p className="mt-3">
                  This gives you a reproducible way to install exactly Ruby 2.6.7, ensuring your legacy project has the exact version it needs.
                </p>
              </div>
            </CollapsibleSection>
          </div>
        </div>
      </div>
    </div>
  );
}
