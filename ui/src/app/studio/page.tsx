'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import CustomChartEditor from '@/components/CustomChartEditor';
import AppShell from '@/components/AppShell';
import { Loader2 } from 'lucide-react';

function StudioContent() {
  const searchParams = useSearchParams();
  const chartId = searchParams.get('chartId');
  const isNew = searchParams.get('new') === 'true';

  return (
    <CustomChartEditor
      mode="standalone"
      initialChartId={isNew ? null : chartId}
    />
  );
}

export default function StudioPage() {
  return (
    <AppShell hideFooter>
      <div className="h-[calc(100vh-40px)] min-h-0 overflow-hidden">
        <Suspense
          fallback={
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
            </div>
          }
        >
          <StudioContent />
        </Suspense>
      </div>
    </AppShell>
  );
}
