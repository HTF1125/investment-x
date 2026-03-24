'use client';

import { Loader2 } from 'lucide-react';

interface SaveToPackModalProps {
  packList: { id: string; name: string }[];
  packsLoading: boolean;
  savingToPack: boolean;
  onSaveToPack: (packId: string) => void;
  onClose: () => void;
}

export default function SaveToPackModal({
  packList,
  packsLoading,
  savingToPack,
  onSaveToPack,
  onClose,
}: SaveToPackModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 dark:bg-black/70" onClick={onClose}>
      <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-5 w-[340px]" onClick={(e) => e.stopPropagation()}>
        <h3 className="section-title mb-4">Save to Pack</h3>
        {packsLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-4 h-4 animate-spin text-primary/40" />
          </div>
        ) : packList.length > 0 ? (
          <div className="flex flex-col gap-1 max-h-[240px] overflow-y-auto custom-scrollbar">
            {packList.map((pack) => (
              <button
                key={pack.id}
                onClick={() => onSaveToPack(pack.id)}
                disabled={savingToPack}
                className="w-full text-left px-3 py-2 rounded-[var(--radius)] text-[12px] font-medium text-foreground hover:bg-primary/[0.06] border border-border/30 hover:border-primary/30 transition-colors disabled:opacity-30"
              >
                {pack.name}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground/40 py-6 text-center">
            No packs yet. <a href="/chartpack" className="text-primary hover:underline">Create one in Chart Packs.</a>
          </p>
        )}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 h-8 rounded-[var(--radius)] text-[11px] font-medium border border-border/40 text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors">Cancel</button>
        </div>
      </div>
    </div>
  );
}
