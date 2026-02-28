'use client';

import { useEffect, useRef, useState } from 'react';
import { FileDown, Loader2, Check, Monitor } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';

/**
 * Compact status bar showing data pipeline health and region.
 * Now includes Global Report export capability.
 */
export default function Header() {
  const [mounted, setMounted] = useState(false);
  const { token } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';

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
      const res = await fetch('/api/custom/pdf', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ items: [] }),
      });

      if (!res.ok) throw new Error('PDF failed');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      setExportStatus('success');
      pdfTimerRef.current = setTimeout(() => setExportStatus('idle'), 3000);
    } catch {
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
      const res = await fetch('/api/custom/html', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ items: [] }),
      });

      if (!res.ok) throw new Error('HTML failed');

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `InvestmentX_Portfolio_${new Date().toISOString().slice(0, 10)}.html`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      setExportHtmlStatus('success');
      htmlTimerRef.current = setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } catch {
      setExportHtmlStatus('error');
      htmlTimerRef.current = setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } finally {
      setExportingHtml(false);
    }
  };

  return (
    <header className="max-w-[1600px] mx-auto mb-8 flex flex-col md:flex-row items-start md:items-center justify-between text-muted-foreground font-mono text-xs gap-4">
        <div className="flex flex-wrap items-center gap-3">
            <button
                onClick={handleExportPDF}
                disabled={exporting || exportingHtml}
                className={`
                    flex items-center gap-2 px-4 py-2 rounded-xl border font-bold transition-all
                    ${exportStatus === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                        : exportStatus === 'error'
                        ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        : 'bg-foreground/[0.04] border-border text-foreground hover:bg-foreground/[0.08] hover:border-border/80'
                    }
                    disabled:opacity-30
                `}
            >
                {exporting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : exportStatus === 'success' ? (
                    <Check className="w-3.5 h-3.5" />
                ) : (
                    <FileDown className="w-3.5 h-3.5 text-indigo-400" />
                )}
                {exporting ? 'GENERATING...' : exportStatus === 'success' ? 'DOWNLOADED' : 'GLOBAL REPORT (PDF)'}
            </button>

            <button
                onClick={handleExportHTML}
                disabled={exporting || exportingHtml}
                className={`
                    flex items-center gap-2 px-4 py-2 rounded-xl border font-bold transition-all
                    ${exportHtmlStatus === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                        : exportHtmlStatus === 'error'
                        ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        : 'bg-indigo-500/[0.04] border-indigo-500/20 text-foreground hover:bg-indigo-500/[0.08] hover:border-indigo-500/40'
                    }
                    disabled:opacity-30
                `}
            >
                {exportingHtml ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : exportHtmlStatus === 'success' ? (
                    <Check className="w-3.5 h-3.5" />
                ) : (
                    <Monitor className="w-3.5 h-3.5 text-sky-400" />
                )}
                {exportingHtml ? 'BUNDLING...' : exportHtmlStatus === 'success' ? 'DOWNLOADED' : 'INTERACTIVE (HTML)'}
            </button>
        </div>

        <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-muted-foreground/50 mb-1">DATA STATUS</span>
                <span className="text-emerald-500 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    LIVE PIPELINE
                </span>
            </div>
            <div className="w-px h-8 bg-border/60" />
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-muted-foreground/50 mb-1">REGION</span>
                <span className="text-foreground font-semibold uppercase">Seoul / KST</span>
            </div>
            {mounted && (
              <>
                <div className="w-px h-8 bg-border/60" />
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-muted-foreground/50 mb-1">LOCAL TIME</span>
                    <span className="text-foreground font-semibold tabular-nums">
                        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
                    </span>
                </div>
              </>
            )}
        </div>
    </header>
  );
}
