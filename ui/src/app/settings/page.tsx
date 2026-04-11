'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import AuthGuard from '@/components/auth/AuthGuard';
import AppShell from '@/components/layout/AppShell';
import { Download, FileSpreadsheet, Check, Loader2, Terminal, Copy } from 'lucide-react';

/* ── Python Code ─────────────────────────────────────────────────────── */

const PYTHON_CODE = `import requests
import pandas as pd
from io import StringIO

BASE_URL = "http://localhost:8000"
EMAIL = "you@example.com"
PASSWORD = "your_password"


def login(email: str, password: str) -> str:
    """Login and return JWT token."""
    r = requests.post(
        f"{BASE_URL}/api/auth/login/json",
        json={"email": email, "password": password},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch(expr: str, token: str, fmt: str = "csv") -> pd.DataFrame:
    """Evaluate an expression and return a DataFrame."""
    r = requests.post(
        f"{BASE_URL}/api/data/evaluation",
        json={"code": expr, "format": fmt},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    if fmt == "csv":
        df = pd.read_csv(StringIO(r.text), index_col=0, parse_dates=True)
    else:
        df = pd.DataFrame(r.json())
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
    return df.sort_index(ascending=False)


# ── Usage ──
token = login(EMAIL, PASSWORD)
spx = fetch('Series("SPX Index:PX_LAST")', token)
macro = fetch('MultiSeries(A=Series("SPX Index:PX_LAST"), B=Series("XAU Curncy:PX_LAST"))', token)
`;

/* ── Main ──────────────────────────────────────────────────────────────── */

export default function SettingsPage() {
  const { user } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [copiedPy, setCopiedPy] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const resp = await apiFetch('/api/download/addin');
      if (!resp.ok) throw new Error('Download failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'InvestmentX.xlam';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDownloaded(true);
      setTimeout(() => setDownloaded(false), 3000);
    } catch {
      // silent
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AuthGuard>
      <AppShell hideFooter>
        <div className="page-shell">
          {/* Header */}
          <div className="page-header">
            <h1 className="page-header-title">SETTINGS</h1>
            <div className="w-px h-3 bg-border/60" aria-hidden />
            <span className="text-[11px] font-mono text-muted-foreground truncate">{user?.email}</span>
          </div>

          {/* Content */}
          <div className="page-content">
            <div className="max-w-3xl mx-auto px-3 sm:px-5 lg:px-6 py-5 space-y-6">

              {/* Excel Add-in Download */}
              <div className="panel-card p-5">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-[var(--radius)] bg-primary/10 border border-primary/15 flex items-center justify-center shrink-0">
                    <FileSpreadsheet className="w-5 h-5 text-primary/60" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h2 className="text-[13px] font-semibold text-foreground">Excel Add-in</h2>
                    <p className="text-[12px] text-muted-foreground/50 mt-1 leading-relaxed">
                      Investment-X ribbon for Excel. Fetch data, search series, manage timeseries metadata, import chartpacks, and format charts.
                    </p>

                    <div className="mt-3 flex items-center gap-3">
                      <button
                        onClick={handleDownload}
                        disabled={downloading}
                        className="flex items-center gap-2 h-8 px-4 text-[12px] font-medium rounded-[var(--radius)] bg-foreground text-background hover:bg-foreground/90 transition-colors disabled:opacity-50"
                      >
                        {downloading ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : downloaded ? (
                          <Check className="w-3.5 h-3.5" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        {downloaded ? 'Downloaded' : 'Download InvestmentX.xlam'}
                      </button>
                      <span className="text-[11px] font-mono text-muted-foreground/30">.xlam</span>
                    </div>

                    <div className="mt-4 pt-3 border-t border-border/20">
                      <h3 className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 mb-2">Installation</h3>
                      <ol className="text-[12px] text-muted-foreground/50 space-y-1.5 leading-relaxed">
                        <li><span className="font-mono text-muted-foreground/30 mr-1.5">1.</span>Download the <code className="font-mono text-[10.5px] px-1 py-0.5 bg-foreground/[0.04] border border-border/30 rounded">.xlam</code> file</li>
                        <li><span className="font-mono text-muted-foreground/30 mr-1.5">2.</span>Double-click to open &mdash; it auto-installs to your Add-ins folder</li>
                        <li><span className="font-mono text-muted-foreground/30 mr-1.5">3.</span>Restart Excel &mdash; the <strong>Investment-X</strong> tab appears in the ribbon</li>
                      </ol>
                    </div>

                    <div className="mt-3 pt-3 border-t border-border/20">
                      <h3 className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 mb-2">Ribbon Features</h3>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12px] text-muted-foreground/50">
                        <div><code className="font-mono text-[10.5px] text-muted-foreground/40">Ctrl+Shift+I</code> Fetch Selected</div>
                        <div><code className="font-mono text-[10.5px] text-muted-foreground/40">Ctrl+Shift+R</code> Refresh All</div>
                        <div><code className="font-mono text-[10.5px] text-muted-foreground/40">Ctrl+Shift+S</code> Series Search</div>
                        <div><code className="font-mono text-[10.5px] text-muted-foreground/40">Ctrl+Shift+F</code> Format Chart</div>
                        <div className="col-span-2"><span className="text-muted-foreground/40">Import Chartpack</span> — import charts into worksheets</div>
                        <div className="col-span-2"><span className="text-muted-foreground/40">Timeseries</span> — download, edit, create, save, and delete timeseries metadata</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Python Snippet */}
              <div className="panel-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5 text-muted-foreground/40" />
                    <span className="text-[12px] font-semibold text-foreground">Python</span>
                  </div>
                  <button
                    onClick={async () => {
                      await navigator.clipboard.writeText(PYTHON_CODE);
                      setCopiedPy(true);
                      setTimeout(() => setCopiedPy(false), 2000);
                    }}
                    className="flex items-center gap-1.5 h-6 px-2 text-[11px] font-medium rounded-[var(--radius)] border border-border/40 text-muted-foreground/50 hover:text-foreground hover:border-border/60 transition-colors"
                  >
                    {copiedPy ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                    {copiedPy ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <p className="text-[11.5px] text-muted-foreground/40 mb-3 leading-relaxed">
                  Uses <code className="font-mono text-[10.5px] px-1 py-0.5 bg-foreground/[0.04] border border-border/30 rounded">requests</code> + <code className="font-mono text-[10.5px] px-1 py-0.5 bg-foreground/[0.04] border border-border/30 rounded">pandas</code>.
                  Works with both <code className="font-mono text-[10.5px] px-1 py-0.5 bg-foreground/[0.04] border border-border/30 rounded">Series()</code> and <code className="font-mono text-[10.5px] px-1 py-0.5 bg-foreground/[0.04] border border-border/30 rounded">MultiSeries()</code>.
                </p>
                <pre className="text-[10.5px] font-mono text-muted-foreground/60 bg-foreground/[0.03] border border-border/30 rounded-[var(--radius)] p-3 overflow-x-auto leading-relaxed max-h-[400px] overflow-y-auto no-scrollbar">
                  {PYTHON_CODE}
                </pre>
              </div>

            </div>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
