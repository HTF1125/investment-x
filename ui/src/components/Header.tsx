'use client';

import { useEffect, useState } from 'react';
import { FileDown, Loader2, Check, Monitor } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

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

  useEffect(() => {
    setMounted(true);
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
      setTimeout(() => setExportStatus('idle'), 3000);
    } catch {
      setExportStatus('error');
      setTimeout(() => setExportStatus('idle'), 3000);
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
      setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } catch {
      setExportHtmlStatus('error');
      setTimeout(() => setExportHtmlStatus('idle'), 3000);
    } finally {
      setExportingHtml(false);
    }
  };

  return (
    <header className="max-w-[1600px] mx-auto mb-8 flex flex-col md:flex-row items-start md:items-center justify-between text-slate-500 font-mono text-xs gap-4">
        <div className="flex flex-wrap items-center gap-3">
            <button
                onClick={handleExportPDF}
                disabled={exporting || exportingHtml}
                className={`
                    flex items-center gap-2 px-4 py-2 rounded-xl border font-bold transition-all
                    ${exportStatus === 'success' 
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                        : exportStatus === 'error'
                        ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:text-white hover:border-white/20 shadow-lg shadow-black/20'
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
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                        : exportHtmlStatus === 'error'
                        ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        : 'bg-indigo-500/5 border-indigo-500/10 text-slate-300 hover:bg-indigo-500/10 hover:text-white hover:border-indigo-500/30'
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
                <span className="text-[10px] text-slate-600 mb-1">DATA STATUS</span>
                <span className="text-emerald-500 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    LIVE PIPELINE
                </span>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-slate-600 mb-1">REGION</span>
                <span className="text-slate-300 font-semibold uppercase">Seoul / KST</span>
            </div>
            {mounted && (
              <>
                <div className="w-px h-8 bg-white/10" />
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-slate-600 mb-1">LOCAL TIME</span>
                    <span className="text-slate-300 font-semibold tabular-nums">
                        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
                    </span>
                </div>
              </>
            )}
        </div>
    </header>
  );
}
