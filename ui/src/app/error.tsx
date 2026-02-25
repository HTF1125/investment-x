'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 p-8 text-center">
      <div className="text-lg font-semibold text-rose-400">Something went wrong</div>
      <div className="text-sm text-muted-foreground max-w-lg">
        {error.message || 'An unexpected error occurred.'}
      </div>
      <button
        type="button"
        onClick={reset}
        className="mt-2 px-5 py-2 rounded-lg border border-border bg-secondary/20 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
