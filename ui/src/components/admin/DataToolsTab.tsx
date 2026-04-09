'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Download, Upload, Check, AlertCircle, Loader2, FileSpreadsheet } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { useNativeInputStyle } from '@/hooks/useNativeInputStyle';

const SOURCES = ['FactSet', 'Bloomberg', 'Infomax'] as const;

// ── Shared ──

function DropZone({ onDrop, uploading, label, dragOver, setDragOver, inputRef }: {
  onDrop: (file: File) => void;
  uploading: boolean;
  label: string;
  dragOver: boolean;
  setDragOver: (v: boolean) => void;
  inputRef: React.RefObject<HTMLInputElement>;
}) {
  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file && /\.xlsx?$/.test(file.name)) onDrop(file);
      }}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-1.5 py-5 border-2 border-dashed rounded-[var(--radius)] cursor-pointer transition-all ${
        dragOver
          ? 'border-primary/60 bg-primary/[0.04]'
          : 'border-border/30 hover:border-border/50 hover:bg-foreground/[0.02]'
      }`}
    >
      {uploading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-primary/50" />
          <span className="stat-label">{label}</span>
        </>
      ) : (
        <>
          <Upload className="w-4 h-4 text-muted-foreground/25" />
          <span className="text-[12.5px] text-muted-foreground/40">Drop <span className="font-mono">.xlsx</span> or click</span>
        </>
      )}
    </div>
  );
}

function StatusMsg({ success, error }: { success?: string | null; error?: string }) {
  if (success) return (
    <div className="mt-2 p-2 bg-success/[0.06] border border-success/20 rounded-[var(--radius)] text-[12.5px] text-success flex items-start gap-2">
      <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />{success}
    </div>
  );
  if (error) return (
    <div className="mt-2 p-2 bg-destructive/[0.06] border border-destructive/20 rounded-[var(--radius)] text-[12.5px] text-destructive flex items-center gap-1.5">
      <AlertCircle className="w-3 h-3 shrink-0" />{error}
    </div>
  );
  return null;
}

// ── Main ──

export default function DataToolsTab() {
  const nativeInputStyle = useNativeInputStyle();

  // ── Update Data flow state ──
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 1);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [templateDl, setTemplateDl] = useState(false);
  const [templateStatus, setTemplateStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [templateError, setTemplateError] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  // ── Create Timeseries state ──
  const createFileRef = useRef<HTMLInputElement>(null);
  const [createUploading, setCreateUploading] = useState(false);
  const [createResult, setCreateResult] = useState<string | null>(null);
  const [createError, setCreateError] = useState('');
  const [createDragOver, setCreateDragOver] = useState(false);

  const invalidRange = startDate >= endDate;

  const toggleSource = (src: string) => {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  // ── Handlers ──

  const handleTemplateDownload = useCallback(async () => {
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
      const filename = match?.[1] || 'timeseries_template.xlsx';

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
  }, [templateDl, selectedSources, startDate, endDate]);

  const doUpload = useCallback(async (file: File) => {
    if (uploading) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/timeseries/upload_template_data', {
        method: 'POST', body: formData, timeoutMs: 300000,
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
      setUploadResult(parts.join('. ') || data.message || `"${file.name}" uploaded.`);
    } catch (err: any) {
      setUploadError(err?.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [uploading]);

  const doCreateUpload = useCallback(async (file: File) => {
    if (createUploading) return;
    setCreateUploading(true);
    setCreateResult(null);
    setCreateError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/timeseries/create_from_template', {
        method: 'POST', body: formData, timeoutMs: 300000,
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
  }, [createUploading]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">

      {/* ═══ Update Data — download template + upload filled file ═══ */}
      <div className="panel-card overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border/30 flex items-center gap-2.5">
          <Download className="w-3.5 h-3.5 text-primary/70" />
          <div>
            <h3 className="text-[13px] font-semibold text-foreground">Update Data</h3>
            <p className="text-[11.5px] text-muted-foreground/50">Download template, fill in Excel, upload back</p>
          </div>
        </div>
        <div className="p-4 space-y-3">

          {/* Step 1: Source + date range + download */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="shrink-0 w-4 h-4 rounded-full bg-foreground/[0.06] flex items-center justify-center text-[11px] font-mono font-bold text-muted-foreground/50">1</span>
              <span className="text-[12.5px] font-semibold text-foreground/70">Download Template</span>
            </div>
            <div className="space-y-2.5 pl-6">
              {/* Source chips */}
              <div>
                <label className="stat-label block mb-1">Source</label>
                <div className="flex flex-wrap gap-1.5">
                  {SOURCES.map(src => (
                    <button
                      key={src}
                      onClick={() => toggleSource(src)}
                      className={`px-2.5 h-7 text-[11.5px] font-mono uppercase tracking-[0.08em] rounded-[var(--radius)] border transition-all ${
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
                <label className="stat-label block mb-1">Date Range</label>
                <div className="flex items-center gap-2">
                  <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                    style={nativeInputStyle}
                    className="h-7 px-2 text-[12.5px] font-mono bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors" />
                  <span className="text-[11.5px] text-muted-foreground/30 font-mono">—</span>
                  <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                    style={nativeInputStyle}
                    className="h-7 px-2 text-[12.5px] font-mono bg-background border border-border/50 rounded-[var(--radius)] text-foreground focus:outline-none focus:border-primary/50 transition-colors" />
                </div>
              </div>
              {/* Download button */}
              <div className="flex items-center gap-3">
                <button onClick={handleTemplateDownload} disabled={templateDl || selectedSources.length === 0 || invalidRange} className="btn-primary">
                  {templateDl ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : templateStatus === 'success' ? <Check className="w-3.5 h-3.5" /> : <Download className="w-3.5 h-3.5" />}
                  {templateDl ? 'Preparing...' : templateStatus === 'success' ? 'Downloaded' : 'Download'}
                </button>
                {selectedSources.length === 0 && <span className="stat-label">Select a source</span>}
                {invalidRange && selectedSources.length > 0 && <span className="stat-label text-destructive/60">Invalid range</span>}
                {templateStatus === 'error' && (
                  <span className="text-[12.5px] text-destructive flex items-center gap-1.5">
                    <AlertCircle className="w-3 h-3" />{templateError}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="h-px bg-border/20" />

          {/* Step 2: Upload filled file */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="shrink-0 w-4 h-4 rounded-full bg-foreground/[0.06] flex items-center justify-center text-[11px] font-mono font-bold text-muted-foreground/50">2</span>
              <span className="text-[12.5px] font-semibold text-foreground/70">Upload Filled File</span>
            </div>
            <div className="pl-6">
              <DropZone onDrop={doUpload} uploading={uploading} label="Uploading..." dragOver={dragOver} setDragOver={setDragOver} inputRef={fileInputRef as React.RefObject<HTMLInputElement>} />
              <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.xlsm" onChange={e => { const f = e.target.files?.[0]; if (f) doUpload(f); }} className="hidden" />
              <StatusMsg success={uploadResult} error={uploadError} />
            </div>
          </div>
        </div>
      </div>

      {/* ═══ Create New Timeseries ═══ */}
      <div className="panel-card overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border/30 flex items-center gap-2.5">
          <FileSpreadsheet className="w-3.5 h-3.5 text-primary/70" />
          <div>
            <h3 className="text-[13px] font-semibold text-foreground">Create Timeseries</h3>
            <p className="text-[11.5px] text-muted-foreground/50">New series from template — metadata (Sheet 1) + data (Sheet 2)</p>
          </div>
        </div>
        <div className="p-4 space-y-3">
          <a href="/api/timeseries/create_template" download="timeseries_create_template.xlsx" className="btn-secondary">
            <Download className="w-3.5 h-3.5" />
            Download Template
          </a>
          <DropZone onDrop={doCreateUpload} uploading={createUploading} label="Creating..." dragOver={createDragOver} setDragOver={setCreateDragOver} inputRef={createFileRef as React.RefObject<HTMLInputElement>} />
          <input ref={createFileRef} type="file" accept=".xlsx,.xls,.xlsm" onChange={e => { const f = e.target.files?.[0]; if (f) doCreateUpload(f); }} className="hidden" />
          <StatusMsg success={createResult} error={createError} />
        </div>
      </div>
    </div>
  );
}
