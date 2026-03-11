'use client';

import { useState, useCallback } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { apiFetch, apiFetchJson, getDirectApiBase } from '@/lib/api';
import type { ChartMeta } from '@/types/chart';

export interface DashboardActionsState {
  refreshChart: (id: string) => void;
  deleteChart: (id: string) => void;
  copyChart: (id: string) => void;
  toggleVisibility: (id: string, status: boolean) => void;
  saveOrder: (charts: ChartMeta[]) => void;
  refreshAll: () => void;
  exportPDF: () => void;
  exportHTML: () => void;
  refreshingChartIds: Record<string, boolean>;
  copySignals: Record<string, number>;
  isRefreshing: boolean;
  exporting: boolean;
  exportingHtml: boolean;
  isReorderSaving: boolean;
  deleteTarget: { id: string; name: string } | null;
  setDeleteTarget: (t: { id: string; name: string } | null) => void;
  confirmDelete: () => void;
}

export function useDashboardActions(opts: {
  onChartDeleted?: (id: string) => void;
  onVisibilityToggled?: (id: string, status: boolean) => void;
  onOrderSaved?: () => void;
}): DashboardActionsState {
  const queryClient = useQueryClient();

  const [refreshingChartIds, setRefreshingChartIds] = useState<Record<string, boolean>>({});
  const [copySignals, setCopySignals] = useState<Record<string, number>>({});
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportingHtml, setExportingHtml] = useState(false);

  // -- Visibility --
  const toggleVisibilityMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: boolean }) => {
      return apiFetchJson(`/api/custom/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ public: status }),
      });
    },
    onMutate: ({ id, status }) => {
      opts.onVisibilityToggled?.(id, status);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });

  // -- Reorder --
  const reorderMutation = useMutation({
    mutationFn: async (items: ChartMeta[]) => {
      return apiFetchJson('/api/custom/reorder', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: items.map(c => ({ id: c.id })) }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
      opts.onOrderSaved?.();
    },
  });

  // -- Refresh single chart --
  const refreshChartMutation = useMutation({
    mutationFn: async (chartId: string) => {
      return apiFetchJson(`/api/custom/${chartId}/refresh`, { method: 'POST' });
    },
    onSuccess: (data: any, chartId) => {
      if (data?.figure) {
        queryClient.setQueryData(['chart-figure', chartId], data.figure);
      } else {
        queryClient.invalidateQueries({ queryKey: ['chart-figure', chartId], exact: true });
      }
      setRefreshingChartIds(prev => { const n = { ...prev }; delete n[chartId]; return n; });
    },
    onError: (_err, chartId) => {
      setRefreshingChartIds(prev => { const n = { ...prev }; delete n[chartId]; return n; });
    },
  });

  // -- Delete chart --
  const deleteChartMutation = useMutation({
    mutationFn: async (chartId: string) => {
      await apiFetchJson(`/api/custom/${chartId}`, { method: 'DELETE' });
      return chartId;
    },
    onSuccess: (chartId) => {
      opts.onChartDeleted?.(chartId);
      queryClient.removeQueries({ queryKey: ['chart-figure', chartId] });
      queryClient.setQueryData(['dashboard-summary'], (old: any) => {
        if (!old?.charts_by_category) return old;
        const updated: Record<string, any[]> = {};
        for (const [cat, charts] of Object.entries(old.charts_by_category as Record<string, any[]>)) {
          const filtered = charts.filter((c: any) => c.id !== chartId);
          if (filtered.length > 0) updated[cat] = filtered;
        }
        return { ...old, charts_by_category: updated, categories: Object.keys(updated) };
      });
      queryClient.invalidateQueries({ queryKey: ['custom-charts'] });
    },
  });

  // -- Refresh all --
  const refreshAllMutation = useMutation({
    mutationFn: async () => {
      const res = await apiFetch('/api/task/refresh-charts', { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to trigger chart refresh');
      }
      return res.json() as Promise<{ task_id?: string }>;
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
    },
  });

  // -- Handlers --
  const refreshChart = useCallback((id: string) => {
    setRefreshingChartIds(prev => ({ ...prev, [id]: true }));
    refreshChartMutation.mutate(id);
  }, [refreshChartMutation]);

  const copyChart = useCallback((id: string) => {
    setCopySignals(prev => ({ ...prev, [id]: (prev[id] || 0) + 1 }));
  }, []);

  const deleteChart = useCallback((id: string) => {
    // This just sets the target — actual deletion via confirmDelete
    // The caller should resolve the chart name
  }, []);

  const confirmDelete = useCallback(() => {
    if (!deleteTarget) return;
    deleteChartMutation.mutate(deleteTarget.id);
    setDeleteTarget(null);
  }, [deleteTarget, deleteChartMutation]);

  const toggleVisibility = useCallback((id: string, status: boolean) => {
    toggleVisibilityMutation.mutate({ id, status });
  }, [toggleVisibilityMutation]);

  const saveOrder = useCallback((charts: ChartMeta[]) => {
    reorderMutation.mutate(charts);
  }, [reorderMutation]);

  const refreshAll = useCallback(async () => {
    if (refreshAllMutation.isPending) return;
    try {
      await refreshAllMutation.mutateAsync();
    } catch {
      // TaskNotifications handles backend errors
    }
  }, [refreshAllMutation]);

  const triggerBlobDownload = useCallback((blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }, []);

  const exportPDF = useCallback(async () => {
    if (exporting) return;
    setExporting(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/pdf`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      triggerBlobDownload(blob, `InvestmentX_Report_${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (err) {
      console.error('PDF export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExporting(false);
    }
  }, [exporting, queryClient, triggerBlobDownload]);

  const exportHTML = useCallback(async () => {
    if (exportingHtml) return;
    setExportingHtml(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('items', JSON.stringify([]));
      formData.append('theme', 'light');
      const res = await fetch(`${getDirectApiBase()}/api/custom/html`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: 'include',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      triggerBlobDownload(blob, `InvestmentX_Portfolio_${new Date().toISOString().slice(0, 10)}.html`);
    } catch (err) {
      console.error('HTML export error:', err);
    } finally {
      queryClient.invalidateQueries({ queryKey: ['task-processes'] });
      setExportingHtml(false);
    }
  }, [exportingHtml, queryClient, triggerBlobDownload]);

  return {
    refreshChart,
    deleteChart,
    copyChart,
    toggleVisibility,
    saveOrder,
    refreshAll,
    exportPDF,
    exportHTML,
    refreshingChartIds,
    copySignals,
    isRefreshing: refreshAllMutation.isPending,
    exporting,
    exportingHtml,
    isReorderSaving: reorderMutation.isPending,
    deleteTarget,
    setDeleteTarget,
    confirmDelete,
  };
}
