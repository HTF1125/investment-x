'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import AppShell from '@/components/AppShell';
import NavigatorShell from '@/components/NavigatorShell';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, apiFetchJson } from '@/lib/api';
import { useResponsiveSidebar } from '@/lib/hooks/useResponsiveSidebar';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { FileText, Search, Upload, Trash2, Download, File, Loader2 } from 'lucide-react';

/* ---------- Types ---------- */

interface InsightItem {
  id: string;
  published_date: string | null;
  issuer: string | null;
  name: string | null;
  status: string | null;
  summary: string | null;
  created: string;
}

interface PaginatedInsights {
  items: InsightItem[];
  total: number;
}

/* ---------- Page ---------- */

export default function InsightsPage() {
  const { user } = useAuth();
  const isAdmin = !!user && (user.role === 'owner' || user.role === 'admin' || user.is_admin);
  const { sidebarOpen, toggleSidebar } = useResponsiveSidebar();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Fetch insights list
  const { data, isLoading } = useQuery<PaginatedInsights>({
    queryKey: ['insights', debouncedSearch],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set('limit', '200');
      if (debouncedSearch) params.set('q', debouncedSearch);
      return apiFetchJson<PaginatedInsights>(`/api/insights?${params}`);
    },
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  // Load PDF blob when selection changes
  useEffect(() => {
    if (!selectedId) {
      setPdfUrl(null);
      return;
    }

    let revoked = false;
    setPdfLoading(true);

    apiFetch(`/api/insights/${selectedId}/pdf`, { timeoutMs: 60000 })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load PDF');
        return res.blob();
      })
      .then((blob) => {
        if (revoked) return;
        const url = URL.createObjectURL(blob);
        setPdfUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return url;
        });
      })
      .catch(() => {
        if (!revoked) setPdfUrl(null);
      })
      .finally(() => {
        if (!revoked) setPdfLoading(false);
      });

    return () => {
      revoked = true;
    };
  }, [selectedId]);

  // Revoke blob URL on unmount
  useEffect(() => {
    return () => {
      setPdfUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, []);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: globalThis.File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/api/insights/upload', {
        method: 'POST',
        body: formData,
        timeoutMs: 120000,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Upload failed');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['insights'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/insights/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Delete failed');
      }
    },
    onSuccess: (_data, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['insights'] });
      if (selectedId === deletedId) {
        setSelectedId(null);
      }
    },
  });

  const handleUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) uploadMutation.mutate(file);
      e.target.value = '';
    },
    [uploadMutation],
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      if (confirm('Delete this document?')) {
        deleteMutation.mutate(id);
      }
    },
    [deleteMutation],
  );

  const handleDownload = useCallback(() => {
    if (!pdfUrl || !selectedId) return;
    const selected = items.find((i) => i.id === selectedId);
    const a = document.createElement('a');
    a.href = pdfUrl;
    a.download = `${selected?.name || 'document'}.pdf`;
    a.click();
  }, [pdfUrl, selectedId, items]);

  const selectedItem = items.find((i) => i.id === selectedId);

  const formStyle = {
    backgroundColor: 'rgb(var(--background))',
    color: 'rgb(var(--foreground))',
  };

  return (
    <AppShell hideFooter>
      <NavigatorShell
        sidebarOpen={sidebarOpen}
        onSidebarToggle={toggleSidebar}
        sidebarIcon={<FileText className="w-3.5 h-3.5 text-sky-400" />}
        sidebarLabel="Insights"
        sidebarHeaderActions={
          isAdmin ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileChange}
              />
              <button
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                title="Upload PDF"
                className="w-5 h-5 rounded flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-foreground/[0.08] transition-colors disabled:opacity-40"
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Upload className="w-3 h-3" />
                )}
              </button>
            </>
          ) : undefined
        }
        sidebarContent={
          <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
            {/* Search */}
            <div className="px-2 py-1.5 border-b border-border/40">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/50" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-6 pl-6 pr-2 rounded-md border border-border/50 text-[11px] bg-transparent text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-sky-500/50 transition-colors"
                  style={formStyle}
                />
              </div>
            </div>

            {/* List */}
            <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar py-0.5">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/40" />
                </div>
              ) : items.length === 0 ? (
                <div className="px-3 py-6 text-center">
                  <File className="w-5 h-5 text-muted-foreground/30 mx-auto mb-1.5" />
                  <p className="text-[11px] text-muted-foreground/50">
                    {debouncedSearch ? 'No results found' : 'No documents yet'}
                  </p>
                </div>
              ) : (
                items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelectedId(item.id)}
                    className={`group w-full text-left px-2.5 py-2 transition-colors border-l-2 hover:bg-foreground/[0.04] ${
                      selectedId === item.id
                        ? 'border-l-sky-400 bg-foreground/[0.06]'
                        : 'border-l-transparent'
                    }`}
                  >
                    <div className="flex items-start gap-1.5">
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-medium text-foreground truncate leading-tight">
                          {item.name || 'Untitled'}
                        </div>
                        <div className="text-[10px] text-muted-foreground/60 truncate mt-0.5">
                          {item.issuer || 'Unknown'}
                        </div>
                        {item.published_date && (
                          <div className="text-[9px] font-mono text-muted-foreground/40 mt-0.5">
                            {item.published_date}
                          </div>
                        )}
                      </div>
                      {isAdmin && (
                        <button
                          onClick={(e) => handleDelete(e, item.id)}
                          className="opacity-0 group-hover:opacity-100 shrink-0 w-5 h-5 rounded flex items-center justify-center text-muted-foreground/40 hover:text-rose-500 hover:bg-rose-500/10 transition-all"
                          title="Delete"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Footer count */}
            {data && (
              <div className="px-2.5 py-1.5 border-t border-border/40 shrink-0">
                <span className="text-[9px] font-mono text-muted-foreground/40">
                  {data.total} document{data.total !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
        }
        topBarLeft={
          <span className="text-sm font-semibold text-foreground">
            {selectedItem ? selectedItem.name || 'Untitled' : 'Research Insights'}
          </span>
        }
        topBarRight={
          selectedId ? (
            <div className="flex items-center gap-1.5">
              {selectedItem?.issuer && (
                <span className="text-[10px] font-mono text-muted-foreground/50">
                  {selectedItem.issuer}
                </span>
              )}
              <button
                onClick={handleDownload}
                title="Download PDF"
                className="p-1.5 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-foreground/[0.06] transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : undefined
        }
        mainClassName="overflow-hidden"
      >
        {/* PDF viewer */}
        <div className="h-full w-full flex items-center justify-center">
          {!selectedId ? (
            <div className="text-center">
              <FileText className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground/50">Select a document to view</p>
              <p className="text-[11px] text-muted-foreground/30 mt-1">
                {data?.total ?? 0} document{(data?.total ?? 0) !== 1 ? 's' : ''} available
              </p>
            </div>
          ) : pdfLoading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground/30" />
              <p className="text-[11px] text-muted-foreground/40">Loading PDF...</p>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title={selectedItem?.name || 'PDF Viewer'}
            />
          ) : (
            <div className="text-center">
              <FileText className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground/50">Failed to load PDF</p>
            </div>
          )}
        </div>
      </NavigatorShell>
    </AppShell>
  );
}
