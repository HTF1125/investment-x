'use client';

import AppShell from '@/components/AppShell';
import Scorecards from '@/components/dashboard/Scorecards';
import { useEffect } from 'react';

export default function Home() {
  useEffect(() => {
    document.title = 'Dashboard | Investment-X';
  }, []);

  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-48px)] flex flex-col bg-background">
        <Scorecards />
      </div>
    </AppShell>
  );
}
