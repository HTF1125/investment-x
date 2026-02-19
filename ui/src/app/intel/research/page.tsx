'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import AppShell from '@/components/AppShell';
import { apiFetchJson, apiFetch } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { 
  FileText, Search, Download, Upload, Calendar, 
  Building2, ExternalLink, ChevronRight, Filter, 
  CloudUpload, CheckCircle, XCircle, Loader2,
  Trash2, Edit3, Check, X, Tag, MoreHorizontal,
  ArrowUpDown, Zap, Database, Mail, RefreshCcw,
  Library
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

interface Insight {
  id: string;
  published_date: string | null;
  issuer: string | null;
  name: string | null;
  status: string;
  summary: string | null;
  created: string;
}

interface PaginatedResponse {
  items: Insight[];
  total: number;
}

export default function ResearchPage() {
  const { user } = useAuth();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState('');
  const [filterIssuer, setFilterIssuer] = useState('all');
  const [isDragging, setIsDragging] = useState(false);
  const [uploadToast, setUploadToast] = useState<{ active: boolean; success: number; total: number } | null>(null);
  
  const [editingId, setEditingId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Insight>>({});

  const LIMIT = 50;

  const fetchInsights = useCallback(async (currentSkip: number, query: string = '', isInitial: boolean = false) => {
    if (isInitial) setLoading(true);
    else setLoadingMore(true);

    try {
      const url = `/api/insights?skip=${currentSkip}&limit=${LIMIT}${query ? `&q=${encodeURIComponent(query)}` : ''}`;
      const data = await apiFetchJson<PaginatedResponse>(url);
      if (isInitial) {
        setInsights(data.items);
      } else {
        setInsights(prev => [...prev, ...data.items]);
      }
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch insights:', err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    const handler = setTimeout(() => {
      setSkip(0);
      fetchInsights(0, search, true);
    }, 500);
    return () => clearTimeout(handler);
  }, [search, fetchInsights]);

  const loadMore = () => {
    if (loadingMore || insights.length >= total) return;
    const nextSkip = skip + LIMIT;
    setSkip(nextSkip);
    fetchInsights(nextSkip, search, false);
  };

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    
    let pid: string | null = null;
    try {
      const res = await apiFetch('/api/task/process/start?name=Intelligence%20Ingestion', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        pid = data.id;
      }
    } catch (e) { console.warn(e); }

    setUploadToast({ active: true, success: 0, total: files.length });
    let successCount = 0;

    for (let i = i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('/api/insights/upload', {
          method: 'POST',
          body: formData,
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (response.ok) {
          successCount++;
          setUploadToast(prev => prev ? { ...prev, success: successCount } : null);
        }
      } catch (err) { console.error(err); }
    }

    setTimeout(() => {
      setUploadToast(null);
      setSkip(0);
      fetchInsights(0, search, true);
    }, 2000);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Permanently delete "${name}"?`)) return;
    try {
      const res = await apiFetch(`/api/insights/${id}`, { method: 'DELETE' });
      if (res.ok) setInsights(prev => prev.filter(i => i.id !== id));
    } catch (err) { console.error(err); }
  };

  const handleUpdate = async () => {
    if (!editingId) return;
    setSavingId(editingId);
    try {
      const res = await apiFetch(`/api/insights/${editingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      });
      if (res.ok) {
        const updated = await res.json();
        setInsights(prev => prev.map(i => i.id === editingId ? updated : i));
        setEditingId(null);
      }
    } catch (err) { console.error(err); } finally { setSavingId(null); }
  };

  const issuers = useMemo(() => Array.from(new Set(insights.map(i => i.issuer).filter(Boolean))) as string[], [insights]);
  const displayedInsights = useMemo(() => insights.filter(i => filterIssuer === 'all' || i.issuer === filterIssuer), [insights, filterIssuer]);

  return (
    <AppShell>
      <div 
        className="relative min-h-[calc(100vh-64px)] bg-[#0A0A0A] text-slate-300 antialiased font-sans selection:bg-cyan-500/30"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleUploadFiles(e.dataTransfer.files); }}
      >
        {/* Progress Toast */}
        <AnimatePresence>
          {uploadToast && (
            <motion.div initial={{ y: 100, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 100, opacity: 0 }}
              className="fixed bottom-8 right-8 z-[100] w-80 bg-[#141414] border border-white/10 rounded-xl shadow-2xl p-5 backdrop-blur-3xl">
              <div className="flex items-center gap-3 mb-3">
                <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                <span className="text-xs font-semibold text-white">Neural Ingest Pipeline</span>
                <span className="ml-auto text-[10px] font-mono text-cyan-500">{uploadToast.success}/{uploadToast.total}</span>
              </div>
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                <motion.div className="h-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]" animate={{ width: `${(uploadToast.success / uploadToast.total) * 100}%` }} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="max-w-full px-6 py-8 mx-auto">
          {/* Timeseries Style Header */}
          <div className="flex flex-col gap-8 mb-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 flex items-center justify-center bg-gradient-to-br from-[#8B5CF6] to-[#6D28D9] rounded-xl shadow-[0_0_20px_rgba(139,92,246,0.2)]">
                  <Library className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight mb-1">Research Intelligence Library</h1>
                  <p className="text-[11px] font-medium text-slate-500 tracking-wide">Search, Collect, Manage, and Audit institutional research</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button className="h-10 px-4 flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#222] border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-all">
                  <RefreshCcw className="w-3.5 h-3.5" />
                  <span>Update Vault</span>
                </button>
                <button className="h-10 px-4 flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#222] border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-all">
                  <Mail className="w-3.5 h-3.5" />
                  <span>Email Report</span>
                </button>
                <button className="h-10 px-4 flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#222] border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-all">
                  <Download className="w-3.5 h-3.5" />
                  <span>Export Data</span>
                </button>
                <label className="h-10 px-4 flex items-center gap-2 bg-[#1A1A1A] hover:bg-[#222] border border-white/10 rounded-lg text-xs font-medium text-slate-300 cursor-pointer transition-all">
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload PDF</span>
                  <input type="file" accept=".pdf" multiple className="hidden" onChange={(e) => handleUploadFiles(e.target.files)} />
                </label>
                <button className="h-10 px-5 flex items-center gap-2 bg-[#00A3FF] hover:bg-[#0095E8] text-white rounded-lg text-xs font-bold transition-all shadow-[0_4px_12px_rgba(0,163,255,0.3)]">
                  <Zap className="w-4 h-4 fill-white" />
                  <span>+ New Analysis</span>
                </button>
              </div>
            </div>

            {/* Prominent Search Bar */}
            <div className="relative">
              <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
              <input 
                type="text" 
                placeholder="Search by analysis name, issuer, summary, or category..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)}
                className="w-full h-14 pl-14 pr-6 bg-[#111] border border-white/5 rounded-xl text-sm text-white placeholder:text-slate-700 focus:outline-none focus:border-cyan-500/20 transition-all font-medium"
              />
            </div>
          </div>

          {/* Timeseries Style Table Container */}
          <div className="border border-white/5 rounded-lg overflow-hidden bg-[#0A0A0A]/50 backdrop-blur-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr className="border-b border-white/[0.04] bg-[#0E0E0E]">
                    <th className="px-6 py-4 text-[11px] font-bold text-slate-500 tracking-wider w-[40%]">Analysis Identifier</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-slate-500 tracking-wider w-[20%]">Provider</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-slate-500 tracking-wider w-[15%]">Asset Class</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-slate-500 tracking-wider w-[12%]">Published</th>
                    <th className="px-6 py-4 text-[11px] font-bold text-slate-500 tracking-wider w-[13%] text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.02]">
                  {loading ? (
                    [1, 2, 3, 4, 15].map(i => (
                      <tr key={i} className="animate-pulse">
                        <td colSpan={5} className="px-6 py-5"><div className="h-4 bg-white/5 rounded w-1/3" /></td>
                      </tr>
                    ))
                  ) : displayedInsights.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-8 py-32 text-center text-slate-600 font-medium text-xs italic opacity-40">No records found in current scan</td>
                    </tr>
                  ) : displayedInsights.map((item) => (
                    <tr key={item.id} className="group hover:bg-white/[0.01] transition-all duration-150 border-b border-white/[0.01]">
                      {/* Name Column */}
                      <td className="px-6 py-4">
                        {editingId === item.id ? (
                          <input value={editForm.name || ''} onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                            className="w-full h-9 bg-black/60 border border-cyan-500/30 rounded px-4 text-xs text-white focus:outline-none" autoFocus />
                        ) : (
                          <div className="flex flex-col gap-1">
                            <span className="text-[13px] font-semibold text-cyan-400/90 hover:text-cyan-400 cursor-pointer tracking-tight truncate">
                              {item.name || 'Untitled Analysis'}
                            </span>
                            <span className="text-[11px] text-slate-500 font-medium truncate opacity-70 group-hover:opacity-100 transition-all">
                              {item.summary || 'Proprietary Research Feed'}
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Source Column */}
                      <td className="px-4 py-4">
                        {editingId === item.id ? (
                          <input value={editForm.issuer || ''} onChange={e => setEditForm({ ...editForm, issuer: e.target.value })}
                            className="w-full h-9 bg-black/60 border border-cyan-500/30 rounded px-4 text-xs text-white" />
                        ) : (
                          <div className="flex items-center gap-3">
                            <span className="text-[12px] font-medium text-slate-400 truncate">{item.issuer || 'Internal'}</span>
                          </div>
                        )}
                      </td>

                      {/* Pill Style Asset Class (Status placeholder) */}
                      <td className="px-4 py-4">
                         <div className="px-3 py-1 rounded-full bg-[#8B5CF6]/5 border border-[#8B5CF6]/20 text-[#A78BFA] text-[10px] font-semibold inline-block">
                           {item.status === 'new' ? 'Intelligence' : 'Archived'}
                         </div>
                      </td>

                      {/* Date Column */}
                      <td className="px-4 py-4 font-mono text-xs font-medium text-slate-500 tracking-tight">
                        {editingId === item.id ? (
                          <input type="date" value={editForm.published_date || ''} onChange={e => setEditForm({ ...editForm, published_date: e.target.value })}
                            className="w-full h-9 bg-black/60 border border-cyan-500/30 rounded px-3 text-xs text-white" />
                        ) : (
                          item.published_date || '----.--.--'
                        )}
                      </td>

                      {/* Actions Column */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {editingId === item.id ? (
                            <>
                              <button onClick={handleUpdate} disabled={savingId === item.id}
                                className="h-8 px-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded transition-all flex items-center justify-center disabled:opacity-50">
                                {savingId === item.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-4 h-4" />}
                              </button>
                              <button onClick={() => setEditingId(null)}
                                className="h-8 px-4 bg-white/5 hover:bg-white/10 text-slate-400 rounded transition-all flex items-center justify-center">
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          ) : (
                            <>
                              <a href={`/api/insights/${item.id}/pdf`} target="_blank" rel="noopener noreferrer"
                                className="h-9 px-4 hover:bg-white/5 text-[11px] font-semibold text-slate-500 hover:text-white transition-all flex items-center gap-2">
                                <ExternalLink className="w-3 h-3" />
                                View
                              </a>
                              {user?.is_admin && (
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button onClick={() => { setEditingId(item.id); setEditForm(item); }}
                                    className="w-8 h-8 flex items-center justify-center hover:bg-white/5 text-slate-600 hover:text-white transition-all rounded">
                                    <Edit3 className="w-3.5 h-3.5" />
                                  </button>
                                  <button onClick={() => handleDelete(item.id, item.name || '')}
                                    className="w-8 h-8 flex items-center justify-center hover:bg-rose-500/5 text-slate-600 hover:text-rose-500 transition-all rounded">
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}

                  {insights.length < total && !search && filterIssuer === 'all' && (
                    <tr>
                      <td colSpan={5} className="px-6 py-10 text-center bg-[#050505]/30">
                        <button 
                          onClick={loadMore}
                          disabled={loadingMore}
                          className="h-11 px-8 bg-[#111] hover:bg-[#1A1A1A] text-slate-500 hover:text-white border border-white/5 rounded-lg text-xs font-semibold tracking-wide transition-all disabled:opacity-50"
                        >
                          {loadingMore ? (
                            <div className="flex items-center gap-3">
                              <Loader2 className="w-3 h-3 animate-spin text-cyan-500" />
                              Synchronizing Stream...
                            </div>
                          ) : (
                            `Load More Records (${insights.length} / ${total})`
                          )}
                        </button>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-20 py-10 border-t border-white/5 flex flex-col items-center gap-4">
              <div className="flex items-center gap-4 px-8 py-3 bg-[#0E0E0E] border border-white/5 rounded-full shadow-2xl">
                  <div className="relative">
                    <div className="w-2 h-2 rounded-full bg-[#8B5CF6]" />
                    <div className="absolute top-0 left-0 w-2 h-2 rounded-full bg-[#8B5CF6] animate-ping" />
                  </div>
                  <span className="text-[10px] font-medium text-slate-600 tracking-wider">High-Density Intelligence Ledger Established</span>
              </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
