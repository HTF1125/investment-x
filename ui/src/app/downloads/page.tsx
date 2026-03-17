'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { Download, FileSpreadsheet, RefreshCw, Check, AlertCircle, Loader2 } from 'lucide-react';
import { apiFetch, apiFetchJson } from '@/lib/api';

export default function DownloadsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [downloading, setDownloading] = useState(false);
  const [dlStatus, setDlStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [dlError, setDlError] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [syncError, setSyncError] = useState('');

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground/40" />
      </div>
    );
  }

  if (!user) {
    router.push('/login');
    return null;
  }

  const handleDownload = async () => {
    setDownloading(true);
    setDlStatus('idle');
    setDlError('');
    try {
      const res = await apiFetch('/api/download/market', { timeoutMs: 120000 });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Market.xlsm';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDlStatus('success');
    } catch (err: any) {
      setDlStatus('error');
      setDlError(err?.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    setSyncError('');
    try {
      const data = await apiFetchJson('/api/sync_uploads', { method: 'POST', timeoutMs: 60000 });
      setSyncResult(data);
    } catch (err: any) {
      setSyncError(err?.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const isAdmin = user?.role === 'owner' || user?.role === 'admin';

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="mb-10">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Downloads</h1>
        <p className="text-sm text-muted-foreground/50 mt-1.5">
          Tools and templates for data management
        </p>
      </div>

      {/* Market.xlsm download */}
      <div className="panel-card p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-[var(--radius)] bg-primary/10 flex items-center justify-center shrink-0">
            <FileSpreadsheet className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Market.xlsm</h2>
            <p className="text-xs text-muted-foreground/50 mt-0.5 leading-relaxed">
              Excel macro workbook for uploading FactSet, Infomax, and Bloomberg data.
              Includes VBA macros for bulk data upload, timeseries management, and chart formatting.
            </p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {['FactSet', 'Bloomberg', 'Infomax', 'VBA Macros'].map((tag) => (
                <span key={tag} className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 border border-border/30 rounded">
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-3">
              <button onClick={handleDownload} disabled={downloading} className="inline-flex items-center gap-2 px-3.5 py-2 bg-primary text-primary-foreground rounded-[var(--radius)] text-xs font-semibold transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]">
                {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : dlStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" />}
                {downloading ? 'Downloading...' : dlStatus === 'success' ? 'Downloaded' : 'Download'}
              </button>
              {dlStatus === 'error' && (
                <span className="text-xs text-destructive flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />{dlError}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* R2 Sync (admin only) */}
      {isAdmin && (
        <div className="panel-card p-5 mt-4">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-[var(--radius)] bg-foreground/5 flex items-center justify-center shrink-0">
              <RefreshCw className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Sync Uploads</h2>
              <p className="text-xs text-muted-foreground/50 mt-0.5 leading-relaxed">
                Process pending R2 upload files into local and cloud databases.
                Runs automatically every 5 minutes on local env.
              </p>
              <div className="mt-4 flex items-center gap-3">
                <button onClick={handleSync} disabled={syncing} className="btn-toolbar inline-flex items-center gap-2 text-xs font-semibold border border-border/50 rounded-[var(--radius)] transition-all hover:bg-foreground/5 disabled:opacity-50 disabled:cursor-not-allowed">
                  {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                  {syncing ? 'Syncing...' : 'Sync Now'}
                </button>
                {syncError && (
                  <span className="text-xs text-destructive flex items-center gap-1.5">
                    <AlertCircle className="w-3 h-3" />{syncError}
                  </span>
                )}
              </div>
              {syncResult && (
                <div className="mt-3 p-2.5 bg-card/50 border border-border/20 rounded text-xs font-mono text-muted-foreground/70">
                  <div>{syncResult.message}</div>
                  {syncResult.details?.map((d: any, i: number) => (
                    <div key={i} className="mt-1 pl-2 border-l-2 border-border/20">
                      {d.file}: {d.codes?.join(', ') || d.error || 'empty'}
                      {d.points ? ` (${d.points} pts)` : ''}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Setup instructions */}
      <div className="mt-8 p-4 border border-border/20 rounded-[var(--radius)] bg-card/30">
        <h3 className="text-xs font-semibold text-foreground mb-2">Setup</h3>
        <ol className="text-xs text-muted-foreground/60 space-y-1.5 list-decimal list-inside leading-relaxed">
          <li>Open <span className="font-mono text-foreground/70">Market.xlsm</span> and enable macros</li>
          <li>Set the API URL in <span className="font-mono text-foreground/70">Settings!E1</span></li>
          <li>Run the <span className="font-mono text-foreground/70">Login</span> macro (Alt+F8) to authenticate</li>
          <li>Use data provider add-ins (FactSet/Bloomberg) to pull data, then run upload macros</li>
        </ol>
      </div>
    </div>
  );
}
