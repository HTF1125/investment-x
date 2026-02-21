'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

/**
 * Shared application shell providing the fixed Navbar and
 * a content area with correct top-padding to avoid overlap.
 */
export default function AppShell({
  children,
  hideFooter = false,
}: {
  children: React.ReactNode;
  hideFooter?: boolean;
}) {
  return (
    <main className="min-h-screen flex flex-col relative overflow-x-hidden">
      <Navbar />
      {/* Match fixed navbar height (h-12) with minimal extra offset */}
      <div className="pt-12 flex-grow">
        {children}
      </div>
      {!hideFooter && <Footer />}
    </main>
  );
}
