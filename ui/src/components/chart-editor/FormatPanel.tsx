'use client';

import React, { useCallback, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

// ── Types ──

interface FormatSeriesConfig {
  code: string;
  name: string;
  chartType: string;
  color?: string;
  showMarkers?: boolean;
  markerSize?: number;
  markerShape?: string;
  fillOpacity?: number;
  showDataLabels?: boolean;
  paneId?: number;
  yAxisIndex?: number;
}

interface FormatPanelProps {
  // Chart-level
  showLegend: boolean;
  onShowLegendChange: (v: boolean) => void;
  legendPosition: string;
  onLegendPositionChange: (v: string) => void;
  showGridlines: boolean;
  onShowGridlinesChange: (v: boolean) => void;
  gridlineStyle: string;
  onGridlineStyleChange: (v: string) => void;
  showZeroline: boolean;
  onShowZerolineChange: (v: boolean) => void;
  titleFontSize: number;
  onTitleFontSizeChange: (v: number) => void;
  bargap: number | undefined;
  onBargapChange: (v: number | undefined) => void;
  axisTitles: Record<string, string>;
  onAxisTitlesChange: (v: Record<string, string>) => void;
  // Series-level
  series: FormatSeriesConfig[];
  onUpdateSeries: (code: string, updates: Partial<FormatSeriesConfig>) => void;
  // Context
  hasBarSeries: boolean;
  axisKeys: string[];
  paneCount: number;
}

const LEGEND_POSITIONS = [
  { value: 'top-right', label: 'Top Right' },
  { value: 'top-left', label: 'Top Left' },
  { value: 'top-center', label: 'Top Center' },
  { value: 'bottom-right', label: 'Bottom Right' },
  { value: 'bottom-left', label: 'Bottom Left' },
];

const GRIDLINE_STYLES = [
  { value: 'solid', label: 'Solid' },
  { value: 'dash', label: 'Dash' },
  { value: 'dot', label: 'Dot' },
];

const MARKER_SHAPES = [
  { value: 'circle', label: 'O' },
  { value: 'square', label: 'Sq' },
  { value: 'diamond', label: 'Dm' },
  { value: 'triangle-up', label: 'Tr' },
  { value: 'cross', label: '+' },
  { value: 'x', label: 'X' },
];

const TITLE_SIZES = [10, 12, 14, 16, 18, 20, 24];

// ── Section Header ──

function SectionHeader({ label, open, onToggle }: { label: string; open: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-primary/[0.03] transition-colors"
    >
      {open ? <ChevronDown className="w-2.5 h-2.5 text-muted-foreground/30" /> : <ChevronRight className="w-2.5 h-2.5 text-muted-foreground/30" />}
      <span className="text-[9px] font-mono font-bold uppercase tracking-[0.12em] text-muted-foreground/40">{label}</span>
    </button>
  );
}

// ── Toggle Button ──

function Toggle({ active, onChange, title }: { active: boolean; onChange: (v: boolean) => void; title?: string }) {
  return (
    <button
      onClick={() => onChange(!active)}
      className={`w-[22px] h-[22px] flex items-center justify-center rounded-[var(--radius)] transition-colors ${
        active ? 'bg-primary/15 text-primary' : 'text-muted-foreground/25 hover:text-foreground hover:bg-primary/[0.06]'
      }`}
      title={title}
    >
      <div className={`w-2.5 h-2.5 rounded-full border-2 transition-colors ${active ? 'border-primary bg-primary' : 'border-muted-foreground/25'}`} />
    </button>
  );
}

// ── Main Component ──

export default function FormatPanel({
  showLegend, onShowLegendChange,
  legendPosition, onLegendPositionChange,
  showGridlines, onShowGridlinesChange,
  gridlineStyle, onGridlineStyleChange,
  showZeroline, onShowZerolineChange,
  titleFontSize, onTitleFontSizeChange,
  bargap, onBargapChange,
  axisTitles, onAxisTitlesChange,
  series, onUpdateSeries,
  hasBarSeries, axisKeys, paneCount,
}: FormatPanelProps) {
  const [chartOpen, setChartOpen] = useState(true);
  const [seriesOpen, setSeriesOpen] = useState(true);

  const handleAxisTitleChange = useCallback((key: string, text: string) => {
    const next = { ...axisTitles };
    if (text.trim()) {
      next[key] = text;
    } else {
      delete next[key];
    }
    onAxisTitlesChange(next);
  }, [axisTitles, onAxisTitlesChange]);

  const formatAxisLabel = useCallback((key: string) => {
    const [paneId, yAxisIndex] = key.split('-').map(Number);
    return paneCount > 1 ? `P${paneId + 1} Y${yAxisIndex + 1}` : `Y${yAxisIndex + 1}`;
  }, [paneCount]);

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar">
      {/* ── Chart Section ── */}
      <SectionHeader label="Chart" open={chartOpen} onToggle={() => setChartOpen(!chartOpen)} />
      {chartOpen && (
        <div className="px-2 pb-2 space-y-2">
          {/* Legend */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Legend</span>
              <Toggle active={showLegend} onChange={onShowLegendChange} title="Show legend" />
            </div>
            {showLegend && (
              <select
                value={legendPosition}
                onChange={(e) => onLegendPositionChange(e.target.value)}
                className="w-full mt-1 px-2 py-1 text-[10px] bg-transparent border border-border/50 rounded-md text-foreground focus:outline-none focus:border-primary/40"
              >
                {LEGEND_POSITIONS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            )}
          </div>

          {/* Gridlines */}
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Gridlines</span>
              <Toggle active={showGridlines} onChange={onShowGridlinesChange} title="Show gridlines" />
            </div>
            {showGridlines && (
              <div className="flex items-center gap-0.5 mt-1">
                {GRIDLINE_STYLES.map((gs) => (
                  <button
                    key={gs.value}
                    onClick={() => onGridlineStyleChange(gs.value)}
                    className={`h-5 px-1.5 text-[8px] font-mono font-bold rounded-[2px] transition-colors ${
                      gridlineStyle === gs.value
                        ? 'text-primary bg-primary/10'
                        : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
                    }`}
                  >
                    {gs.label.toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Zeroline */}
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Zero Line</span>
            <Toggle active={showZeroline} onChange={onShowZerolineChange} title="Show zero line" />
          </div>

          {/* Title Font Size */}
          <div>
            <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 block mb-1">Title Size</span>
            <select
              value={titleFontSize}
              onChange={(e) => onTitleFontSizeChange(parseInt(e.target.value))}
              className="w-full px-2 py-1 text-[10px] bg-transparent border border-border/50 rounded-md text-foreground focus:outline-none focus:border-primary/40"
            >
              {TITLE_SIZES.map((s) => (
                <option key={s} value={s}>{s}px</option>
              ))}
            </select>
          </div>

          {/* Bar Gap — only when bar series exist */}
          {hasBarSeries && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Bar Gap</span>
                <span className="text-[9px] font-mono text-muted-foreground/30">{((bargap ?? 0.2) * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min={0} max={0.8} step={0.05}
                value={bargap ?? 0.2}
                onChange={(e) => onBargapChange(parseFloat(e.target.value))}
                className="w-full h-1 accent-primary"
              />
            </div>
          )}

          {/* Axis Titles */}
          {axisKeys.length > 0 && (
            <div>
              <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40 block mb-1">Axis Titles</span>
              {axisKeys.map((key) => (
                <div key={key} className="flex items-center gap-1.5 mb-1">
                  <span className="text-[9px] font-mono font-bold text-muted-foreground/50 w-8 shrink-0">{formatAxisLabel(key)}</span>
                  <input
                    type="text"
                    value={axisTitles[key] || ''}
                    onChange={(e) => handleAxisTitleChange(key, e.target.value)}
                    placeholder="Title..."
                    className="flex-1 min-w-0 px-2 py-1 text-[10px] bg-transparent border border-border/50 rounded-md text-foreground placeholder:text-muted-foreground/20 focus:outline-none focus:border-primary/40"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="border-t border-border/20" />

      {/* ── Series Section ── */}
      <SectionHeader label="Series" open={seriesOpen} onToggle={() => setSeriesOpen(!seriesOpen)} />
      {seriesOpen && (
        <div className="px-2 pb-2">
          {series.length === 0 && (
            <p className="text-[10px] text-muted-foreground/25 py-2">No series added</p>
          )}
          {series.map((s) => (
            <SeriesFormatRow key={s.code} series={s} onUpdate={(updates) => onUpdateSeries(s.code, updates)} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Series Format Row ──

function SeriesFormatRow({ series: s, onUpdate }: { series: FormatSeriesConfig; onUpdate: (u: Partial<FormatSeriesConfig>) => void }) {
  const [open, setOpen] = useState(false);
  const isArea = s.chartType === 'area' || s.chartType === 'stackedarea';
  const isLine = s.chartType === 'line' || !s.chartType;

  return (
    <div className="border-b border-border/10 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-1.5 py-1.5 text-left hover:bg-primary/[0.03] transition-colors"
      >
        {open ? <ChevronDown className="w-2.5 h-2.5 text-muted-foreground/30" /> : <ChevronRight className="w-2.5 h-2.5 text-muted-foreground/30" />}
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: s.color || '#6382ff' }}
        />
        <span className="text-[10px] text-foreground/70 truncate flex-1 min-w-0">{s.name || s.code}</span>
      </button>

      {open && (
        <div className="pl-5 pr-1 pb-2 space-y-2">
          {/* Markers — for line charts */}
          {isLine && (
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Markers</span>
                <Toggle active={!!s.showMarkers} onChange={(v) => onUpdate({ showMarkers: v })} title="Show markers" />
              </div>
              {s.showMarkers && (
                <div className="mt-1 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-mono text-muted-foreground/30">Size</span>
                    <span className="text-[9px] font-mono text-muted-foreground/30">{s.markerSize ?? 4}</span>
                  </div>
                  <input
                    type="range" min={2} max={12} step={1}
                    value={s.markerSize ?? 4}
                    onChange={(e) => onUpdate({ markerSize: parseInt(e.target.value) })}
                    className="w-full h-1 accent-primary"
                  />
                  <div className="flex items-center gap-0.5 flex-wrap">
                    {MARKER_SHAPES.map((ms) => (
                      <button
                        key={ms.value}
                        onClick={() => onUpdate({ markerShape: ms.value })}
                        className={`h-5 px-1 text-[8px] font-mono font-bold rounded-[2px] transition-colors ${
                          (s.markerShape || 'circle') === ms.value
                            ? 'text-primary bg-primary/10'
                            : 'text-muted-foreground/30 hover:text-foreground hover:bg-primary/[0.06]'
                        }`}
                      >
                        {ms.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Fill Opacity — for area charts */}
          {isArea && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Fill Opacity</span>
                <span className="text-[9px] font-mono text-muted-foreground/30">{s.fillOpacity ?? (s.chartType === 'stackedarea' ? 25 : 9)}%</span>
              </div>
              <input
                type="range" min={0} max={100} step={1}
                value={s.fillOpacity ?? (s.chartType === 'stackedarea' ? 25 : 9)}
                onChange={(e) => onUpdate({ fillOpacity: parseInt(e.target.value) })}
                className="w-full h-1 accent-primary"
              />
            </div>
          )}

          {/* Data Labels — for all types */}
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-mono uppercase tracking-[0.08em] text-muted-foreground/40">Data Labels</span>
            <Toggle active={!!s.showDataLabels} onChange={(v) => onUpdate({ showDataLabels: v })} title="Show data labels" />
          </div>
        </div>
      )}
    </div>
  );
}
