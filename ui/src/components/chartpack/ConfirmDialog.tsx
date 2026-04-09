import React, { useEffect } from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';

interface Props {
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel, loading }: Props) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape' && !loading) onCancel(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onCancel, loading]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div className="bg-card border border-destructive/30 rounded-[var(--radius)] w-full max-w-sm shadow-md p-5 mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-md bg-destructive/15 flex items-center justify-center border border-destructive/30 shrink-0">
            <AlertTriangle className="w-4 h-4 text-destructive" />
          </div>
          <div>
            <h3 className="text-[13px] font-semibold text-foreground">{title}</h3>
            <p className="text-[11.5px] text-muted-foreground/50 mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-[13px] text-muted-foreground leading-relaxed mb-5">{message}</p>
        <div className="flex items-center justify-end gap-2">
          <button onClick={onCancel} disabled={loading} className="px-4 py-1.5 text-[12.5px] font-semibold text-muted-foreground hover:text-foreground bg-background hover:bg-accent/40 rounded-[var(--radius)] transition-all border border-border/50 disabled:opacity-50">
            Cancel
          </button>
          <button onClick={onConfirm} disabled={loading} className="flex items-center gap-1.5 px-4 py-1.5 text-[12.5px] font-semibold bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-[var(--radius)] transition-all disabled:opacity-50">
            {loading ? (
              <span className="w-3 h-3 border-2 border-destructive-foreground/30 border-t-destructive-foreground rounded-full animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3" />
            )}
            {confirmLabel || 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
