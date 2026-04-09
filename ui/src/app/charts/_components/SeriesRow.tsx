'use client';

import { useState } from 'react';
import { GripVertical, ChevronDown, Eye, EyeOff, X, AlertTriangle } from 'lucide-react';
import { COLORWAY } from '@/lib/chartTheme';
import { LINE_STYLES, LINE_WIDTHS, CHART_TYPES } from './constants';
import type { SelectedSeries, Pane } from './types';
import ColorPicker from './ColorPicker';

export default function SeriesRow({
  series,
  index,
  onRemove,
  onUpdate,
  hasError,
  panes,
}: {
  series: SelectedSeries;
  index: number;
  onRemove: () => void;
  onUpdate: (updates: Partial<SelectedSeries>) => void;
  hasError?: boolean;
  panes: Pane[];
}) {
  const color = series.color || COLORWAY[index % COLORWAY.length];

  const [expanded, setExpanded] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [hovered, setHovered] = useState(false);

  const chartTypeLabel = CHART_TYPES.find((t) => t.key === series.chartType)?.label?.toLowerCase() || 'line';

  return (
    <div className={`border-b border-border/15 transition-colors ${expanded ? 'bg-foreground/[0.02]' : ''} ${series.visible === false ? 'opacity-40' : ''}`}>
      {/* Collapsed row */}
      <div
        className="flex items-center gap-1 px-2 h-7 cursor-pointer group"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={(e) => {
          if ((e.target as HTMLElement).closest('button, input')) return;
          setExpanded(!expanded);
        }}
      >
        <GripVertical className="w-3 h-3 text-muted-foreground/25 shrink-0 cursor-grab active:cursor-grabbing" />
        <ColorPicker color={color} onChange={(c) => onUpdate({ color: c })} />

        {editingName ? (
          <input
            autoFocus
            defaultValue={series.name}
            onBlur={(e) => { onUpdate({ name: e.target.value || series.code }); setEditingName(false); }}
            onKeyDown={(e) => { if (e.key === 'Enter') { onUpdate({ name: (e.target as HTMLInputElement).value || series.code }); setEditingName(false); } if (e.key === 'Escape') setEditingName(false); }}
            className="flex-1 min-w-0 text-[12.5px] text-foreground bg-transparent border-b border-primary/40 focus:outline-none px-0 py-0"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span
            className="text-[12.5px] text-foreground truncate flex-1 min-w-0"
            title={`${series.name}${series.name !== series.code ? ` (${series.code})` : ''} — double-click to rename`}
            onDoubleClick={(e) => { e.stopPropagation(); setEditingName(true); }}
          >
            {hasError && <AlertTriangle className="w-2.5 h-2.5 text-warning inline mr-0.5" />}
            {series.name}
          </span>
        )}

        <span className="text-[9.5px] font-mono text-muted-foreground/40 shrink-0">{chartTypeLabel}</span>

        <span
          className={`text-[9.5px] font-mono font-bold shrink-0 ${
            (series.yAxisIndex ?? 0) > 0 ? 'text-primary' : 'text-muted-foreground/30'
          }`}
        >
          Y{(series.yAxisIndex ?? 0) + 1}
        </span>

        {hovered ? (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onUpdate({ visible: series.visible === false ? true : false }); }}
              className="w-4 h-4 flex items-center justify-center text-muted-foreground/30 hover:text-foreground transition-colors shrink-0"
              title={series.visible === false ? 'Show series' : 'Hide series'}
            >
              {series.visible === false ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(); }}
              className="w-4 h-4 flex items-center justify-center text-muted-foreground/20 hover:text-destructive transition-colors shrink-0"
            >
              <X className="w-3 h-3" />
            </button>
          </>
        ) : (
          <ChevronDown className={`w-3 h-3 text-muted-foreground/20 shrink-0 transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`} />
        )}
      </div>

      {/* Expanded settings */}
      {expanded && (
        <div className="px-2 pb-2.5 pt-1.5 border-t border-border/10 space-y-2">
          {/* Chart type */}
          <div className="flex items-center gap-1 flex-wrap">
            {CHART_TYPES.map((t) => (
              <button
                key={t.key}
                onClick={() => onUpdate({ chartType: t.key })}
                className={`h-[22px] px-2 rounded text-[11px] font-mono transition-colors ${
                  series.chartType === t.key
                    ? 'bg-foreground text-background font-bold'
                    : 'text-muted-foreground/40 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Line style + width */}
          <div className="flex items-center gap-1">
            {LINE_STYLES.map((st) => (
              <button
                key={st.key}
                onClick={() => onUpdate({ lineStyle: st.key })}
                className={`h-[22px] px-2 rounded text-[11px] font-mono transition-colors ${
                  (series.lineStyle || 'solid') === st.key
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}
                title={st.label}
              >
                {st.preview}
              </button>
            ))}
            <div className="w-px h-3.5 bg-border/20 mx-0.5" />
            {LINE_WIDTHS.map((w) => (
              <button
                key={w}
                onClick={() => onUpdate({ lineWidth: w })}
                className={`h-[22px] w-7 rounded text-[11px] font-mono text-center transition-colors ${
                  (series.lineWidth ?? 1.5) === w
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Axis + Pane */}
          <div className="flex items-center gap-1">
            <span className="text-[9.5px] font-mono text-muted-foreground/30 uppercase tracking-wider mr-0.5">Axis</span>
            {[0, 1, 2].map((yi) => (
              <button
                key={yi}
                onClick={() => onUpdate({ yAxisIndex: yi })}
                className={`h-[22px] w-7 rounded text-[11px] font-mono font-bold transition-colors ${
                  (series.yAxisIndex ?? 0) === yi
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                }`}
              >
                Y{yi + 1}
              </button>
            ))}
            {panes.length > 1 && (
              <>
                <div className="w-px h-3.5 bg-border/20 mx-0.5" />
                <span className="text-[9.5px] font-mono text-muted-foreground/30 uppercase tracking-wider mr-0.5">Pane</span>
                {panes.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => onUpdate({ paneId: p.id })}
                    className={`h-[22px] px-2 rounded text-[11px] font-mono transition-colors ${
                      (series.paneId ?? 0) === p.id
                        ? 'bg-foreground text-background'
                        : 'text-muted-foreground/35 hover:text-foreground hover:bg-foreground/[0.05]'
                    }`}
                  >
                    P{p.id + 1}
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
