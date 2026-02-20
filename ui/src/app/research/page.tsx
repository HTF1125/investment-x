'use client';

import { useState, useCallback, useMemo } from 'react';
import AppShell from '@/components/AppShell';
import { apiFetch, apiFetchJson } from '@/lib/api';
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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import TaskNotifications from '@/components/TaskNotifications';

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
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [skip, setSkip] = useState(0);
  const [filterIssuer, setFilterIssuer] = useState('all');
  const [isDragging, setIsDragging] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Insight>>({});
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' | 'loading' } | null>(null);

  const showToast = useCallback((msg: string, type: 'success' | 'error' | 'loading') => {
    setToast({ msg, type });
    if (type !== 'loading') {
      setTimeout(() => setToast(null), 3000);
    }
  }, []);

  const LIMIT = 50;

  // React Query for Insights
  const { data, isLoading, isPlaceholderData } = useQuery({
    queryKey: ['insights', skip, search],
    queryFn: () => {
        const url = `/api/insights?skip=${skip}&limit=${LIMIT}${search ? `&q=${encodeURIComponent(search)}` : ''}`;
        return apiFetchJson<PaginatedResponse>(url);
    },
    placeholderData: (previousData) => previousData, // Keep previous data while fetching new
    staleTime: 5 * 60 * 1000, // Data is considered fresh for 5 minutes
  });

  const insights = data?.items || [];
  const total = data?.total || 0;

  // Mutation for file uploads
  const uploadMutation = useMutation({
    mutationFn: async (files: FileList) => {
      // 1. Start Task (if needed, this might be handled by a separate service or component)
      try {
        await apiFetch('/api/task/process/start?name=Intelligence%20Ingestion', { method: 'POST' });
      } catch (e) {
        console.warn('Failed to start ingestion task:', e);
      }
      
      // 2. Upload Files
      let successCount = 0;
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        try {
          const response = await fetch('/api/insights/upload', {
             method: 'POST',
             body: formData,
             headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
          });
          if (response.ok) {
            successCount++;
          }
        } catch (err) { console.error(`Failed to upload file ${files[i].name}:`, err); }
      }
      return successCount;
    },
    onSuccess: () => {
        // Invalidate insights query to refetch the list and show new uploads
        queryClient.invalidateQueries({ queryKey: ['insights'] });
    },
    onError: (error) => {
      console.error('Upload failed:', error);
    }
  });

  // Mutation for deleting an insight
  const deleteMutation = useMutation({
    mutationFn: async ({ id }: { id: string }) => {
        await apiFetch(`/api/insights/${id}`, { method: 'DELETE' });
    },
    onMutate: () => {
        showToast('Executing deletion command...', 'loading');
    },
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['insights'] });
        showToast('Record purged successfully', 'success');
    },
    onError: (error: any) => {
      console.error('Delete failed:', error);
      showToast(error.message || 'Purge failed', 'error');
    }
  });

  // Mutation for updating an insight
  const updateMutation = useMutation({
    mutationFn: async ({ id, data: updateData }: { id: string; data: Partial<Insight> }) => {
        const res = await apiFetchJson(`/api/insights/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });
        return res;
    },
    onMutate: () => {
        showToast('Synchronizing analysis ledger...', 'loading');
    },
    onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['insights'] });
        showToast('Update confirmed and committed', 'success');
        setEditingId(null); // Exit editing mode
        setEditForm({}); // Clear edit form
    },
    onError: (error: any) => {
      console.error('Update failed:', error);
      showToast(error.message || 'Synchronization failed', 'error');
    }
  });

  const handleUploadFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    uploadMutation.mutate(files);
  };

  const handleDelete = (id: string, name: string) => {
    if (!confirm(`Permanently delete "${name}"?`)) return;
    deleteMutation.mutate({ id });
  };

  const handleUpdate = () => {
    if (!editingId) return;
    updateMutation.mutate({ id: editingId, data: editForm });
  };

  const loadMore = () => {
    // Only load more if not currently loading and there are more items to fetch
    if (!isLoading && insights.length < total) {
      setSkip(prev => prev + LIMIT);
    }
  };

  const issuers = useMemo(() => Array.from(new Set(insights.map(i => i.issuer).filter(Boolean))) as string[], [insights]);
  const displayedInsights = useMemo(() => insights.filter(i => filterIssuer === 'all' || i.issuer === filterIssuer), [insights, filterIssuer]);

  return (
    <AppShell>
      <div 
        className="relative min-h-[calc(100vh-64px)] bg-background text-foreground antialiased font-sans selection:bg-cyan-500/30"
        onDragOver={(e) => { 
          if (user?.is_admin) {
            e.preventDefault(); 
            setIsDragging(true); 
          }
        }}
        onDragLeave={(e) => { 
          e.preventDefault(); 
          setIsDragging(false); 
        }}
        onDrop={(e) => { 
          e.preventDefault(); 
          setIsDragging(false); 
          if (user?.is_admin) {
            handleUploadFiles(e.dataTransfer.files); 
          }
        }}
      >
        {/* Drag and Drop Overlay */}
        <AnimatePresence>
          {isDragging && user?.is_admin && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[150] bg-sky-500/10 backdrop-blur-sm border-4 border-dashed border-sky-500/50 m-4 rounded-3xl flex flex-col items-center justify-center pointer-events-none"
            >
              <div className="bg-background/80 p-8 rounded-full shadow-2xl mb-4">
                <CloudUpload className="w-16 h-16 text-sky-500 animate-bounce" />
              </div>
              <h2 className="text-2xl font-bold text-sky-400 tracking-tight">Drop PDF to Ingest</h2>
              <p className="text-sky-400/60 font-mono text-xs mt-2 uppercase tracking-widest">Release to begin automated analysis</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="max-w-full px-6 py-8 mx-auto">
          {/* Timeseries Style Header */}
          <div className="flex flex-col gap-8 mb-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 flex items-center justify-center bg-gradient-to-br from-indigo-500 to-sky-600 rounded-xl shadow-lg shadow-indigo-500/20">
                  <Library className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-foreground tracking-tight mb-1">Research Intelligence Library</h1>
                  <p className="text-[11px] font-medium text-muted-foreground tracking-wide">Search, Collect, Manage, and Audit institutional research</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button 
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['insights'] })}
                  className="h-10 px-4 flex items-center gap-2 bg-secondary/50 hover:bg-secondary/80 border border-border/50 rounded-lg text-xs font-medium text-foreground transition-all"
                >
                  <RefreshCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                  <span>Sync</span>
                </button>
                
                {user?.is_admin && (
                  <label className="h-10 px-4 flex items-center gap-2 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/30 rounded-lg text-xs font-bold text-sky-400 cursor-pointer transition-all shadow-lg shadow-sky-500/5">
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload PDF</span>
                    <input type="file" accept=".pdf" multiple className="hidden" onChange={(e) => handleUploadFiles(e.target.files)} />
                  </label>
                )}
              </div>
            </div>

            {/* Prominent Search Bar */}
            <div className="relative">
              <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input 
                type="text" 
                placeholder="Search by analysis name, issuer, summary, or category..." 
                value={search} 
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        setSkip(0);
                        queryClient.invalidateQueries({ queryKey: ['insights'] });
                    }
                }}
                className="w-full h-14 pl-14 pr-6 bg-secondary/10 border border-border/50 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-cyan-500/20 transition-all font-medium"
              />
            </div>
          </div>

          {/* Timeseries Style Table Container */}
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card/30 backdrop-blur-xl shadow-2xl">
            <div className="overflow-x-auto min-h-[400px]">
              <table className="w-full text-left border-collapse table-fixed">
                <thead>
                  <tr className="border-b border-border/50 bg-secondary/30">
                    <th className="px-6 py-4 text-[11px] font-bold text-muted-foreground tracking-wider w-[40%] uppercase">Analysis Identifier</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-muted-foreground tracking-wider w-[20%] uppercase">Provider</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-muted-foreground tracking-wider w-[15%] uppercase">Asset Class</th>
                    <th className="px-4 py-4 text-[11px] font-bold text-muted-foreground tracking-wider w-[12%] uppercase">Published</th>
                    <th className="px-6 py-4 text-[11px] font-bold text-muted-foreground tracking-wider w-[13%] text-right uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/20 font-mono">
                  {isLoading && !isPlaceholderData ? ( // Show skeleton only on initial load or full refresh, not background refresh
                    [1, 2, 3, 4, 5].map(i => ( // Reduced skeleton rows for brevity, adjust as needed
                      <tr key={i} className="animate-pulse">
                        <td colSpan={5} className="px-6 py-5"><div className="h-4 bg-white/5 rounded w-1/3" /></td>
                      </tr>
                    ))
                  ) : displayedInsights.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-8 py-32 text-center text-muted-foreground font-medium text-xs italic opacity-40">No records found in current scan</td>
                    </tr>
                  ) : displayedInsights.map((item) => (
                    <tr key={item.id} className="group hover:bg-secondary/10 transition-all duration-150">
                      {/* Name Column */}
                      <td className="px-6 py-4">
                        {editingId === item.id ? (
                          <input value={editForm.name || ''} onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                            className="w-full h-9 bg-background/60 border border-cyan-500/30 rounded px-4 text-xs text-foreground focus:outline-none" autoFocus />
                        ) : (
                          <div className="flex flex-col gap-1">
                            <a 
                              href={`/api/insights/${item.id}/pdf`} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-[13px] font-bold text-cyan-500/90 hover:text-cyan-400 cursor-pointer tracking-tight truncate block"
                            >
                              {item.name || 'Untitled Analysis'}
                            </a>
                            <span className="text-[11px] text-muted-foreground font-medium truncate opacity-70 group-hover:opacity-100 transition-all">
                              {item.summary || 'Proprietary Research Feed'}
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Source Column */}
                      <td className="px-4 py-4">
                        {editingId === item.id ? (
                          <input value={editForm.issuer || ''} onChange={e => setEditForm({ ...editForm, issuer: e.target.value })}
                            className="w-full h-9 bg-background/60 border border-cyan-500/30 rounded px-4 text-xs text-foreground" />
                        ) : (
                          <div className="flex items-center gap-3">
                            <span className="text-[12px] font-bold text-muted-foreground truncate uppercase">{item.issuer || 'Internal'}</span>
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
                      <td className="px-4 py-4 text-xs font-bold text-muted-foreground tracking-tight">
                        {editingId === item.id ? (
                          <input 
                            type="text" 
                            placeholder="YYYY-MM-DD"
                            value={editForm.published_date || ''} 
                            onChange={e => setEditForm({ ...editForm, published_date: e.target.value })}
                            className="w-full h-9 bg-background/60 border border-cyan-500/30 rounded px-3 text-xs text-foreground font-mono" 
                          />
                        ) : (
                          <span className="font-mono tracking-tighter">
                            {item.published_date ? item.published_date.replace(/-/g, ' ') : '---- -- --'}
                          </span>
                        )}
                      </td>

                      {/* Actions Column */}
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {editingId === item.id ? (
                            <>
                              <button onClick={handleUpdate} disabled={updateMutation.isPending}
                                className="h-8 px-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded transition-all flex items-center justify-center disabled:opacity-50">
                                {updateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-4 h-4" />}
                              </button>
                              <button onClick={() => { setEditingId(null); setEditForm({}); }}
                                className="h-8 px-4 bg-white/5 hover:bg-white/10 text-slate-400 rounded transition-all flex items-center justify-center">
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          ) : (
                            <>
                              {user?.is_admin && (
                                <div className="flex items-center gap-1 transition-all">
                                  <button onClick={() => { setEditingId(item.id); setEditForm(item); }}
                                    className="w-8 h-8 flex items-center justify-center hover:bg-secondary/40 text-muted-foreground hover:text-foreground transition-all rounded-lg"
                                    title="Edit Analysis"
                                  >
                                    <Edit3 className="w-3.5 h-3.5" />
                                  </button>
                                  <button onClick={() => handleDelete(item.id, item.name || '')}
                                    className="w-8 h-8 flex items-center justify-center hover:bg-rose-500/10 text-muted-foreground hover:text-rose-500 transition-all rounded-lg"
                                    title="Delete Analysis"
                                  >
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

                  {/* Load More Row */}
                  {insights.length < total && !search && filterIssuer === 'all' && (
                    <tr>
                      <td colSpan={5} className="px-6 py-10 text-center bg-secondary/5">
                        <button 
                          onClick={loadMore}
                          disabled={isLoading}
                          className="h-11 px-8 bg-secondary/20 hover:bg-secondary/30 text-muted-foreground hover:text-foreground border border-border/50 rounded-xl text-xs font-bold tracking-wide transition-all disabled:opacity-50"
                        >
                          {isLoading ? (
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

          <div className="mt-20 py-10 border-t border-border/50 flex flex-col items-center gap-4">
              <div className="flex items-center gap-4 px-8 py-3 bg-card border border-border/50 rounded-full shadow-2xl">
                  <div className="relative">
                    <div className="w-2 h-2 rounded-full bg-indigo-500" />
                    <div className="absolute top-0 left-0 w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                  </div>
                  <span className="text-[10px] font-bold text-muted-foreground tracking-wider uppercase">High-Density Intelligence Ledger Established</span>
              </div>
          </div>
        </div>
      </div>
      
      {/* Dynamic Progress Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className={`fixed bottom-8 right-8 z-[100] flex items-center gap-4 px-6 py-4 rounded-2xl shadow-3xl backdrop-blur-xl border ${
              toast.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : toast.type === 'error'
                ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                : 'bg-sky-500/10 border-sky-500/20 text-sky-400'
            }`}
          >
            <div className="shrink-0">
              {toast.type === 'loading' ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : toast.type === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <XCircle className="w-5 h-5" />
              )}
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-60">
                {toast.type === 'loading' ? 'In Progress' : 'System Status'}
              </span>
              <span className="text-xs font-bold text-foreground">
                {toast.msg}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </AppShell>
  );
}

