/**
 * Shared Plotly figure builder used by both the chart builder and pack chart viewer.
 * Handles multi-pane, multi-axis (Y1/Y2/Y3), log scale, annotations, and date ranges.
 */

import { COLORWAY } from './chartTheme';

export interface SeriesConfig {
  code: string;
  name: string;
  chartType: string;
  yAxis: string;
  yAxisIndex?: number;
  visible: boolean;
  color?: string;
  transform?: string;
  transformParam?: number;
  lineStyle?: string;
  lineWidth?: number;
  paneId?: number;
}

export interface PaneConfig {
  id: number;
  label: string;
}

export interface AnnotationConfig {
  id: string;
  type: 'hline' | 'vline' | 'text';
  x?: string;
  y?: number;
  text?: string;
  color: string;
  paneId: number;
}

export function getApiCode(s: SeriesConfig): string {
  const t = s.transform || 'none';
  if (t === 'none' || t === 'log') return s.code;
  if (s.code.includes('(')) return s.code;
  const p = s.transformParam;
  switch (t) {
    case 'pctchg': return `PctChange(Series("${s.code}"),${p || 1})`;
    case 'yoy': return `PctChange(Series("${s.code}"),252)`;
    case 'ma': return `Series("${s.code}").rolling(${p || 20}).mean()`;
    case 'zscore': return `ZScore(Series("${s.code}"),${p || 252})`;
    case 'diff': return `Diff(Series("${s.code}"),${p || 1})`;
    case 'drawdown': return `Drawdown(Series("${s.code}"))`;
    case 'rebase': return `Rebase(Series("${s.code}"))`;
    default: return s.code;
  }
}

export interface BuildFigureOpts {
  rawData: Record<string, (string | number | null)[]>;
  series: SeriesConfig[];
  /** All series in the parent (for stable color indexing). Falls back to `series` if not provided. */
  allSeries?: SeriesConfig[];
  panes?: PaneConfig[];
  annotations?: AnnotationConfig[];
  logAxes?: Set<string>;
  /** Per-axis y-axis base values. Key: "paneId-yAxisIndex", value: base number. Default 0 (tozero). */
  yAxisBases?: Record<string, number>;
  /** Per-axis manual range. Key: "paneId-yAxisIndex", value: {min?, max?}. Overrides auto-computed range. */
  yAxisRanges?: Record<string, { min?: number; max?: number }>;
  /** Per-axis inverted state. Key: "paneId-yAxisIndex". When set, axis uses autorange: 'reversed'. */
  invertedAxes?: Set<string>;
  /** Per-axis percentage format. Key: "paneId-yAxisIndex". When set, tickformat: '.1%'. */
  pctAxes?: Set<string>;
  isLight: boolean;
  title?: string;
  startDate?: string;
  endDate?: string;
  /** Compact mode for smaller tiles — smaller fonts, hidden modebar */
  compact?: boolean;
  /** Show NBER recession shading bands */
  showRecessions?: boolean;
  /** Hover/crosshair mode */
  hoverMode?: 'x unified' | 'closest' | 'x';
}

const NBER_RECESSIONS: [string, string][] = [
  ['1980-01-01', '1980-07-01'],
  ['1981-07-01', '1982-11-01'],
  ['1990-07-01', '1991-03-01'],
  ['2001-03-01', '2001-11-01'],
  ['2007-12-01', '2009-06-01'],
  ['2020-02-01', '2020-04-01'],
];

export function buildChartFigure(opts: BuildFigureOpts): { data: any[]; layout: any } | null {
  const {
    rawData, series, isLight, title,
    startDate = '', endDate = '',
    compact = false,
    showRecessions = false,
    hoverMode = 'x unified',
  } = opts;
  const allSeries = opts.allSeries || series;
  const panes = opts.panes?.length ? opts.panes : [{ id: 0, label: 'Pane 1' }];
  const annotations = opts.annotations || [];
  const logAxes = opts.logAxes || new Set<string>();
  const yAxisBases = opts.yAxisBases || {};
  const yAxisRanges = opts.yAxisRanges || {};
  const invertedAxes = opts.invertedAxes || new Set<string>();
  const pctAxes = opts.pctAxes || new Set<string>();

  if (!rawData?.Date) return null;
  const dates = rawData.Date as string[];

  // ── Pane domains ──
  const numPanes = panes.length;
  const paneGap = 0.03;
  const totalGap = paneGap * (numPanes - 1);
  const paneHeight = (1 - totalGap) / numPanes;
  const paneDomains: Record<number, [number, number]> = {};
  panes.forEach((p, idx) => {
    const top = 1 - idx * (paneHeight + paneGap);
    const bottom = top - paneHeight;
    paneDomains[p.id] = [Math.max(0, bottom), top];
  });

  // ── Axis key helpers ──
  const paneXAxisKey = (paneId: number): string => {
    const idx = panes.findIndex((p) => p.id === paneId);
    return idx === 0 ? 'x' : `x${idx + 1}`;
  };

  // Collect unique yAxisIndex values used per pane
  const paneAxisIndices: Record<number, Set<number>> = {};
  panes.forEach((p) => { paneAxisIndices[p.id] = new Set([0]); });
  series.forEach((s) => {
    const pid = s.paneId ?? 0;
    if (paneAxisIndices[pid]) paneAxisIndices[pid].add(s.yAxisIndex ?? 0);
  });

  // Build stable mapping: (paneId, yAxisIndex) → plotly yaxis number
  let yAxisCounter = 0;
  const yAxisMap: Record<string, number> = {};
  panes.forEach((p) => {
    const indices = Array.from(paneAxisIndices[p.id]).sort();
    indices.forEach((yi) => {
      yAxisCounter++;
      yAxisMap[`${p.id}-${yi}`] = yAxisCounter;
    });
  });

  const getYAxisRef = (paneId: number, yAxisIndex: number): string => {
    const num = yAxisMap[`${paneId}-${yAxisIndex}`] || yAxisMap[`${paneId}-0`] || 1;
    return num === 1 ? 'y' : `y${num}`;
  };
  const getYAxisPrimary = (paneId: number): string => getYAxisRef(paneId, 0);

  // ── Check if any series uses stacked modes ──
  const hasStackedBar = series.some((s) => s.chartType === 'stackedbar');
  const hasStackedArea = series.some((s) => s.chartType === 'stackedarea');

  // ── Traces ──
  // Track stackgroup counters per (pane, yAxisIndex) for proper grouping
  let stackAreaGroupCounter = 0;
  const stackAreaGroups = new Map<string, string>();

  const traces = series.map((s) => {
    const color = s.color || COLORWAY[allSeries.indexOf(s) % COLORWAY.length];
    const dash = s.lineStyle || 'solid';
    const width = s.lineWidth ?? 1.5;
    let values = (rawData[getApiCode(s)] || rawData[s.code] || []) as (number | null)[];

    if (s.transform === 'log') {
      values = values.map((v) => (v != null && v > 0 ? Math.log(v) : null));
    }

    const seriesPaneId = s.paneId ?? 0;
    const yAxisRef = getYAxisRef(seriesPaneId, s.yAxisIndex ?? 0);
    const xAxisRef = paneXAxisKey(seriesPaneId);

    const base: any = {
      x: dates, y: values,
      name: s.name || s.code,
      yaxis: yAxisRef, xaxis: xAxisRef,
      marker: { color },
      line: { color, width, dash },
      connectgaps: true,
      hovertemplate: `<b>${s.name || s.code}</b><br>%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>`,
    };

    switch (s.chartType) {
      case 'bar': return { ...base, type: 'bar' };
      case 'stackedbar': return { ...base, type: 'bar' };
      case 'area': return { ...base, type: 'scatter', mode: 'lines', fill: 'tozeroy', fillcolor: color + '18' };
      case 'stackedarea': {
        // Group stacked areas by (pane, yAxisIndex) so independent panes stack separately
        const groupKey = `${seriesPaneId}-${s.yAxisIndex ?? 0}`;
        if (!stackAreaGroups.has(groupKey)) {
          stackAreaGroups.set(groupKey, `stack${stackAreaGroupCounter++}`);
        }
        return {
          ...base, type: 'scatter', mode: 'lines',
          stackgroup: stackAreaGroups.get(groupKey),
          fillcolor: color + '40',
          line: { ...base.line, width: 0.5 },
        };
      }
      case 'scatter': return { ...base, type: 'scatter', mode: 'markers', marker: { ...base.marker, size: compact ? 3 : 4 } };
      default: return { ...base, type: 'scatter', mode: 'lines' };
    }
  });

  // ── Date range ──
  const xRangeStart = startDate || undefined;
  const xRangeEnd = endDate || undefined;
  const hasXRange = !!(xRangeStart || xRangeEnd);

  let visStartIdx = 0;
  let visEndIdx = dates.length - 1;
  if (xRangeStart) {
    const idx = dates.findIndex((d) => d >= xRangeStart);
    if (idx >= 0) visStartIdx = idx;
  }
  if (xRangeEnd) {
    for (let i = dates.length - 1; i >= 0; i--) {
      if (dates[i] <= xRangeEnd) { visEndIdx = i; break; }
    }
  }

  // Compute y-axis range per (pane, yAxisIndex) from visible data window.
  // For stacked bars/areas, sum all series per date to get the true axis extent.
  const yRanges: Record<string, [number, number]> = {};
  if (hasXRange) {
    // Collect stacked sums per axis key
    const stackedSums: Record<string, (number | null)[]> = {};

    series.forEach((s) => {
      const key = `${s.paneId ?? 0}-${s.yAxisIndex ?? 0}`;
      let values = (rawData[getApiCode(s)] || rawData[s.code] || []) as (number | null)[];
      if (s.transform === 'log') {
        values = values.map((v) => (v != null && v > 0 ? Math.log(v) : null));
      }
      const slice = values.slice(visStartIdx, visEndIdx + 1);

      const isStacked = s.chartType === 'stackedbar' || s.chartType === 'stackedarea';
      if (isStacked) {
        // Accumulate per-date sums for stacked series on the same axis
        if (!stackedSums[key]) stackedSums[key] = new Array(slice.length).fill(0);
        for (let j = 0; j < slice.length; j++) {
          const v = slice[j];
          if (v != null && isFinite(v)) {
            stackedSums[key][j] = (stackedSums[key][j] ?? 0) + v;
          }
        }
      } else {
        // Non-stacked: use individual min/max
        let min = Infinity, max = -Infinity;
        for (const v of slice) {
          if (v != null && isFinite(v)) {
            if (v < min) min = v;
            if (v > max) max = v;
          }
        }
        if (min === Infinity) return;
        const prev = yRanges[key];
        if (prev) {
          yRanges[key] = [Math.min(prev[0], min), Math.max(prev[1], max)];
        } else {
          yRanges[key] = [min, max];
        }
      }
    });

    // Merge stacked sums into yRanges
    for (const [key, sums] of Object.entries(stackedSums)) {
      let min = Infinity, max = -Infinity;
      for (const v of sums) {
        if (v != null && isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      if (min === Infinity) continue;
      const prev = yRanges[key];
      if (prev) {
        yRanges[key] = [Math.min(prev[0], min), Math.max(prev[1], max)];
      } else {
        yRanges[key] = [min, max];
      }
    }
  }

  // ── Style constants ──
  const fg = isLight ? '#020617' : '#dbeafe';
  const grid = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(148,163,184,0.04)';
  const baseFontSize = compact ? 9 : 10;
  const axisBase = {
    gridcolor: grid, griddash: 'dot' as const, zerolinecolor: grid, showgrid: true,
    tickfont: { color: fg, size: baseFontSize, family: 'Inter, sans-serif' },
    linecolor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.06)',
  };

  const maxAxesPerPane = Math.max(...panes.map((p) => paneAxisIndices[p.id].size));

  const layout: any = {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: fg, family: 'Inter, sans-serif', size: compact ? 10 : 11 },
    margin: {
      t: title ? (compact ? 28 : 35) : (compact ? 8 : 10),
      l: compact ? 8 : 10,
      r: compact ? 45 : 55,
      b: compact ? 28 : 35,
    },
    hovermode: hoverMode,
    dragmode: 'zoom',
    hoverdistance: 20,
    spikedistance: -1,
    showlegend: compact ? series.length > 1 : false,
    ...(compact && series.length > 1 ? {
      legend: {
        orientation: 'h' as const, x: 0, y: 1.02, xanchor: 'left', yanchor: 'bottom',
        font: { size: 9, color: fg }, bgcolor: 'rgba(0,0,0,0)',
        tracegroupgap: 2,
      },
    } : {}),
    ...(hasStackedBar ? { barmode: 'stack' as const } : {}),
    hoverlabel: {
      bgcolor: isLight ? 'rgba(255,255,255,0.98)' : 'rgba(15,23,42,0.98)',
      bordercolor: isLight ? 'rgba(15,23,42,0.1)' : 'rgba(148,163,184,0.2)',
      font: { color: fg, family: 'Inter, sans-serif', size: compact ? 10 : 11 },
    },
    ...(title ? {
      title: {
        text: title,
        font: { size: compact ? 12 : 14, color: fg, family: 'Inter, sans-serif' },
        x: 0.5, xanchor: 'center',
      },
    } : {}),
    modebar: compact
      ? { bgcolor: 'rgba(0,0,0,0)', color: 'transparent', activecolor: 'transparent' }
      : {
          bgcolor: 'rgba(0,0,0,0)',
          color: isLight ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.3)',
          activecolor: fg, orientation: 'v',
        },
    shapes: [] as any[],
    annotations: [] as any[],
  };

  // ── Build axes per pane ──
  panes.forEach((pane, paneIdx) => {
    const domain = paneDomains[pane.id];
    const xKey = paneIdx === 0 ? 'xaxis' : `xaxis${paneIdx + 1}`;
    const primaryYRef = getYAxisPrimary(pane.id);

    layout[xKey] = {
      ...axisBase, type: 'date', domain: [0, 1],
      anchor: primaryYRef,
      rangeslider: { visible: false },
      showspikes: true,
      spikecolor: isLight ? 'rgba(0,0,0,0.08)' : 'rgba(148,163,184,0.1)',
      spikethickness: 0.5, spikedash: 'dot', spikemode: 'across',
      showticklabels: paneIdx === numPanes - 1,
      ...(paneIdx > 0 ? { matches: 'x' } : {}),
      ...(hasXRange ? { range: [xRangeStart || dates[0], xRangeEnd || dates[dates.length - 1]] } : {}),
    };

    const indices = Array.from(paneAxisIndices[pane.id]).sort();
    indices.forEach((yi, axisOrd) => {
      const plotlyNum = yAxisMap[`${pane.id}-${yi}`];
      const yKey = plotlyNum === 1 ? 'yaxis' : `yaxis${plotlyNum}`;
      const isPrimary = axisOrd === 0;
      const isLog = logAxes.has(`${pane.id}-${yi}`);
      const isInverted = invertedAxes.has(`${pane.id}-${yi}`);
      const isPct = pctAxes.has(`${pane.id}-${yi}`);

      const rangeKey = `${pane.id}-${yi}`;
      const yRange = yRanges[rangeKey];
      const axisBase_val = yAxisBases[rangeKey];
      const hasCustomBase = axisBase_val != null && axisBase_val !== 0;
      const manualRange = yAxisRanges[rangeKey];
      const hasManualMin = manualRange?.min != null;
      const hasManualMax = manualRange?.max != null;
      const hasManualRange = hasManualMin || hasManualMax;

      // Check if this axis has any stacked series — if so, let Plotly autorange
      // since our manual range can't account for Plotly's internal stacking offsets.
      const axisHasStacked = series.some(
        (s) =>
          `${s.paneId ?? 0}-${s.yAxisIndex ?? 0}` === rangeKey &&
          (s.chartType === 'stackedbar' || s.chartType === 'stackedarea'),
      );

      let computedRange: [number, number] | undefined;

      // Manual Y-axis range takes highest priority
      if (hasManualRange && !axisHasStacked) {
        // If only min or only max is set, compute the missing bound from data
        const autoMin = yRange ? yRange[0] : 0;
        const autoMax = yRange ? yRange[1] : 100;
        const lo = hasManualMin ? manualRange!.min! : autoMin;
        const hi = hasManualMax ? manualRange!.max! : autoMax;
        computedRange = [lo, hi];
      } else if (!axisHasStacked && hasXRange && yRange) {
        if (isLog) {
          const lo = yRange[0] > 0 ? yRange[0] : 0.01;
          const hi = yRange[1] > 0 ? yRange[1] : lo * 10;
          const logLo = Math.log10(lo);
          const logHi = Math.log10(hi);
          const pad = (logHi - logLo) * 0.05 || 0.1;
          computedRange = [logLo - pad, logHi + pad];
        } else {
          const baseVal = axisBase_val ?? 0;
          const lo = Math.min(baseVal, yRange[0]);
          const span = yRange[1] - lo;
          const pad = span > 0 ? span * 0.05 : Math.abs(lo) * 0.05 || 1;
          computedRange = [lo - pad, yRange[1] + pad];
        }
      }

      // rangemode: include base value when no explicit range
      const rangeModeProps = !computedRange && !isLog && !hasManualRange
        ? (hasCustomBase
          ? { rangemode: 'normal' as const, range: [axisBase_val, undefined], autorange: 'max' as const }
          : { rangemode: 'tozero' as const })
        : {};

      // Determine autorange considering inversion and computed range
      const autorangeVal = (() => {
        if (computedRange) return false;
        if (isInverted) return 'reversed' as const;
        return undefined;
      })();

      layout[yKey] = {
        ...axisBase,
        domain,
        side: 'right',
        type: isLog ? 'log' : undefined,
        showgrid: isPrimary,
        showspikes: isPrimary,
        tickformat: isPct ? '.1%' : '~s',
        minexponent: 3,
        ...rangeModeProps,
        ...(computedRange
          ? { range: isInverted ? [computedRange[1], computedRange[0]] : computedRange, autorange: false }
          : {}),
        ...(autorangeVal !== undefined ? { autorange: autorangeVal } : {}),
        ...(isPrimary ? {
          automargin: true,
          spikecolor: isLight ? 'rgba(0,0,0,0.08)' : 'rgba(148,163,184,0.1)',
          spikethickness: 0.5, spikedash: 'dot', spikemode: 'across',
          anchor: paneXAxisKey(pane.id),
        } : {
          overlaying: primaryYRef,
          anchor: 'free',
          automargin: true,
          autoshift: true,
          shift: 0,
        }),
        title: undefined,
      };

      // Y-axis labels when multiple axes — use native axis title so it follows autoshift
      if (indices.length > 1) {
        layout[yKey].title = {
          text: `Y${yi + 1}${isLog ? ' log' : ''}`,
          font: { size: 9, color: fg, family: 'Inter, sans-serif' },
          standoff: 2,
        };
      }
    });
  });

  // ── Annotations ──
  annotations.forEach((ann) => {
    const paneIdx = panes.findIndex((p) => p.id === ann.paneId);
    const xRef = paneIdx === 0 ? 'x' : `x${paneIdx + 1}`;
    const yRef = getYAxisPrimary(ann.paneId);

    if (ann.type === 'hline' && ann.y != null) {
      layout.shapes.push({ type: 'line', x0: 0, x1: 1, xref: 'paper', y0: ann.y, y1: ann.y, yref: yRef, line: { color: ann.color, width: 1, dash: 'dash' } });
      layout.annotations.push({ x: 1, xref: 'paper', xanchor: 'left', y: ann.y, yref: yRef, text: `${ann.y}`, showarrow: false, font: { size: 9, color: ann.color, family: 'Inter' }, xshift: 4 });
    } else if (ann.type === 'vline' && ann.x) {
      layout.shapes.push({ type: 'line', x0: ann.x, x1: ann.x, xref: xRef, y0: 0, y1: 1, yref: 'paper', line: { color: ann.color, width: 1, dash: 'dash' } });
      if (ann.text) layout.annotations.push({ x: ann.x, xref: xRef, y: 1, yref: 'paper', yanchor: 'bottom', text: ann.text, showarrow: false, font: { size: 9, color: ann.color, family: 'Inter' }, yshift: 2 });
    } else if (ann.type === 'text' && ann.x && ann.y != null) {
      layout.annotations.push({
        x: ann.x, xref: xRef, y: ann.y, yref: yRef, text: ann.text || '', showarrow: true, arrowhead: 2, arrowsize: 0.8, arrowwidth: 1, arrowcolor: ann.color,
        font: { size: 10, color: ann.color, family: 'Inter' },
        bgcolor: isLight ? 'rgba(255,255,255,0.9)' : 'rgba(15,15,22,0.9)',
        bordercolor: ann.color, borderwidth: 1, borderpad: 3,
      });
    }
  });

  // ── Year boundary lines (Jan 1 verticals, matching dashboard style) ──
  const yearGridColor = isLight ? 'rgba(15,23,42,0.08)' : 'rgba(148,163,184,0.12)';
  if (dates.length >= 2) {
    const firstDate = new Date(dates[0]);
    const lastDate = new Date(dates[dates.length - 1]);
    if (!isNaN(firstDate.getTime()) && !isNaN(lastDate.getTime())) {
      const startYear = firstDate.getFullYear() + 1;
      const endYear = lastDate.getFullYear() + 1;
      for (let year = startYear; year <= endYear; year++) {
        const jan1 = `${year}-01-01`;
        if (jan1 > dates[0] && jan1 <= dates[dates.length - 1]) {
          layout.shapes.push({
            type: 'line',
            xref: 'x', yref: 'paper',
            x0: jan1, x1: jan1,
            y0: 0, y1: 1,
            line: { color: yearGridColor, width: 0.5, dash: 'solid' },
            layer: 'below',
            name: 'year_boundary',
          });
        }
      }
    }
  }

  // ── NBER recession shading ──
  if (showRecessions && dates.length >= 2) {
    const dataStart = dates[0];
    const dataEnd = dates[dates.length - 1];
    const recFill = isLight ? 'rgba(0,0,0,0.04)' : 'rgba(148,163,184,0.06)';
    for (const [rStart, rEnd] of NBER_RECESSIONS) {
      if (rEnd < dataStart || rStart > dataEnd) continue;
      layout.shapes.push({
        type: 'rect', xref: 'x', yref: 'paper',
        x0: rStart, x1: rEnd, y0: 0, y1: 1,
        fillcolor: recFill, line: { width: 0 }, layer: 'below',
      });
    }
  }

  return { data: traces, layout };
}
