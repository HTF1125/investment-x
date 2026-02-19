'use client';

import React from 'react';
import Navbar from '@/components/Navbar';

/**
 * Shared application shell providing the fixed Navbar and
 * a content area with correct top-padding to avoid overlap.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-black">
      <Navbar />
      {/* pt-14 = 56px matches the navbar h-12 + breathing room */}
      <div className="pt-14">
        {children}
      </div>
    </main>
  );
}
