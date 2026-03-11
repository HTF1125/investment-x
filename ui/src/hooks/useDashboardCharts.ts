'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import type { ChartMeta } from '@/types/chart';

export interface GroupedCategory {
  category: string;
  charts: ChartMeta[];
}

export interface DashboardChartsState {
  allCharts: ChartMeta[];
  filteredCharts: ChartMeta[];
  groupedCharts: GroupedCategory[];
  categories: string[];
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  activeCategory: string;
  setActiveCategory: (cat: string) => void;
  favorites: Set<string>;
  toggleFavorite: (id: string) => void;
  setChartOrder: React.Dispatch<React.SetStateAction<ChartMeta[]>>;
  isOrderDirty: boolean;
  resetOrder: () => void;
  removeChart: (id: string) => void;
  updateChartOptimistic: (id: string, patch: Partial<ChartMeta>) => void;
}

export function useDashboardCharts(
  chartsByCategory: Record<string, ChartMeta[]>
): DashboardChartsState {
  const { user } = useAuth();
  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const currentUserId = user?.id || null;

  // -- Chart data --
  const [localCharts, setLocalCharts] = useState<ChartMeta[]>([]);
  const [originalCharts, setOriginalCharts] = useState<ChartMeta[]>([]);

  useEffect(() => {
    const uniqueMap = new Map<string, ChartMeta>();
    Object.values(chartsByCategory || {}).forEach(charts => {
      if (Array.isArray(charts)) {
        charts.forEach(c => uniqueMap.set(c.id, c));
      }
    });
    const sorted = Array.from(uniqueMap.values())
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
    setLocalCharts(sorted);
    setOriginalCharts([...sorted]);
  }, [chartsByCategory]);

  // -- Search / Filter --
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim().toLowerCase()), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const allFilteredCharts = useMemo(() => {
    let result = [...localCharts];
    if (debouncedSearch) {
      result = result.filter(c =>
        `${c.name || ''}|${c.category || ''}|${c.description || ''}`.toLowerCase().includes(debouncedSearch)
      );
    }
    if (!isOwner && !isAdminRole) {
      result = result.filter(c =>
        c.public !== false || (currentUserId && String(c.created_by_user_id) === String(currentUserId))
      );
    }
    return result;
  }, [localCharts, isOwner, isAdminRole, currentUserId, debouncedSearch]);

  const filteredCharts = useMemo(() => {
    if (activeCategory === 'all') return allFilteredCharts;
    return allFilteredCharts.filter(c => (c.category || 'Uncategorized') === activeCategory);
  }, [allFilteredCharts, activeCategory]);

  const groupedCharts = useMemo(() => {
    const groups = new Map<string, ChartMeta[]>();
    for (const chart of allFilteredCharts) {
      const cat = chart.category || 'Uncategorized';
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat)!.push(chart);
    }
    return Array.from(groups.entries()).map(([category, charts]) => ({ category, charts }));
  }, [allFilteredCharts]);

  const categories = useMemo(() => groupedCharts.map(g => g.category), [groupedCharts]);

  // -- Favorites --
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    if (typeof window === 'undefined') return new Set<string>();
    try {
      const saved = localStorage.getItem('ix-chart-favorites');
      return saved ? new Set(JSON.parse(saved)) : new Set<string>();
    } catch { return new Set<string>(); }
  });

  const toggleFavorite = useCallback((id: string) => {
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      localStorage.setItem('ix-chart-favorites', JSON.stringify(Array.from(next)));
      return next;
    });
  }, []);

  // -- Order tracking --
  const isOrderDirty = useMemo(() => {
    if (localCharts.length !== originalCharts.length) return false;
    return localCharts.some((c, i) => c.id !== originalCharts[i]?.id);
  }, [localCharts, originalCharts]);

  const resetOrder = useCallback(() => {
    setLocalCharts([...originalCharts]);
  }, [originalCharts]);

  // -- Optimistic helpers --
  const removeChart = useCallback((id: string) => {
    setLocalCharts(prev => prev.filter(c => c.id !== id));
    setOriginalCharts(prev => prev.filter(c => c.id !== id));
  }, []);

  const updateChartOptimistic = useCallback((id: string, patch: Partial<ChartMeta>) => {
    setLocalCharts(prev => prev.map(c => c.id === id ? { ...c, ...patch } : c));
  }, []);

  return {
    allCharts: localCharts,
    filteredCharts,
    groupedCharts,
    categories,
    searchQuery,
    setSearchQuery,
    activeCategory,
    setActiveCategory,
    favorites,
    toggleFavorite,
    setChartOrder: setLocalCharts,
    isOrderDirty,
    resetOrder,
    removeChart,
    updateChartOptimistic,
  };
}
