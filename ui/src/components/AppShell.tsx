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
    <main className="min-h-screen flex flex-col relative overflow-x-hidden bg-background">
      {/* Ambient background gradient — subtle, works in both themes */}
      <div className="pointer-events-none fixed inset-0 z-[-1]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_-10%,rgba(120,119,198,0.07),transparent)] dark:bg-[radial-gradient(ellipse_70%_60%_at_50%_-10%,rgba(120,119,198,0.06),transparent)]" />
      </div>

      <Navbar />
      {/* Match fixed navbar height (40px) */}
      <div className="pt-[40px] flex-grow relative z-0">
        {children}
      </div>
      {!hideFooter && <Footer />}
    </main>
  );
}
