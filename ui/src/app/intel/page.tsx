'use client';

import { Suspense, lazy } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AppShell from '@/components/AppShell';
import PageSkeleton from '@/components/PageSkeleton';
import MacroBriefFeed from '@/components/MacroBriefFeed';
import IntelTabs from '@/components/intel/IntelTabs';
import IntelHeader from '@/components/intel/IntelHeader';
import { useIntelState } from '@/hooks/useIntelState';
import { Loader2 } from 'lucide-react';

const tabTransition = { duration: 0.15, ease: 'easeOut' } as const;
const tabInitial = { opacity: 0 } as const;
const tabAnimate = { opacity: 1 } as const;
const tabExit = { opacity: 0 } as const;

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

export default function IntelPage() {
  const state = useIntelState();

  return (
    <Suspense
      fallback={
        <AppShell hideFooter>
          <PageSkeleton label="Loading intel" />
        </AppShell>
      }
    >
      <AppShell hideFooter>
        <div className="h-[calc(100vh-48px)] flex flex-col min-h-0 overflow-hidden">
          <IntelTabs activeTab={state.activeTab} setActiveTab={state.setActiveTab} />
          <IntelHeader state={state} />

          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
            <AnimatePresence mode="wait">
              {state.activeTab === 'research' && (
                <motion.div key="research" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                  <MacroBriefFeed
                    hideHeader
                    externalDateIdx={state.dateIdx}
                    onDateIdxChange={state.setDateIdx}
                  />
                </motion.div>
              )}

              {state.activeTab === 'wartime' && (
                <motion.div key="wartime" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                  <Suspense fallback={<LazyFallback label="Loading wartime analysis" />}>
                    <WartimeContent embedded />
                  </Suspense>
                </motion.div>
              )}

              {state.activeTab === 'stress' && (
                <motion.div key="stress" initial={tabInitial} animate={tabAnimate} exit={tabExit} transition={tabTransition} className="h-full">
                  <Suspense fallback={<LazyFallback label="Loading stress analysis" />}>
                    <StressTestContent embedded />
                  </Suspense>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </AppShell>
    </Suspense>
  );
}
