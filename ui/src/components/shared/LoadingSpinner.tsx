'use client';

import { Loader2 } from 'lucide-react';

/**
 * Canonical loading indicator for the whole app.
 *
 * Three size variants share the same look so every loading state reads
 * as the same visual beat:
 *
 *   "inline"  — compact, for inline buttons / row-level feedback
 *   "section" — default, for card / panel / tab content areas
 *   "page"    — full viewport minus navbar, for route-level Suspense
 *
 * Single source of truth — `PageSkeleton`, `regimes/LoadingSpinner`, and
 * `macro/LoadingSpinner` all delegate here so every loading state on the
 * site looks identical.
 */
export type LoadingSpinnerSize = 'inline' | 'section' | 'page';

interface Props {
  label?: string;
  size?: LoadingSpinnerSize;
  className?: string;
}

export default function LoadingSpinner({
  label = 'Loading',
  size = 'section',
  className = '',
}: Props) {
  const wrap =
    size === 'page'
      ? 'h-[calc(100vh-3.5rem)] flex items-center justify-center'
      : size === 'inline'
      ? 'inline-flex items-center justify-center py-2'
      : 'flex items-center justify-center py-10';

  const iconSize =
    size === 'inline' ? 'w-3.5 h-3.5' : size === 'page' ? 'w-5 h-5' : 'w-4 h-4';

  const labelSize =
    size === 'inline'
      ? 'text-[10px]'
      : size === 'page'
      ? 'text-[11.5px]'
      : 'text-[11px]';

  return (
    <div className={`${wrap} ${className}`}>
      <div
        className={
          size === 'inline'
            ? 'flex items-center gap-2'
            : 'flex flex-col items-center gap-2'
        }
      >
        <Loader2 className={`${iconSize} animate-spin text-primary/50`} />
        {label && (
          <span
            className={`${labelSize} text-muted-foreground/60 tracking-[0.14em] uppercase font-mono`}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

/** Compact dynamic-import loader for heavy client components (Plot, etc). */
export function DynamicImportLoader() {
  return (
    <div className="h-full w-full flex items-center justify-center bg-background/40">
      <Loader2 className="w-4 h-4 animate-spin text-primary/40" />
    </div>
  );
}
