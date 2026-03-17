'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { Download, FileSpreadsheet, Check, AlertCircle, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';

export default function DownloadsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [downloading, setDownloading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

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
    setStatus('idle');
    setErrorMsg('');

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
      setStatus('success');
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err?.message || 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="mb-10">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Downloads</h1>
        <p className="text-sm text-muted-foreground/50 mt-1.5">
          Tools and templates for data management
        </p>
      </div>

      <div className="panel-card p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-[var(--radius)] bg-primary/10 flex items-center justify-center shrink-0">
            <FileSpreadsheet className="w-5 h-5 text-primary" />
          </div>

          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Market.xlsm</h2>
            <p className="text-xs text-muted-foreground/50 mt-0.5 leading-relaxed">
              Excel macro workbook for uploading FactSet, Infomax, and Bloomberg data.
              Includes VBA macros for bulk data upload, timeseries management, Python query
              evaluation, and chart formatting.
            </p>

            <div className="flex flex-wrap gap-1.5 mt-3">
              {['FactSet', 'Bloomberg', 'Infomax', 'VBA Macros'].map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 border border-border/30 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-primary text-primary-foreground rounded-[var(--radius)] text-xs font-semibold transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
              >
                {downloading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : status === 'success' ? (
                  <Check className="w-3.5 h-3.5" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                {downloading ? 'Downloading...' : status === 'success' ? 'Downloaded' : 'Download'}
              </button>

              {status === 'error' && (
                <span className="text-xs text-destructive flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />
                  {errorMsg}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 border border-border/20 rounded-[var(--radius)] bg-card/30">
        <h3 className="text-xs font-semibold text-foreground mb-2">Setup</h3>
        <ol className="text-xs text-muted-foreground/60 space-y-1.5 list-decimal list-inside leading-relaxed">
          <li>Open <span className="font-mono text-foreground/70">Market.xlsm</span> and enable macros</li>
          <li>Set the <span className="font-mono text-foreground/70">API_URL</span> named range to your server URL</li>
          <li>Run the <span className="font-mono text-foreground/70">Login</span> macro (Alt+F8) to authenticate</li>
          <li>Use data provider add-ins (FactSet/Bloomberg) to pull data, then run upload macros</li>
        </ol>
      </div>
    </div>
  );
}
