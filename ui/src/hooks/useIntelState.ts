'use client';

import { useState, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiFetchJson } from '@/lib/api';

export type IntelTab = 'research' | 'wartime' | 'stress';

export interface ReportDateMeta {
  date: string;
  has_briefing: boolean;
}

export interface IntelState {
  activeTab: IntelTab;
  setActiveTab: (tab: IntelTab) => void;

  reportDates: ReportDateMeta[];
  datesLoading: boolean;
  datesError: boolean;
  dateIdx: number;
  setDateIdx: (idx: number) => void;
  selectedDate: string | null;
  hasPrev: boolean;
  hasNext: boolean;
}

export function useIntelState(): IntelState {
  const [activeTab, setActiveTab] = useState<IntelTab>('research');
  const [dateIdx, setDateIdx] = useState(0);

  const {
    data: reportDates = [],
    isLoading: datesLoading,
    isError: datesError,
  } = useQuery<ReportDateMeta[]>({
    queryKey: ['research-reports'],
    queryFn: () => apiFetchJson<ReportDateMeta[]>('/api/news/reports'),
    staleTime: 120_000,
  });

  const selectedDate = reportDates[dateIdx]?.date ?? null;
  const hasPrev = dateIdx < reportDates.length - 1;
  const hasNext = dateIdx > 0;

  // Keyboard shortcuts: [ / ] for date navigation on Research tab
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (activeTab !== 'research') return;
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;

      if (e.key === '[') {
        e.preventDefault();
        setDateIdx((i) => Math.min(i + 1, reportDates.length - 1));
      } else if (e.key === ']') {
        e.preventDefault();
        setDateIdx((i) => Math.max(i - 1, 0));
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [activeTab, reportDates.length]);

  return {
    activeTab,
    setActiveTab,
    reportDates,
    datesLoading,
    datesError,
    dateIdx,
    setDateIdx,
    selectedDate,
    hasPrev,
    hasNext,
  };
}
