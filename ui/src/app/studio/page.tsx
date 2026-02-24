'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, Lock } from 'lucide-react';

import AppShell from '@/components/AppShell';
import CustomChartEditor from '@/components/CustomChartEditor';
import { useAuth } from '@/context/AuthContext';

export default function StudioPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated, loading } = useAuth();

  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const canUseStudio = !!user && (isOwner || (!isAdminRole && role === 'general'));

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (loading || (!isAuthenticated && !loading)) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-3rem)] flex items-center justify-center text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading studio...
        </div>
      </AppShell>
    );
  }

  if (!canUseStudio) {
    return (
      <AppShell hideFooter>
        <div className="h-[calc(100vh-3rem)] flex items-center justify-center px-4">
          <div className="max-w-md w-full rounded-xl border border-border/60 bg-card/30 p-6 text-center">
            <div className="mx-auto mb-3 w-10 h-10 rounded-lg border border-border/50 flex items-center justify-center">
              <Lock className="w-5 h-5 text-muted-foreground" />
            </div>
            <h1 className="text-sm font-semibold text-foreground">Studio Access Restricted</h1>
            <p className="mt-2 text-xs text-muted-foreground">
              Studio is available to owner and general users.
            </p>
            <Link
              href="/"
              className="mt-4 inline-flex h-8 items-center rounded-md border border-border/50 px-3 text-xs text-muted-foreground hover:text-foreground"
            >
              Return to Dashboard
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  const chartId = (searchParams.get('chartId') || '').trim() || null;

  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-3rem)] w-full overflow-hidden">
        <CustomChartEditor mode="standalone" initialChartId={chartId} />
      </div>
    </AppShell>
  );
}

