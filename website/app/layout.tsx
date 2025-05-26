import type { Metadata, Viewport } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'MCP-NixOS | Model Context Protocol for NixOS',
  description: 'MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration.',
  keywords: ['NixOS', 'MCP', 'Model Context Protocol', 'Home Manager', 'nix-darwin', 'Claude', 'AI Assistant'],
  authors: [{ name: 'Utensils', url: 'https://utensils.io' }],
  creator: 'Utensils',
  publisher: 'Utensils',
  metadataBase: new URL('https://mcp-nixos.io'),
  alternates: {
    canonical: '/',
  },
  // Open Graph metadata
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://mcp-nixos.io',
    siteName: 'MCP-NixOS',
    title: 'MCP-NixOS | Model Context Protocol for NixOS',
    description: 'MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration.',
    images: [
      {
        url: '/images/og-image.png',
        width: 1200,
        height: 630,
        alt: 'MCP-NixOS - Model Context Protocol for NixOS',
      },
    ],
  },
  // Twitter Card metadata
  twitter: {
    card: 'summary_large_image',
    title: 'MCP-NixOS | Model Context Protocol for NixOS',
    description: 'MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration.',
    images: ['/images/og-image.png'],
    creator: '@utensils_io',
  },
  icons: {
    icon: [
      { url: '/favicon/favicon.ico' },
      { url: '/favicon/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon/favicon-32x32.png', sizes: '32x32', type: 'image/png' }
    ],
    apple: [
      { url: '/favicon/apple-touch-icon.png' }
    ],
    other: [
      {
        rel: 'mask-icon',
        url: '/favicon/safari-pinned-tab.svg',
        color: '#5277c3'
      }
    ]
  },
  manifest: '/favicon/site.webmanifest',
};

export const viewport: Viewport = {
  themeColor: '#5277c3',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-grow">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}