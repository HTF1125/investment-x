'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[GlobalError]', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground px-6">
      <p className="text-[11.5px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-4">
        Runtime Error
      </p>
      <h1 className="text-2xl font-semibold tracking-tight mb-2">
        Something went wrong
      </h1>
      <p className="text-sm text-muted-foreground max-w-md text-center mb-8">
        {error.message || 'An unexpected error occurred.'}
      </p>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="px-5 py-2 rounded-[var(--radius)] bg-foreground text-background text-xs font-medium tracking-wide transition-opacity hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-foreground/25 focus:ring-offset-2 focus:ring-offset-background"
        >
          Try again
        </button>
        <Link
          href="/"
          className="px-5 py-2 rounded-[var(--radius)] border border-border/50 text-xs text-muted-foreground font-medium tracking-wide transition-colors hover:text-foreground focus:outline-none focus:ring-2 focus:ring-foreground/25 focus:ring-offset-2 focus:ring-offset-background"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
