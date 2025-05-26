"use client";

import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language: string;
  showLineNumbers?: boolean;
}

// Create a custom theme based on NixOS colors
const nixosTheme = {
  ...atomDark,
  'pre[class*="language-"]': {
    ...atomDark['pre[class*="language-"]'],
    background: '#1C3E5A', // nix-dark
    margin: 0,
    padding: '1rem',
    fontSize: '0.875rem',
    fontFamily: '"Fira Code", Menlo, Monaco, Consolas, "Courier New", monospace',
  },
  'code[class*="language-"]': {
    ...atomDark['code[class*="language-"]'],
    color: '#E6F0FA', // nix-light - base text color
    textShadow: 'none',
    fontFamily: '"Fira Code", Menlo, Monaco, Consolas, "Courier New", monospace',
  },
  punctuation: {
    color: '#BBDEFB', // Lighter blue for better contrast
  },
  comment: {
    color: '#78909C', // Muted blue-gray for comments
  },
  string: {
    color: '#B9F6CA', // Brighter green for strings
  },
  keyword: {
    color: '#CE93D8', // Brighter purple for keywords
  },
  number: {
    color: '#FFCC80', // Brighter orange for numbers
  },
  function: {
    color: '#90CAF9', // Brighter blue for functions
  },
  operator: {
    color: '#E1F5FE', // Very light blue for operators
  },
  property: {
    color: '#90CAF9', // Brighter blue for properties
  },
  // Additional token types for better coverage
  boolean: {
    color: '#FFCC80', // Same as numbers
  },
  className: {
    color: '#90CAF9', // Same as functions
  },
  tag: {
    color: '#CE93D8', // Same as keywords
  },
};



// Helper function to decode HTML entities
function decodeHtmlEntities(text: string): string {
  const textArea = document.createElement('textarea');
  textArea.innerHTML = text;
  return textArea.value;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ 
  code, 
  language,
  showLineNumbers = false
}) => {
  const [copied, setCopied] = useState(false);
  
  // Decode HTML entities in the code
  const decodedCode = typeof window !== 'undefined' ? decodeHtmlEntities(code) : code;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code to clipboard:', error);
      // Fallback method for browsers with restricted clipboard access
      const textArea = document.createElement('textarea');
      textArea.value = code;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        const successful = document.execCommand('copy');
        if (successful) {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } else {
          console.error('Fallback clipboard copy failed');
        }
      } catch (err) {
        console.error('Fallback clipboard copy error:', err);
      }
      
      document.body.removeChild(textArea);
    }
  };

  // Map common language identifiers to ones supported by react-syntax-highlighter
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'ts': 'typescript',
    'jsx': 'jsx',
    'tsx': 'tsx',
    'py': 'python',
    'rb': 'ruby',
    'go': 'go',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'cs': 'csharp',
    'php': 'php',
    'sh': 'bash',
    'yaml': 'yaml',
    'yml': 'yaml',
    'json': 'json',
    'md': 'markdown',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sql': 'sql',
    'nix': 'nix',
  };

  const mappedLanguage = languageMap[language.toLowerCase()] || language;

  return (
    <div className="rounded-lg overflow-hidden shadow-md mb-6">
      <div className="flex justify-between items-center bg-nix-primary px-4 py-2 text-xs text-white font-medium">
        <span className="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          {language}
        </span>
        <button 
          onClick={handleCopy}
          className="text-white hover:text-nix-secondary transition-colors duration-200"
          aria-label="Copy code"
        >
          {copied ? (
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span>Copied!</span>
            </div>
          ) : (
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>Copy</span>
            </div>
          )}
        </button>
      </div>
      <SyntaxHighlighter 
        language={mappedLanguage} 
        style={nixosTheme}
        showLineNumbers={showLineNumbers}
        wrapLongLines={true}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: '#1C3E5A', // Ensure consistent background
        }}
        codeTagProps={{
          style: {
            fontFamily: '"Fira Code", Menlo, Monaco, Consolas, "Courier New", monospace',
            fontSize: '0.875rem',
          }
        }}
      >
        {decodedCode}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeBlock;