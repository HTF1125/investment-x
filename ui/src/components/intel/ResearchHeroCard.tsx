'use client';

import { BookOpen, Shield, FileText, Zap } from 'lucide-react';

interface ResearchHeroCardProps {
  selectedDate: string | null;
  riskCount: number;
  avgScore: number | null;
  sectionCount: number;
  takeawayCount: number;
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

function scoreColorClass(score: number): string {
  if (score >= 8) return 'text-rose-400 bg-rose-500/8 border-rose-500/20';
  if (score >= 6) return 'text-amber-400 bg-amber-500/8 border-amber-500/20';
  return 'text-emerald-400 bg-emerald-500/8 border-emerald-500/20';
}

export default function ResearchHeroCard({
  selectedDate,
  riskCount,
  avgScore,
  sectionCount,
  takeawayCount,
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
              Macro Research Briefing
            </h2>
            <p className="text-[10px] font-mono text-muted-foreground/50 mt-0.5">
              {formatReportDate(selectedDate)}
            </p>
          </div>
        </div>

        {/* Right: Stat badges */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {riskCount > 0 && avgScore !== null && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[10px] font-mono font-bold tabular-nums ${scoreColorClass(avgScore)}`}
            >
              <Shield className="w-3 h-3" />
              {avgScore.toFixed(1)} avg
            </span>
          )}
          {riskCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <Shield className="w-3 h-3 opacity-40" />
              {riskCount} risks
            </span>
          )}
          {sectionCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <FileText className="w-3 h-3 opacity-40" />
              {sectionCount} sections
            </span>
          )}
          {takeawayCount > 0 && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-muted-foreground/50">
              <Zap className="w-3 h-3 opacity-40" />
              {takeawayCount} takeaways
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
