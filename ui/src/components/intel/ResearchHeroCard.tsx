'use client';

import { BookOpen, FileText, Globe } from 'lucide-react';

interface ResearchHeroCardProps {
  selectedDate: string | null;
  sectionCount: number;
  translationCount: number;
}

function formatReportDate(dateStr: string): string {
  try {
    const [y, m, d] = dateStr.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export default function ResearchHeroCard({
  selectedDate,
  sectionCount,
  translationCount,
}: ResearchHeroCardProps) {
  if (!selectedDate) return null;

  return (
    <div className="panel-card px-4 py-3.5 animate-fade-in">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Left: Title + date */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground truncate">
              Macro Outlook
            </h2>
            <p className="text-[10px] font-mono text-muted-foreground/50 mt-0.5">
              {formatReportDate(selectedDate)}
            </p>
          </div>
        </div>

        {/* Right: Stat badges */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {sectionCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <FileText className="w-3 h-3 opacity-40" />
              {sectionCount} sections
            </span>
          )}
          {translationCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <Globe className="w-3 h-3 opacity-40" />
              {translationCount + 1} languages
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
