import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground px-6">
      <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground/50 mb-4">
        Error
      </p>
      <h1 className="text-7xl font-mono font-bold tracking-tight mb-3">
        404
      </h1>
      <p className="text-sm text-muted-foreground mb-8">
        Page not found
      </p>
      <Link
        href="/"
        className="px-5 py-2 rounded-[var(--radius)] bg-foreground text-background text-xs font-medium tracking-wide transition-opacity hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-foreground/25 focus:ring-offset-2 focus:ring-offset-background"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
