'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

/**
 * Shared application shell providing the fixed Navbar and
 * a content area with correct top-padding to avoid overlap.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen flex flex-col relative overflow-x-hidden">
      <Navbar />
      {/* pt-14 = 56px matches the navbar h-12 + breathing room */}
      <div className="pt-20 flex-grow">
        {children}
      </div>
      <Footer />
    </main>
  );
}
