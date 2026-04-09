'use client';

import { useState, useEffect, useRef } from 'react';
import { COLORWAY } from '@/lib/chartTheme';

export default function ColorPicker({ color, onChange }: { color: string; onChange: (c: string) => void }) {
  const [open, setOpen] = useState(false);
  const [hex, setHex] = useState(color);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => { setHex(color); }, [color]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="w-3.5 h-3.5 rounded-full shrink-0 cursor-pointer ring-1 ring-border/20 hover:ring-border/50 transition-all"
        style={{ backgroundColor: color }}
        title="Change color"
      />
      {open && (
        <div className="absolute left-0 top-full mt-1 p-2 bg-card border border-border/50 rounded-[var(--radius)] shadow-lg z-50 w-[140px]">
          <div className="grid grid-cols-5 gap-1.5 mb-2">
            {COLORWAY.map((c) => (
              <button
                key={c}
                onClick={() => { onChange(c); setOpen(false); }}
                className={`w-5 h-5 rounded-full transition-all ${
                  color === c ? 'ring-2 ring-foreground ring-offset-1 ring-offset-card' : 'hover:ring-1 hover:ring-border/50'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
          <input
            type="text"
            value={hex}
            onChange={(e) => setHex(e.target.value)}
            onBlur={() => {
              if (/^#[0-9a-fA-F]{6}$/.test(hex)) { onChange(hex); setOpen(false); }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && /^#[0-9a-fA-F]{6}$/.test(hex)) { onChange(hex); setOpen(false); }
            }}
            className="w-full px-1.5 py-1 text-[11.5px] font-mono border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/40"
            placeholder="#FF0000"
          />
        </div>
      )}
    </div>
  );
}
