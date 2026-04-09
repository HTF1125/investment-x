import React, { useState, useEffect, useRef } from 'react';
import { MoreVertical, Edit3, RefreshCw, FolderOutput, ArrowUp, ArrowDown, Trash2, Link } from 'lucide-react';

interface Props {
  onEdit: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onCopyMove: () => void;
  onRemove: () => void;
  onRefresh: () => void;
  onCopyImageUrl?: () => void;
  hasCachedFigure: boolean;
  isFirst: boolean;
  isLast: boolean;
}

export default function ChartMenu({ onEdit, onMoveUp, onMoveDown, onCopyMove, onRemove, onRefresh, onCopyImageUrl, hasCachedFigure, isFirst, isLast }: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const item = (onClick: () => void, icon: React.ReactNode, label: string, destructive?: boolean) => (
    <button
      onClick={() => { onClick(); setOpen(false); }}
      className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-[12.5px] rounded-[calc(var(--radius)-2px)] transition-colors ${
        destructive
          ? 'text-destructive hover:bg-destructive/10'
          : 'text-foreground/70 hover:text-foreground hover:bg-foreground/[0.05]'
      }`}
    >
      {icon}{label}
    </button>
  );

  return (
    <div ref={menuRef} className="relative pointer-events-auto">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className="w-7 h-7 flex items-center justify-center rounded-[var(--radius)] text-muted-foreground/30 hover:text-foreground hover:bg-foreground/[0.06] transition-colors"
        aria-label="Chart actions"
      >
        <MoreVertical className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-20 w-[160px] py-1 bg-card border border-border/50 rounded-[var(--radius)] shadow-md animate-fade-in">
          {item(onEdit, <Edit3 className="w-3 h-3" />, 'Edit chart')}
          {hasCachedFigure && item(onRefresh, <RefreshCw className="w-3 h-3" />, 'Refresh data')}
          {item(onCopyMove, <FolderOutput className="w-3 h-3" />, 'Copy / Move')}
          {onCopyImageUrl && item(onCopyImageUrl, <Link className="w-3 h-3" />, 'Copy image URL')}
          {!isFirst && item(onMoveUp, <ArrowUp className="w-3 h-3" />, 'Move up')}
          {!isLast && item(onMoveDown, <ArrowDown className="w-3 h-3" />, 'Move down')}
          <div className="my-1 border-t border-border/20" />
          {item(onRemove, <Trash2 className="w-3 h-3" />, 'Remove', true)}
        </div>
      )}
    </div>
  );
}
