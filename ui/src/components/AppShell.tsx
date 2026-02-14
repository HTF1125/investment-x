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
      {/* pt-20 = 80px matches the navbar h-16 + 16px breathing room */}
      <div className="pt-20">
        {children}
      </div>
    </main>
  );
}
