'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Navbar from '@/components/layout/Navbar';
import Footer from '@/components/layout/Footer';
import GlobalSearchPalette from '@/components/shared/GlobalSearchPalette';

/**
 * Shared application shell providing the fixed Navbar and
 * a content area with correct top-padding to avoid overlap.
 * Manages global Ctrl+K search palette.
 */
export default function AppShell({
  children,
  hideFooter = false,
  fullWidth = false,
}: {
  children: React.ReactNode;
  hideFooter?: boolean;
  fullWidth?: boolean;
}) {
  const [searchOpen, setSearchOpen] = useState(false);

  const openSearch = useCallback(() => setSearchOpen(true), []);
  const closeSearch = useCallback(() => setSearchOpen(false), []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="min-h-screen flex flex-col relative overflow-x-clip bg-background">
      <Navbar onOpenSearch={openSearch} />
      {/* Match fixed navbar height (56px) */}
      <main id="main-content" className={`pt-[56px] flex-grow relative w-full ${fullWidth ? '' : 'max-w-[1600px] mx-auto'}`}>
        {children}
      </main>
      {!hideFooter && <Footer />}

      <GlobalSearchPalette isOpen={searchOpen} onClose={closeSearch} />
    </div>
  );
}
