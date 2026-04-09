'use client';

import { AlertCircle } from 'lucide-react';
import dynamic from 'next/dynamic';

export const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-background/50">
      <span className="font-mono text-[11px] text-muted-foreground animate-pulse">[...]</span>
    </div>
  ),
}) as any;

export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[13px] text-muted-foreground animate-pulse">
          [...]
        </span>
        <span className="text-[10px] font-mono font-semibold tracking-[0.12em] uppercase text-muted-foreground">
          {label ?? 'Loading'}
        </span>
      </div>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="flex flex-col items-center gap-2 text-center">
        <AlertCircle className="w-5 h-5 text-destructive/80" />
        <p className="text-[12.5px] text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

export function StatLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.12em] text-muted-foreground">
      {children}
    </span>
  );
}

export function PanelCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`panel-card p-4 ${className}`}>
      {children}
    </div>
  );
}
