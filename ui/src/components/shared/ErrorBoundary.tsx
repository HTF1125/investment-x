'use client';

import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/** Detect stale code-split chunk failures caused by a redeploy. When a user
 * has an old tab open and navigates to a route whose dynamic chunk name has
 * changed, Webpack rejects the import with one of these errors. The right
 * response is a hard reload so the browser fetches the fresh chunk manifest.
 */
function isChunkLoadError(error: unknown): boolean {
  if (!error) return false;
  const err = error as { name?: string; message?: string; code?: string };
  const msg = err.message || '';
  return (
    err.name === 'ChunkLoadError' ||
    err.code === 'CSS_CHUNK_LOAD_FAILED' ||
    /Loading chunk [\w-]+ failed/i.test(msg) ||
    /Loading CSS chunk [\w-]+ failed/i.test(msg) ||
    /ChunkLoadError/.test(msg) ||
    /Failed to fetch dynamically imported module/i.test(msg)
  );
}

/** Hard-reload once per session on stale-chunk errors. The sessionStorage
 * flag prevents an infinite reload loop if the new build is ALSO broken. */
function reloadOnceForStaleChunk() {
  if (typeof window === 'undefined') return;
  const key = '__ix_chunk_reload_at';
  const now = Date.now();
  try {
    const last = Number(sessionStorage.getItem(key) || '0');
    if (now - last < 10_000) return; // already reloaded in the last 10s — bail
    sessionStorage.setItem(key, String(now));
  } catch {
    /* storage blocked — still attempt reload */
  }
  window.location.reload();
}

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private onWindowError = (event: ErrorEvent) => {
    if (isChunkLoadError(event.error) || isChunkLoadError(event.message)) {
      event.preventDefault();
      reloadOnceForStaleChunk();
    }
  };

  private onUnhandledRejection = (event: PromiseRejectionEvent) => {
    if (isChunkLoadError(event.reason)) {
      event.preventDefault();
      reloadOnceForStaleChunk();
    }
  };

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  componentDidMount() {
    if (typeof window !== 'undefined') {
      window.addEventListener('error', this.onWindowError);
      window.addEventListener('unhandledrejection', this.onUnhandledRejection);
    }
  }

  componentWillUnmount() {
    if (typeof window !== 'undefined') {
      window.removeEventListener('error', this.onWindowError);
      window.removeEventListener('unhandledrejection', this.onUnhandledRejection);
    }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    if (isChunkLoadError(error)) {
      reloadOnceForStaleChunk();
      return;
    }
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Stale chunk errors trigger a reload in componentDidCatch — render a
      // minimal placeholder while the reload is in flight so the user doesn't
      // flash the generic fallback.
      if (isChunkLoadError(this.state.error)) {
        return (
          <div className="flex items-center justify-center min-h-[200px]">
            <span className="text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground animate-pulse">
              Updating…
            </span>
          </div>
        );
      }

      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] gap-3 p-6 text-center">
          <div className="text-sm font-semibold text-destructive">Something went wrong</div>
          <div className="text-xs text-muted-foreground max-w-md">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </div>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-2 px-4 py-1.5 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
