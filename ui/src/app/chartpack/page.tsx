'use client';

import React, { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';
import { Check, X, AlertTriangle, Loader2 } from 'lucide-react';
import PackListView from '@/components/chartpack/PackListView';
import PackDetailView from '@/components/chartpack/PackDetailView';
import type { PackSummary, PackDetail, FlashMessage } from '@/components/chartpack/types';

// ── Flash Toast ──

function FlashToast({ flash, onDismiss }: { flash: FlashMessage; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500);
    return () => clearTimeout(t);
  }, [flash, onDismiss]);

  const isError = flash.type === 'error';
  return (
    <div className="fixed bottom-4 right-4 z-[70] animate-fade-in">
      <div className={`flex items-center gap-2 px-3.5 py-2 rounded-[var(--radius)] shadow-lg border text-[12.5px] font-medium ${
        isError
          ? 'bg-destructive/10 border-destructive/25 text-destructive'
          : 'bg-success/10 border-success/25 text-success'
      }`}>
        {isError ? <AlertTriangle className="w-3 h-3 shrink-0" /> : <Check className="w-3 h-3 shrink-0" />}
        <span>{flash.text}</span>
        <button onClick={onDismiss} className="ml-1 opacity-50 hover:opacity-100 transition-opacity">
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ── Main Page ──

function ChartPacksPageInner() {
  const { theme } = useTheme();
  const isLight = theme === 'light';
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const activePackId = searchParams.get('chartpack') || null;
  const setActivePackId = useCallback((id: string | null) => {
    if (id) {
      router.push(`/chartpack?chartpack=${id}`);
    } else {
      router.push('/chartpack');
    }
  }, [router]);

  const [flash, setFlash] = useState<FlashMessage | null>(null);
  const handleFlash = useCallback((msg: FlashMessage) => setFlash(msg), []);
  const dismissFlash = useCallback(() => setFlash(null), []);

  // ── Queries ──

  const { data: packs, refetch: refetchPacks, isLoading: packsLoading, isError: packsError } = useQuery({
    queryKey: ['chart-packs'],
    queryFn: () => apiFetchJson<PackSummary[]>('/api/chart-packs'),
    staleTime: 30_000,
    enabled: !!user,
  });

  const { data: publishedPacks, refetch: refetchPublished, isError: publishedError } = useQuery({
    queryKey: ['chart-packs-published'],
    queryFn: () => apiFetchJson<PackSummary[]>('/api/chart-packs/published'),
    staleTime: 30_000,
  });

  const { data: activePack, refetch: refetchPack, isLoading: isPackLoading, isError: packError } = useQuery({
    queryKey: ['chart-pack', activePackId],
    queryFn: () => apiFetchJson<PackDetail>(`/api/chart-packs/${activePackId}`),
    enabled: !!activePackId,
    staleTime: 30_000,
  });

  // ── Render ──

  return (
    <AppShell hideFooter>
      {activePackId ? (
        packError ? (
          <div className="h-[calc(100vh-56px)] flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
              <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
              </div>
              <p className="text-[13px] font-medium text-foreground">Failed to load chart pack</p>
              <p className="text-[12px] text-muted-foreground">Check your connection and try again.</p>
              <button onClick={() => refetchPack()} className="mt-1 text-[12px] font-medium text-primary hover:text-primary/80 transition-colors">Retry</button>
            </div>
          </div>
        ) : (
          <PackDetailView
            activePack={activePack}
            activePackId={activePackId}
            isPackLoading={isPackLoading}
            user={user}
            packs={packs}
            isLight={isLight}
            onBack={() => setActivePackId(null)}
            onFlash={handleFlash}
            refetchPack={refetchPack}
            refetchPacks={refetchPacks}
            refetchPublished={refetchPublished}
          />
        )
      ) : (
        (packsError || publishedError) && !packs && !publishedPacks ? (
          <div className="h-[calc(100vh-56px)] flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-center max-w-xs animate-fade-in">
              <div className="w-10 h-10 rounded-[var(--radius)] bg-destructive/10 border border-destructive/20 flex items-center justify-center">
                <AlertTriangle className="w-4.5 h-4.5 text-destructive" />
              </div>
              <p className="text-[13px] font-medium text-foreground">Failed to load chart packs</p>
              <p className="text-[12px] text-muted-foreground">Check your connection and try again.</p>
              <button onClick={() => { refetchPacks(); refetchPublished(); }} className="mt-1 text-[12px] font-medium text-primary hover:text-primary/80 transition-colors">Retry</button>
            </div>
          </div>
        ) : (
          <PackListView
            user={user}
            packs={packs}
            publishedPacks={publishedPacks}
            packsLoading={packsLoading}
            onSelectPack={setActivePackId}
            onFlash={handleFlash}
            refetchPacks={refetchPacks}
            refetchPublished={refetchPublished}
            isLight={isLight}
          />
        )
      )}

      {/* Flash toast */}
      {flash && <FlashToast flash={flash} onDismiss={dismissFlash} />}
    </AppShell>
  );
}

export default function ChartPackPage() {
  return (
    <Suspense fallback={
      <AppShell hideFooter>
        <div className="h-[calc(100vh-56px)] flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 animate-fade-in">
            <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
            <span className="stat-label text-muted-foreground/40">Loading chart packs</span>
          </div>
        </div>
      </AppShell>
    }>
      <ChartPacksPageInner />
    </Suspense>
  );
}
