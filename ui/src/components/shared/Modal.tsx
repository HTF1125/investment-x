'use client';

import { useEffect, useCallback, useId } from 'react';
import { X } from 'lucide-react';
import { useFocusTrap } from '@/hooks/useFocusTrap';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export default function Modal({ open, onClose, title, children, maxWidth = 'max-w-2xl' }: ModalProps) {
  const titleId = useId();
  const focusTrapRef = useFocusTrap(open, onClose);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby={title ? titleId : undefined}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div ref={focusTrapRef} className={`relative w-full ${maxWidth} overflow-hidden rounded-xl border border-border/50 bg-background shadow-2xl animate-in fade-in zoom-in-95 duration-150`}>
        {title && (
          <div className="flex items-center justify-between border-b border-border/40 px-5 py-3.5 bg-card/50">
            <h3 id={titleId} className="text-[13px] font-semibold tracking-tight text-foreground/90">{title}</h3>
            <button
              onClick={onClose}
              className="rounded-[var(--radius)] p-1.5 text-muted-foreground/60 hover:bg-primary/10 hover:text-primary transition-colors"
              aria-label="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
        <div className="p-5 space-y-5 max-h-[60vh] overflow-y-auto custom-scrollbar">
          {children}
        </div>
      </div>
    </div>
  );
}
