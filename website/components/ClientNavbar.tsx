"use client";

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function ClientNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);
  const closeMenu = () => setIsMenuOpen(false);

  return (
    <nav className="bg-white shadow-md">
      <div className="container-custom mx-auto py-4">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <Image 
              src="/images/nixos-snowflake-colour.svg" 
              alt="NixOS Snowflake" 
              width={32} 
              height={32} 
              className="h-8 w-8"
            />
            <Link href="/" className="text-2xl font-bold text-nix-primary">
              MCP-NixOS
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex space-x-8">
            <Link href="/" className="text-gray-700 hover:text-nix-primary">
              Home
            </Link>
            <Link href="/usage" className="text-gray-700 hover:text-nix-primary">
              Usage
            </Link>
            <Link href="/docs" className="text-gray-700 hover:text-nix-primary">
              Documentation
            </Link>
            <Link href="/about" className="text-gray-700 hover:text-nix-primary">
              About
            </Link>
            <Link 
              href="https://github.com/utensils/mcp-nixos" 
              className="text-gray-700 hover:text-nix-primary"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={toggleMenu}
              className="text-gray-500 hover:text-nix-primary focus:outline-none"
              aria-label="Toggle menu"
            >
              {isMenuOpen ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden mt-4 pb-2">
            <div className="flex flex-col space-y-4">
              <Link
                href="/"
                className="text-gray-700 hover:text-nix-primary"
                onClick={closeMenu}
              >
                Home
              </Link>
              <Link
                href="/usage"
                className="text-gray-700 hover:text-nix-primary"
                onClick={closeMenu}
              >
                Usage
              </Link>
              <Link
                href="/docs"
                className="text-gray-700 hover:text-nix-primary"
                onClick={closeMenu}
              >
                Documentation
              </Link>
              <Link
                href="/about"
                className="text-gray-700 hover:text-nix-primary"
                onClick={closeMenu}
              >
                About
              </Link>
              <Link
                href="https://github.com/utensils/mcp-nixos"
                className="text-gray-700 hover:text-nix-primary"
                target="_blank"
                rel="noopener noreferrer"
                onClick={closeMenu}
              >
                GitHub
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}