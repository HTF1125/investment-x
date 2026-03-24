'use client';

import React, { useState, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import AppShell from '@/components/layout/AppShell';
import { Download, Upload, RefreshCw, Check, AlertCircle, Loader2, FileSpreadsheet } from 'lucide-react';
import { apiFetch, apiFetchJson } from '@/lib/api';

const SOURCES = ['FactSet', 'Bloomberg', 'Infomax'] as const;

export default function DataToolsPage() {
  const { user, token } = useAuth();

  // Template download state
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [templateDl, setTemplateDl] = useState(false);
  const [templateStatus, setTemplateStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [templateError, setTemplateError] = useState('');

  // Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  // Bulk create upload state
  const createFileRef = useRef<HTMLInputElement>(null);
  const [createUploading, setCreateUploading] = useState(false);
  const [createResult, setCreateResult] = useState<string | null>(null);
  const [createError, setCreateError] = useState('');
  const [createDragOver, setCreateDragOver] = useState(false);

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [syncError, setSyncError] = useState('');

  const isAdmin = user?.role === 'owner' || user?.role === 'admin';

  // ───── Template Download
  const toggleSource = (src: string) => {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  const handleTemplateDownload = async () => {
    if (templateDl || selectedSources.length === 0) return;
    setTemplateDl(true);
    setTemplateStatus('idle');
    setTemplateError('');
    try {
      const params = new URLSearchParams();
      selectedSources.forEach(s => params.append('source', s));
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const res = await apiFetch(`/api/timeseries/download_template?${params}`, { timeoutMs: 120000 });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(err.detail);
      }

      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] || `timeseries_template.xlsx`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setTemplateStatus('success');
      setTimeout(() => setTemplateStatus('idle'), 3000);
    } catch (err: any) {
      setTemplateStatus('error');
      setTemplateError(err?.message || 'Download failed');
    } finally {
      setTemplateDl(false);
    }
  };

  // ───── File Upload (via proxy)
  const doUpload = async (file: File) => {
    if (uploading) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError('');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await apiFetch('/api/timeseries/upload_template_data', {
        method: 'POST',
        body: formData,
        timeoutMs: 300000,
      });

      if (!res.ok) {
        const text = await res.text();
        let detail = `Upload failed (${res.status})`;
        try { detail = JSON.parse(text).detail || detail; } catch {}
        throw new Error(detail);
      }

      const data = await res.json();
      const parts: string[] = [];
      if (data.db_updated?.length) parts.push(`${data.db_updated.length} codes updated`);
      if (data.db_points_merged) parts.push(`${data.db_points_merged} points merged`);
      if (data.warning) parts.push(data.warning);
      setUploadResult(parts.join('. ') || data.message || `"${file.name}" uploaded successfully.`);
    } catch (err: any) {
      setUploadError(err?.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) doUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
      doUpload(file);
    } else {
      setUploadError('Please drop an .xlsx file');
    }
  };

  // ───── Bulk Create Upload
  const doCreateUpload = async (file: File) => {
    if (createUploading) return;
    setCreateUploading(true);
    setCreateResult(null);
    setCreateError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/timeseries/create_from_template', {
        method: 'POST',
        body: formData,
        timeoutMs: 300000,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      const data = await res.json();
      const parts: string[] = [];
      if (data.created?.length) parts.push(`${data.created.length} created`);
      if (data.updated?.length) parts.push(`${data.updated.length} updated`);
      if (data.data_merged) parts.push(`${data.data_merged} data points merged`);
      if (data.errors?.length) parts.push(`${data.errors.length} errors`);
      setCreateResult(parts.join(', ') || data.message);
    } catch (err: any) {
      setCreateError(err?.message || 'Upload failed');
    } finally {
      setCreateUploading(false);
      if (createFileRef.current) createFileRef.current.value = '';
    }
  };

  // ───── Sync
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

  return (
    <AppShell>
    <div className="max-w-xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="page-title">Data Tools</h1>
        <p className="text-[11px] text-muted-foreground/50 mt-1 font-mono tracking-wider">
          DOWNLOAD · UPLOAD · SYNC
        </p>
      </div>

      {/* ───── Download Template ───── */}
      <div className="panel-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-primary/10 flex items-center justify-center shrink-0">
            <Download className="w-3.5 h-3.5 text-primary" />
          </div>
          <div>
            <h2 className="text-[12px] font-semibold text-foreground">Download Template</h2>
            <p className="text-[10px] text-muted-foreground/50 mt-0.5">
              Generate an .xlsx with dates, codes, and add-in formulas ready for Excel
            </p>
          </div>
        </div>
        <div className="p-4 space-y-4">
          {/* Source chips */}
          <div>
            <label className="stat-label block mb-2">Data Source</label>
            <div className="flex flex-wrap gap-1.5">
              {SOURCES.map(src => (
                <button
                  key={src}
                  onClick={() => toggleSource(src)}
                  className={`px-2.5 h-7 text-[10px] font-mono uppercase tracking-[0.08em] rounded-[var(--radius)] border transition-all ${
                    selectedSources.includes(src)
                      ? 'bg-foreground text-background border-foreground'
                      : 'text-muted-foreground/50 border-border/40 hover:border-border/70 hover:text-foreground'
                  }`}
                >
                  {src}
                </button>
              ))}
            </div>
          </div>

          {/* Date range */}
          <div>
            <label className="stat-label block mb-2">Date Range</label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="h-7 px-2 text-[11px] font-mono bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
              />
              <span className="text-[10px] text-muted-foreground/30 font-mono">—</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="h-7 px-2 text-[11px] font-mono bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors"
              />
            </div>
          </div>

          {/* Download button */}
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handleTemplateDownload}
              disabled={templateDl || selectedSources.length === 0}
              className="btn-primary"
            >
              {templateDl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : templateStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" />}
              {templateDl ? 'Preparing...' : templateStatus === 'success' ? 'Downloaded' : 'Download Template'}
            </button>
            {selectedSources.length === 0 && (
              <span className="stat-label">Select at least one source</span>
            )}
            {templateStatus === 'error' && (
              <span className="text-[11px] text-destructive flex items-center gap-1.5">
                <AlertCircle className="w-3 h-3" />{templateError}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ───── Upload Data (admin only) ───── */}
      {isAdmin && (
        <div className="panel-card overflow-hidden mt-3">
          <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-primary/10 flex items-center justify-center shrink-0">
              <Upload className="w-3.5 h-3.5 text-primary" />
            </div>
            <div>
              <h2 className="text-[12px] font-semibold text-foreground">Upload Data</h2>
              <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                Row 8 = codes, column A = dates, row 9+ = values
              </p>
            </div>
          </div>
          <div className="p-4">
            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`flex flex-col items-center justify-center gap-2 py-8 border-2 border-dashed rounded-[var(--radius)] cursor-pointer transition-all ${
                dragOver
                  ? 'border-primary/60 bg-primary/[0.04]'
                  : 'border-border/30 hover:border-border/50 hover:bg-foreground/[0.02]'
              }`}
            >
              {uploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-primary/50" />
                  <span className="stat-label">Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5 text-muted-foreground/25" />
                  <span className="text-[11px] text-muted-foreground/40">Drop <span className="font-mono">.xlsx</span> here or click to browse</span>
                </>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.xlsm"
              onChange={handleFileChange}
              className="hidden"
            />

            {uploadResult && (
              <div className="mt-3 p-2.5 bg-success/[0.06] border border-success/20 rounded-[var(--radius)] text-[11px] text-success flex items-start gap-2">
                <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                {uploadResult}
              </div>
            )}
            {uploadError && (
              <div className="mt-3 p-2.5 bg-destructive/[0.06] border border-destructive/20 rounded-[var(--radius)] text-[11px] text-destructive flex items-center gap-1.5">
                <AlertCircle className="w-3 h-3 shrink-0" />{uploadError}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ───── Create New Timeseries (admin only) ───── */}
      {isAdmin && (
        <div className="panel-card overflow-hidden mt-3">
          <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-primary/10 flex items-center justify-center shrink-0">
              <FileSpreadsheet className="w-3.5 h-3.5 text-primary" />
            </div>
            <div>
              <h2 className="text-[12px] font-semibold text-foreground">Create New Timeseries</h2>
              <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                Fill in metadata (Sheet 1) and data (Sheet 2), then upload
              </p>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {/* Download template link */}
            <a
              href="/api/timeseries/create_template"
              download="timeseries_create_template.xlsx"
              className="btn-secondary"
            >
              <Download className="w-3.5 h-3.5" />
              Download Create Template
            </a>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setCreateDragOver(true); }}
              onDragLeave={() => setCreateDragOver(false)}
              onDrop={e => {
                e.preventDefault();
                setCreateDragOver(false);
                const file = e.dataTransfer.files?.[0];
                if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))) {
                  doCreateUpload(file);
                } else {
                  setCreateError('Please drop an .xlsx file');
                }
              }}
              onClick={() => createFileRef.current?.click()}
              className={`flex flex-col items-center justify-center gap-2 py-8 border-2 border-dashed rounded-[var(--radius)] cursor-pointer transition-all ${
                createDragOver
                  ? 'border-primary/60 bg-primary/[0.04]'
                  : 'border-border/30 hover:border-border/50 hover:bg-foreground/[0.02]'
              }`}
            >
              {createUploading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-primary/50" />
                  <span className="stat-label">Creating timeseries...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5 text-muted-foreground/25" />
                  <span className="text-[11px] text-muted-foreground/40">Drop filled template here or click to browse</span>
                </>
              )}
            </div>
            <input
              ref={createFileRef}
              type="file"
              accept=".xlsx,.xls,.xlsm"
              onChange={e => { const f = e.target.files?.[0]; if (f) doCreateUpload(f); }}
              className="hidden"
            />

            {createResult && (
              <div className="p-2.5 bg-success/[0.06] border border-success/20 rounded-[var(--radius)] text-[11px] text-success flex items-start gap-2">
                <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                {createResult}
              </div>
            )}
            {createError && (
              <div className="p-2.5 bg-destructive/[0.06] border border-destructive/20 rounded-[var(--radius)] text-[11px] text-destructive flex items-center gap-1.5">
                <AlertCircle className="w-3 h-3 shrink-0" />{createError}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ───── Sync Uploads (admin only) ───── */}
      {isAdmin && (
        <div className="panel-card overflow-hidden mt-3">
          <div className="px-4 py-3 border-b border-border/30 flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-foreground/[0.06] flex items-center justify-center shrink-0">
              <RefreshCw className="w-3.5 h-3.5 text-muted-foreground" />
            </div>
            <div>
              <h2 className="text-[12px] font-semibold text-foreground">Sync Uploads</h2>
              <p className="text-[10px] text-muted-foreground/50 mt-0.5">
                Process pending R2 files into local and cloud databases
              </p>
            </div>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex items-center gap-3">
              <button onClick={handleSync} disabled={syncing} className="btn-toolbar">
                {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                {syncing ? 'Syncing...' : 'Sync Now'}
              </button>
              {syncError && (
                <span className="text-[11px] text-destructive flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />{syncError}
                </span>
              )}
            </div>
            {syncResult && (
              <div className="p-3 bg-background border border-border/30 rounded-[var(--radius)] text-[11px] font-mono text-muted-foreground/70 space-y-1">
                <div className="text-foreground/70">{syncResult.message}</div>
                {syncResult.details?.map((d: any, i: number) => (
                  <div key={i} className="pl-2 border-l border-border/40 text-muted-foreground/50">
                    {d.file}: {d.codes?.join(', ') || d.error || 'empty'}
                    {d.points ? ` (${d.points} pts)` : ''}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ───── Setup Instructions ───── */}
      <div className="mt-6 p-4 border border-border/20 rounded-[var(--radius)] bg-foreground/[0.015]">
        <div className="flex items-center gap-2 mb-3">
          <span className="stat-label">Workflow</span>
          <div className="h-px flex-1 bg-border/20" />
        </div>
        <ol className="space-y-2">
          {[
            <>Select sources and date range, then <strong className="text-foreground/70 font-semibold">download a template</strong></>,
            <>Open the <span className="font-mono text-foreground/60 text-[10px]">.xlsx</span> in Excel with FactSet / Bloomberg / Infomax add-ins</>,
            <>Add-in formulas in row 9 <strong className="text-foreground/70 font-semibold">auto-populate data</strong> for the date range</>,
            <>Upload the filled file using the <strong className="text-foreground/70 font-semibold">Upload Data</strong> section above</>,
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <span className="shrink-0 w-4 h-4 rounded-full border border-border/40 flex items-center justify-center text-[9px] font-mono text-muted-foreground/50 mt-0.5">{i + 1}</span>
              <span className="text-[11px] text-muted-foreground/60 leading-relaxed">{step}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
    </AppShell>
  );
}
