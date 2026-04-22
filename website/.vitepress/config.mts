import { defineConfig } from 'vitepress';

const siteUrl = 'https://mcp-nixos.io';

export default defineConfig({
  lang: 'en-US',
  title: 'MCP-NixOS',
  description:
    'Model Context Protocol server for NixOS, Home Manager, nix-darwin, and flakes. Stops AI assistants from hallucinating NixOS package names.',
  cleanUrls: true,
  lastUpdated: true,
  sitemap: {
    hostname: siteUrl,
  },
  outDir: 'out',
  srcExclude: ['**/README.md', 'public/**', 'out/**', '.vitepress/dist/**'],

  head: [
    ['link', { rel: 'icon', href: '/favicon/favicon.ico' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon/favicon-16x16.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon/favicon-32x32.png' }],
    ['link', { rel: 'apple-touch-icon', href: '/favicon/apple-touch-icon.png' }],
    ['link', { rel: 'manifest', href: '/favicon/site.webmanifest' }],
    ['meta', { name: 'theme-color', content: '#5277c3' }],
    ['meta', { name: 'author', content: 'Utensils' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:url', content: siteUrl }],
    ['meta', { property: 'og:site_name', content: 'MCP-NixOS' }],
    ['meta', { property: 'og:title', content: 'MCP-NixOS | Model Context Protocol for NixOS' }],
    [
      'meta',
      {
        property: 'og:description',
        content:
          'MCP resources and tools for NixOS packages, options, Home Manager, and nix-darwin. Real answers, no hallucinations.',
      },
    ],
    ['meta', { property: 'og:image', content: `${siteUrl}/images/og-image.png` }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:creator', content: '@utensils_io' }],
    ['meta', { name: 'twitter:image', content: `${siteUrl}/images/og-image.png` }],
  ],

  themeConfig: {
    logo: '/images/nixos-snowflake-colour.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Usage', link: '/usage' },
      { text: 'About', link: '/about' },
      {
        text: 'Resources',
        items: [
          { text: 'GitHub', link: 'https://github.com/utensils/mcp-nixos' },
          { text: 'PyPI', link: 'https://pypi.org/project/mcp-nixos/' },
          { text: 'FlakeHub', link: 'https://flakehub.com/flake/utensils/mcp-nixos' },
          { text: 'Docker Hub', link: 'https://hub.docker.com/r/utensils/mcp-nixos' },
        ],
      },
    ],

    sidebar: {
      '/usage': [
        {
          text: 'Usage',
          items: [
            { text: 'Pick Your Poison', link: '/usage#pick-your-poison' },
            { text: 'uvx (Recommended)', link: '/usage#option-1-uvx' },
            { text: 'Nix', link: '/usage#option-2-nix' },
            { text: 'Declarative Nix', link: '/usage#option-2b-declarative-nix' },
            { text: 'Docker', link: '/usage#option-3-docker' },
            { text: 'HTTP Transport', link: '/usage#option-4-http-transport' },
            { text: 'Pi Coding Agent', link: '/usage#option-5-pi-coding-agent' },
          ],
        },
        {
          text: 'Tools',
          items: [
            { text: 'nix — Unified Query', link: '/usage#the-nix-tool' },
            { text: 'nix_versions', link: '/usage#the-nix-versions-tool' },
            { text: 'Binary Cache & NixHub', link: '/usage#binary-cache-nixhub' },
          ],
        },
        {
          text: 'Reference',
          items: [
            { text: 'Environment Variables', link: '/usage#environment-variables' },
            { text: 'What Happens Next?', link: '/usage#what-happens-next' },
          ],
        },
      ],
      '/about': [
        {
          text: 'About',
          items: [
            { text: 'Project Overview', link: '/about#project-overview' },
            { text: 'Architecture', link: '/about#architecture' },
            { text: 'Features', link: '/about#features' },
            { text: 'What is MCP?', link: '/about#what-is-model-context-protocol' },
            { text: 'Authors', link: '/about#authors' },
            { text: 'Contributing', link: '/about#contributing' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/utensils/mcp-nixos' },
      { icon: 'twitter', link: 'https://twitter.com/utensils_io' },
    ],

    editLink: {
      pattern: 'https://github.com/utensils/mcp-nixos/edit/main/website/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message:
        'Released under the MIT License. A <a href="https://utensils.io" target="_blank" rel="noopener">Utensils</a> creation.',
      copyright: `© 2024–${new Date().getFullYear()} MCP-NixOS contributors.`,
    },

    search: {
      provider: 'local',
    },

    outline: {
      level: [2, 3],
      label: 'On this page',
    },
  },
});
