'use client';

import React, { useState, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Download, Upload, FileSpreadsheet, RefreshCw, Check, AlertCircle, Loader2, ChevronDown } from 'lucide-react';
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

  // Sync state
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [syncError, setSyncError] = useState('');

  // Legacy Market.xlsm state
  const [showLegacy, setShowLegacy] = useState(false);
  const [legacyDl, setLegacyDl] = useState(false);
  const [legacyStatus, setLegacyStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [legacyError, setLegacyError] = useState('');

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
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }

      const data = await res.json();
      setUploadResult(data.message || `"${file.name}" uploaded successfully.`);
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

  // ───── Legacy Market.xlsm
  const handleLegacyDownload = async () => {
    setLegacyDl(true);
    setLegacyStatus('idle');
    setLegacyError('');
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
      setLegacyStatus('success');
    } catch (err: any) {
      setLegacyStatus('error');
      setLegacyError(err?.message || 'Download failed');
    } finally {
      setLegacyDl(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      {/* Header */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Data Tools</h1>
        <p className="text-sm text-muted-foreground/50 mt-1.5">
          Download templates, upload data, and manage timeseries
        </p>
      </div>

      {/* ───── Download Template ───── */}
      <div className="panel-card p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-[var(--radius)] bg-primary/10 flex items-center justify-center shrink-0">
            <Download className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-semibold text-foreground">Download Template</h2>
            <p className="text-xs text-muted-foreground/50 mt-0.5 leading-relaxed">
              Generate a macro-free .xlsx with dates, codes, and add-in formulas.
              Open in Excel with FactSet/Infomax add-ins to auto-populate data.
            </p>

            {/* Source chips */}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {SOURCES.map(src => (
                <button
                  key={src}
                  onClick={() => toggleSource(src)}
                  className={`px-2.5 py-1 text-[10px] font-mono uppercase tracking-[0.08em] rounded border transition-all ${
                    selectedSources.includes(src)
                      ? 'bg-foreground text-background border-foreground'
                      : 'text-muted-foreground/50 border-border/30 hover:border-border/60'
                  }`}
                >
                  {src}
                </button>
              ))}
            </div>

            {/* Date range */}
            <div className="flex items-center gap-2 mt-3">
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="h-7 px-2 text-xs font-mono bg-background border border-border/50 rounded text-foreground"
              />
              <span className="text-xs text-muted-foreground/30">to</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="h-7 px-2 text-xs font-mono bg-background border border-border/50 rounded text-foreground"
              />
            </div>

            {/* Download button */}
            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={handleTemplateDownload}
                disabled={templateDl || selectedSources.length === 0}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-primary text-primary-foreground rounded-[var(--radius)] text-xs font-semibold transition-all hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
              >
                {templateDl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : templateStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" />}
                {templateDl ? 'Preparing...' : templateStatus === 'success' ? 'Downloaded' : 'Download Template'}
              </button>
              {selectedSources.length === 0 && (
                <span className="text-[10px] text-muted-foreground/40">Select at least one source</span>
              )}
              {templateStatus === 'error' && (
                <span className="text-xs text-destructive flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />{templateError}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ───── Upload Data (admin only) ───── */}
      {isAdmin && (
        <div className="panel-card p-5 mt-4">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-[var(--radius)] bg-primary/10 flex items-center justify-center shrink-0">
              <Upload className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-foreground">Upload Data</h2>
              <p className="text-xs text-muted-foreground/50 mt-0.5 leading-relaxed">
                Upload a filled .xlsx template. Row 8 = codes, column A = dates, row 9+ = values.
              </p>

              {/* Drop zone */}
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`mt-3 flex flex-col items-center justify-center gap-1.5 py-6 border-2 border-dashed rounded-[var(--radius)] cursor-pointer transition-all ${
                  dragOver
                    ? 'border-primary bg-primary/5'
                    : 'border-border/30 hover:border-border/60'
                }`}
              >
                {uploading ? (
                  <Loader2 className="w-5 h-5 animate-spin text-muted-foreground/40" />
                ) : (
                  <Upload className="w-5 h-5 text-muted-foreground/30" />
                )}
                <span className="text-xs text-muted-foreground/40">
                  {uploading ? 'Uploading...' : 'Drop .xlsx here or click to browse'}
                </span>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
              />

              {uploadResult && (
                <div className="mt-3 p-2.5 bg-card/50 border border-success/20 rounded text-xs text-success flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  {uploadResult}
                </div>
              )}
              {uploadError && (
                <div className="mt-3 text-xs text-destructive flex items-center gap-1.5">
                  <AlertCircle className="w-3 h-3" />{uploadError}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ───── Sync Uploads (admin only) ───── */}
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

      {/* ───── Legacy Market.xlsm (collapsed) ───── */}
      <div className="mt-4">
        <button
          onClick={() => setShowLegacy(!showLegacy)}
          className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/30 hover:text-muted-foreground/50 transition-colors"
        >
          <ChevronDown className={`w-3 h-3 transition-transform ${showLegacy ? 'rotate-0' : '-rotate-90'}`} />
          Legacy Tools
        </button>
        {showLegacy && (
          <div className="panel-card p-5 mt-2 opacity-70">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-[var(--radius)] bg-foreground/5 flex items-center justify-center shrink-0">
                <FileSpreadsheet className="w-5 h-5 text-muted-foreground/50" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-sm font-semibold text-foreground/70">Market.xlsm</h2>
                <p className="text-xs text-muted-foreground/40 mt-0.5 leading-relaxed">
                  Excel macro workbook with VBA for bulk upload, timeseries management, and chart formatting.
                  Requires enabling macros and VBA login.
                </p>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {['VBA Macros', 'Legacy'].map(tag => (
                    <span key={tag} className="px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.08em] text-muted-foreground/30 border border-border/20 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex items-center gap-3">
                  <button onClick={handleLegacyDownload} disabled={legacyDl} className="btn-toolbar inline-flex items-center gap-2 text-xs font-semibold border border-border/50 rounded-[var(--radius)] transition-all hover:bg-foreground/5 disabled:opacity-50 disabled:cursor-not-allowed">
                    {legacyDl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : legacyStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" />}
                    {legacyDl ? 'Downloading...' : legacyStatus === 'success' ? 'Downloaded' : 'Download'}
                  </button>
                  {legacyStatus === 'error' && (
                    <span className="text-xs text-destructive flex items-center gap-1.5">
                      <AlertCircle className="w-3 h-3" />{legacyError}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ───── Setup Instructions ───── */}
      <div className="mt-8 p-4 border border-border/20 rounded-[var(--radius)] bg-card/30">
        <h3 className="text-xs font-semibold text-foreground mb-2">Workflow</h3>
        <ol className="text-xs text-muted-foreground/60 space-y-1.5 list-decimal list-inside leading-relaxed">
          <li>Select sources and date range, then download a template above</li>
          <li>Open the <span className="font-mono text-foreground/70">.xlsx</span> in Excel with data provider add-ins (FactSet / Bloomberg / Infomax)</li>
          <li>Add-in formulas in row 9 auto-populate data for the date range</li>
          <li>Upload the filled file using the upload section above</li>
        </ol>
      </div>
    </div>
  );
}
