'use client';

import { Radio, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import type { IntelState } from '@/hooks/useIntelState';

function formatReportDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

interface IntelHeaderProps {
  state: IntelState;
}

export default function IntelHeader({ state }: IntelHeaderProps) {
  const { activeTab, dateIdx, setDateIdx, selectedDate, hasPrev, hasNext } = state;

  const showDateNav = activeTab === 'research';

  return (
    <div className="h-9 px-4 sm:px-5 lg:px-6 border-b border-border/25 flex items-center justify-between shrink-0 bg-background">
      <div className="flex items-center gap-2">
        <Radio className="w-3.5 h-3.5 text-primary" />
        <span className="text-[11px] font-semibold text-foreground uppercase tracking-wide">
          Intel Center
        </span>
      </div>

      {showDateNav && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => setDateIdx(dateIdx + 1)}
            disabled={!hasPrev}
            className="p-1 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20 disabled:cursor-default"
            aria-label="Older report"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <div className="flex items-center gap-1.5 min-w-[140px] justify-center">
            <Calendar className="w-3 h-3 text-muted-foreground/40" />
            <span className="text-[11px] font-mono text-muted-foreground/70 tabular-nums">
              {selectedDate ? formatReportDate(selectedDate) : '---'}
            </span>
          </div>
          <button
            onClick={() => setDateIdx(dateIdx - 1)}
            disabled={!hasNext}
            className="p-1 rounded-md text-muted-foreground/40 hover:text-muted-foreground hover:bg-primary/10 transition-colors disabled:opacity-20 disabled:cursor-default"
            aria-label="Newer report"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
