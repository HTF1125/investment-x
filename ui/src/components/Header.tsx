'use client';

import { useEffect, useRef, useState } from 'react';
import { FileDown, Loader2, Check, Monitor } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { getDirectApiBase } from '@/lib/api';

/**
 * Compact status bar showing data pipeline health and region.
 * Now includes Global Report export capability.
 */
export default function Header() {
  const [mounted, setMounted] = useState(false);
  const { token } = useAuth();
  // PDF State
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // HTML State
  const [exportingHtml, setExportingHtml] = useState(false);
  const [exportHtmlStatus, setExportHtmlStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Timer refs for cleanup on unmount
  const pdfTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const htmlTimerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    setMounted(true);
    return () => {
      clearTimeout(pdfTimerRef.current);
      clearTimeout(htmlTimerRef.current);
    };
  }, []);

  const handleExportPDF = async () => {
    if (exporting) return;
    setExporting(true);
    setExportStatus('idle');

    try {
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/pdf`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(`PDF failed: ${res.status} ${errText}`);
      }

      const blob = await res.blob();
      if (!blob.size) throw new Error('Empty PDF response');

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Delay revocation so the browser has time to start the download
      setTimeout(() => window.URL.revokeObjectURL(url), 60000);

      setExportStatus('success');
      pdfTimerRef.current = setTimeout(() => setExportStatus('idle'), 3000);
    } catch (err) {
      console.error('PDF export error:', err);
      setExportStatus('error');
      pdfTimerRef.current = setTimeout(() => setExportStatus('idle'), 3000);
    } finally {
      setExporting(false);
    }
  };

  const handleExportHTML = async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
    setExportHtmlStatus('idle');

    try {
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/html`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        credentials: 'include',
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(`HTML failed: ${res.status} ${errText}`);
      }

      const blob = await res.blob();
      if (!blob.size) throw new Error('Empty HTML response');

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Portfolio_${new Date().toISOString().slice(0, 10)}.html`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 60000);

      setExportHtmlStatus('success');
      htmlTimerRef.current = setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } catch (err) {
      console.error('HTML export error:', err);
      setExportHtmlStatus('error');
      htmlTimerRef.current = setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } finally {
      setExportingHtml(false);
    }
  };

  return (
    <header className="max-w-[1600px] mx-auto mb-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
            <button
                onClick={handleExportPDF}
                disabled={exporting || exportingHtml}
                className={`btn-toolbar ${
                    exportStatus === 'success'
                        ? '!text-emerald-500 !border-emerald-500/25'
                        : exportStatus === 'error'
                        ? '!text-rose-400 !border-rose-500/25'
                        : ''
                }`}
            >
                {exporting ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                ) : exportStatus === 'success' ? (
                    <Check className="w-3 h-3" />
                ) : (
                    <FileDown className="w-3 h-3" />
                )}
                {exporting ? 'Generating...' : exportStatus === 'success' ? 'Downloaded' : 'PDF Report'}
            </button>

            <button
                onClick={handleExportHTML}
                disabled={exporting || exportingHtml}
                className={`btn-toolbar ${
                    exportHtmlStatus === 'success'
                        ? '!text-emerald-500 !border-emerald-500/25'
                        : exportHtmlStatus === 'error'
                        ? '!text-rose-400 !border-rose-500/25'
                        : ''
                }`}
            >
                {exportingHtml ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                ) : exportHtmlStatus === 'success' ? (
                    <Check className="w-3 h-3" />
                ) : (
                    <Monitor className="w-3 h-3" />
                )}
                {exportingHtml ? 'Bundling...' : exportHtmlStatus === 'success' ? 'Downloaded' : 'Interactive HTML'}
            </button>
        </div>

        <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground">
            <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-emerald-500 uppercase tracking-wider">Live</span>
            </div>
            <div className="w-px h-3.5 bg-border/50" />
            <span className="uppercase tracking-wider text-muted-foreground/60">Seoul / KST</span>
            {mounted && (
              <>
                <div className="w-px h-3.5 bg-border/50" />
                <span className="text-foreground tabular-nums">
                    {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
                </span>
              </>
            )}
        </div>
    </header>
  );
}
