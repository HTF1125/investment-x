'use client';

import React from 'react';
import CustomChartEditor from '@/components/CustomChartEditor';
import AuthGuard from '@/components/AuthGuard';
import Navbar from '@/components/Navbar';

export default function StudioPage() {
  return (
    <AuthGuard>
      {/* Full-viewport layout: Navbar is fixed, editor fills remaining space */}
      <main className="h-screen w-screen overflow-hidden bg-black">
        <Navbar />
        <CustomChartEditor />
      </main>
    </AuthGuard>
  );
}
