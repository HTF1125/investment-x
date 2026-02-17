'use client';

import { useEffect, useState } from 'react';

/**
 * Compact status bar showing data pipeline health and region.
 * Replaces the previous near-empty header that consumed excessive vertical space.
 */
export default function Header() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header className="max-w-[1600px] mx-auto mb-8 flex items-center justify-end gap-6 text-slate-500 font-mono text-xs">
        <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-slate-600 mb-1">DATA STATUS</span>
                <span className="text-emerald-500 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    LIVE PIPELINE
                </span>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="flex flex-col items-end">
                <span className="text-[10px] text-slate-600 mb-1">REGION</span>
                <span className="text-slate-300 font-semibold uppercase">Seoul / KST</span>
            </div>
            {mounted && (
              <>
                <div className="w-px h-8 bg-white/10" />
                <div className="flex flex-col items-end">
                    <span className="text-[10px] text-slate-600 mb-1">LOCAL TIME</span>
                    <span className="text-slate-300 font-semibold tabular-nums">
                        {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
                    </span>
                </div>
              </>
            )}
        </div>
    </header>
  );
}
