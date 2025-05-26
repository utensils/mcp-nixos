'use client';

import React, { useEffect } from 'react';

interface AnchorHeadingProps {
  level: 1 | 2 | 3 | 4 | 5 | 6;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

const AnchorHeading: React.FC<AnchorHeadingProps> = ({ 
  level, 
  children, 
  className = '',
  id
}) => {
  
  // Extract text content for ID generation
  const extractTextContent = (node: React.ReactNode): string => {
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(extractTextContent).join(' ');
    if (React.isValidElement(node)) {
      const childContent = React.Children.toArray(node.props.children);
      return extractTextContent(childContent);
    }
    return '';
  };

  // Generate an ID from the children if none is provided
  const textContent = extractTextContent(children);
  const headingId = id || (textContent
    ? textContent.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '')
    : `heading-${Math.random().toString(36).substring(2, 9)}`);
  
  const handleAnchorClick = (e: React.MouseEvent) => {
    e.preventDefault();
    const hash = `#${headingId}`;
    
    // Update URL without page reload
    window.history.pushState(null, '', hash);
    
    // Scroll to the element
    const element = document.getElementById(headingId);
    if (element) {
      // Smooth scroll to the element
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };
  
  // Handle initial load with hash in URL
  useEffect(() => {
    // Check if the current URL hash matches this heading
    if (typeof window !== 'undefined' && window.location.hash === `#${headingId}`) {
      // Add a small delay to ensure the page has fully loaded
      setTimeout(() => {
        const element = document.getElementById(headingId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }, [headingId]);

  const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
  
  // Check if the heading has text-center class
  const isCentered = className.includes('text-center');
  
  return (
    <HeadingTag id={headingId} className={`group relative ${className} scroll-mt-16`}>
      {isCentered ? (
        <div className="relative inline-flex items-center">
          {level !== 1 && (
            <a
              href={`#${headingId}`}
              onClick={handleAnchorClick}
              className="absolute -left-5 opacity-0 group-hover:opacity-100 transition-opacity text-nix-primary hover:text-nix-dark font-semibold"
              aria-label={`Link to ${textContent || 'this heading'}`}
            >
              #
            </a>
          )}
          {children}
        </div>
      ) : (
        <>
          {level !== 1 && (
            <a
              href={`#${headingId}`}
              onClick={handleAnchorClick}
              className="absolute -left-5 opacity-0 group-hover:opacity-100 transition-opacity text-nix-primary hover:text-nix-dark font-semibold"
              aria-label={`Link to ${textContent || 'this heading'}`}
            >
              #
            </a>
          )}
          {children}
        </>
      )}
    </HeadingTag>
  );
};

export default AnchorHeading;
