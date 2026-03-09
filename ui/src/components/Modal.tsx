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
      <div className="absolute inset-0 bg-foreground/40 dark:bg-black/70 backdrop-blur-md" onClick={onClose} />
      <div ref={focusTrapRef} className={`relative w-full ${maxWidth} overflow-hidden rounded-xl border border-border/60 bg-background shadow-2xl animate-in fade-in zoom-in-95 duration-150 backdrop-blur-xl`}>
        {title && (
          <div className="flex items-center justify-between border-b border-border/50 px-4 py-3 bg-foreground/[0.02]">
            <h3 id={titleId} className="text-[13px] font-semibold tracking-tight text-foreground/90">{title}</h3>
            <button
              onClick={onClose}
              className="rounded-md p-1.5 text-muted-foreground/60 hover:bg-foreground/10 hover:text-foreground transition-colors"
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
