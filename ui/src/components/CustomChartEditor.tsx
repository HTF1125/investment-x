'use client';

/**
 * CustomChartEditor — thin re-export wrapper.
 *
 * The implementation lives in `./chart-editor/index.tsx` with state managed
 * by the `useChartEditor` hook in `@/hooks/useChartEditor`.
 *
 * This file exists so that existing dynamic imports
 * (`import('./CustomChartEditor')`) continue to resolve without changes.
 */
export { default } from './chart-editor';
