'use client';

import { Suspense, lazy, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import AppShell from '@/components/AppShell';
import AuthGuard from '@/components/AuthGuard';
import PageSkeleton from '@/components/PageSkeleton';
import MacroBriefFeed from '@/components/MacroBriefFeed';
import NewsFeed from '@/components/NewsFeed';
import TelegramFeed from '@/components/TelegramFeed';
import IntelTabs from '@/components/intel/IntelTabs';
import IntelHeader from '@/components/intel/IntelHeader';
import IntelSidePanel from '@/components/intel/IntelSidePanel';
import ResearchHeroCard from '@/components/intel/ResearchHeroCard';
import { useIntelState } from '@/hooks/useIntelState';
import { apiFetchJson } from '@/lib/api';
import {
  parseRiskScorecard,
  parseBriefingSections,
  parseTakeaways,
} from '@/components/MacroBriefFeed';
import type { ReportData } from '@/components/MacroBriefFeed';
import { Loader2 } from 'lucide-react';

const WartimeContent = lazy(() =>
  import('@/components/WartimeContent').then((m) => ({ default: m.WartimeContent })),
);
const StressTestContent = lazy(() =>
  import('@/components/StressTestContent').then((m) => ({ default: m.StressTestContent })),
);

function LazyFallback({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground/40" />
        <span className="text-[10px] font-mono text-muted-foreground/50 uppercase tracking-wider">
          {label}
        </span>
      </div>
    </div>
  );
}

function ResearchTab({ state }: { state: ReturnType<typeof useIntelState> }) {
  const { selectedDate, dateIdx, setDateIdx } = state;

  // Query the report data for the hero card stats
  const { data: report } = useQuery<ReportData>({
    queryKey: ['research-report', selectedDate],
    queryFn: () => apiFetchJson<ReportData>(`/api/news/reports/${selectedDate}`),
    enabled: !!selectedDate,
    staleTime: 300_000,
  });

  const riskItems = useMemo(
    () => (report?.risk_scorecard ? parseRiskScorecard(report.risk_scorecard) : []),
    [report?.risk_scorecard],
  );
  const briefingSections = useMemo(
    () => (report?.briefing ? parseBriefingSections(report.briefing) : []),
    [report?.briefing],
  );
  const takeaways = useMemo(
    () => (report?.takeaways ? parseTakeaways(report.takeaways) : []),
    [report?.takeaways],
  );
  const avgScore =
    riskItems.length > 0
      ? riskItems.reduce((sum, r) => sum + r.score, 0) / riskItems.length
      : null;

  return (
    <>
      {/* Hero summary card */}
      <div className="px-5 md:px-8 pt-5 max-w-[1600px] mx-auto">
        <ResearchHeroCard
          selectedDate={selectedDate}
          riskCount={riskItems.length}
          avgScore={avgScore}
          sectionCount={briefingSections.length}
          takeawayCount={takeaways.length}
        />
      </div>

      {/* MacroBriefFeed with external date control */}
      <MacroBriefFeed
        hideHeader
        externalDateIdx={dateIdx}
        onDateIdxChange={setDateIdx}
      />
    </>
  );
}

export default function IntelPage() {
  const state = useIntelState();

  return (
    <AuthGuard>
      <Suspense
        fallback={
          <AppShell hideFooter>
            <PageSkeleton label="Loading intel" />
          </AppShell>
        }
      >
        <AppShell hideFooter>
          <div className="h-[calc(100vh-48px)] flex flex-col min-h-0 overflow-hidden">
            {/* Tab bar */}
            <IntelTabs activeTab={state.activeTab} setActiveTab={state.setActiveTab} />

            {/* Header with date nav + side panel toggle */}
            <IntelHeader state={state} />

            {/* Content area: main + optional side panel */}
            <div className="flex-1 flex min-h-0 overflow-hidden">
              {/* Main content */}
              <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
                {state.activeTab === 'research' && <ResearchTab state={state} />}

                {state.activeTab === 'news' && (
                  <div className="h-full">
                    <NewsFeed embedded />
                  </div>
                )}

                {state.activeTab === 'signals' && (
                  <div className="h-full">
                    <TelegramFeed embedded />
                  </div>
                )}

                {state.activeTab === 'wartime' && (
                  <Suspense fallback={<LazyFallback label="Loading wartime analysis" />}>
                    <div className="flex-1 overflow-y-auto">
                      <WartimeContent embedded />
                    </div>
                  </Suspense>
                )}

                {state.activeTab === 'stress' && (
                  <Suspense fallback={<LazyFallback label="Loading stress analysis" />}>
                    <div className="flex-1 overflow-y-auto">
                      <StressTestContent embedded />
                    </div>
                  </Suspense>
                )}
              </div>

              {/* Collapsible side panel */}
              <IntelSidePanel state={state} />
            </div>
          </div>
        </AppShell>
      </Suspense>
    </AuthGuard>
  );
}
