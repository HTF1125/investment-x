'use client';

import LoadingSpinner from '@/components/shared/LoadingSpinner';

/**
 * Route-level loading fallback for Suspense boundaries on data-fetching
 * pages. Thin wrapper around the canonical `LoadingSpinner` in
 * `components/shared/` — kept as a named export for backward compatibility
 * with existing `loading.tsx` imports.
 */
export default function PageSkeleton({ label }: { label?: string }) {
  return <LoadingSpinner label={label} size="page" />;
}
