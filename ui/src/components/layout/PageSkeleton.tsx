'use client';

import { Loader2 } from 'lucide-react';

/**
 * Lightweight loading fallback for Suspense boundaries on data-fetching pages.
 */
export default function PageSkeleton({ label }: { label?: string }) {
  return (
    <div className="h-[calc(100vh-3rem)] flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-primary/40" />
        {label && (
          <span className="text-[11px] text-muted-foreground/50 tracking-widest uppercase">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
