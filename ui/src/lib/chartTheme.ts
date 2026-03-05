type UiTheme = 'light' | 'dark';

export type ChartStyle = 'default' | 'minimal' | 'terminal' | 'presentation';

export const CHART_STYLE_LABELS: Record<ChartStyle, string> = {
  default: 'Default',
  minimal: 'Minimal',
  terminal: 'Terminal',
  presentation: 'Presentation',
};

interface ChartStyleConfig {
  showGrid: boolean;
  showXGrid: boolean;
  showZeroline: boolean;
  showLine: boolean;
  mirror: boolean | 'ticks';
  fontFamily: string;
  baseFontSize: number;
  titleFontSize: number;
  legend: { x: number; y: number; xanchor: string; yanchor: string; orientation: 'v' | 'h' };
  margin: { t: number; l: number; r: number; b: number };
  gridOpacityScale: number;
  showSpikes: boolean;
  ticksOutside: boolean;
  legendBorderWidth: number;
}

export const CHART_STYLE_CONFIGS: Record<ChartStyle, ChartStyleConfig> = {
  default: {
    showGrid: true,
    showXGrid: false,
    showZeroline: true,
    showLine: true,
    mirror: true,
    fontFamily: 'Inter, -apple-system, sans-serif',
    baseFontSize: 10,
    titleFontSize: 13,
    legend: { x: 0.01, y: 0.99, xanchor: 'left', yanchor: 'top', orientation: 'v' },
    margin: { t: 44, l: 0, r: 0, b: 0 },
    gridOpacityScale: 1.0,
    showSpikes: true,
    ticksOutside: true,
    legendBorderWidth: 1,
  },
  minimal: {
    showGrid: false,
    showXGrid: false,
    showZeroline: false,
    showLine: false,
    mirror: false,
    fontFamily: 'Inter, -apple-system, sans-serif',
    baseFontSize: 10,
    titleFontSize: 12,
    legend: { x: 0.99, y: 0.01, xanchor: 'right', yanchor: 'bottom', orientation: 'h' },
    margin: { t: 36, l: 5, r: 5, b: 5 },
    gridOpacityScale: 0,
    showSpikes: false,
    ticksOutside: false,
    legendBorderWidth: 0,
  },
  terminal: {
    showGrid: true,
    showXGrid: false,
    showZeroline: true,
    showLine: true,
    mirror: true,
    fontFamily: 'JetBrains Mono, Fira Mono, Consolas, monospace',
    baseFontSize: 9,
    titleFontSize: 11,
    legend: { x: 0.01, y: 0.99, xanchor: 'left', yanchor: 'top', orientation: 'v' },
    margin: { t: 40, l: 0, r: 0, b: 0 },
    gridOpacityScale: 1.8,
    showSpikes: true,
    ticksOutside: true,
    legendBorderWidth: 1,
  },
  presentation: {
    showGrid: true,
    showXGrid: false,
    showZeroline: true,
    showLine: true,
    mirror: false,
    fontFamily: 'Inter, -apple-system, sans-serif',
    baseFontSize: 12,
    titleFontSize: 16,
    legend: { x: 0.99, y: 0.99, xanchor: 'right', yanchor: 'top', orientation: 'v' },
    margin: { t: 56, l: 10, r: 10, b: 10 },
    gridOpacityScale: 0.7,
    showSpikes: true,
    ticksOutside: true,
    legendBorderWidth: 1,
  },
};

interface ApplyChartThemeOptions {
  transparentBackground?: boolean;
  chartStyle?: ChartStyle;
}

const DATE_TICK_FORMAT = '%Y-%m-%d';
const AXIS_KEY_REGEX = /^(x|y)axis(\d*)$/;

/**
 * Curated color palette matching the backend Investment-X design system.
 * Ordered for maximum contrast between adjacent traces.
 */
const COLORWAY = [
  '#00D2FF', // Cyan
  '#FF69B4', // Magenta
  '#A020F0', // Purple
  '#00FF66', // Emerald
  '#FFB84D', // Amber
  '#ef4444', // Rose
  '#3b82f6', // Sky
  '#f59e0b', // Gold
  '#8b5cf6', // Violet
  '#06b6d4', // Teal
];

const THEME_TOKENS: Record<UiTheme, {
  text: string;
  textSecondary: string;
  grid: string;
  paperBg: string;
  plotBg: string;
  chartBorder: string;
  legendBg: string;
  legendBorder: string;
  hoverBg: string;
  spikeColor: string;
}> = {
  light: {
    text: 'rgb(15 23 42)',
    textSecondary: 'rgba(15,23,42,0.5)',
    grid: 'rgba(15,23,42,0.08)',
    paperBg: '#ffffff',
    plotBg: '#ffffff',
    chartBorder: 'rgba(15,23,42,0.12)',
    legendBg: 'rgba(255,255,255,0.95)',
    legendBorder: 'rgba(15,23,42,0.08)',
    hoverBg: 'rgba(255,255,255,0.98)',
    spikeColor: 'rgba(15,23,42,0.15)',
  },
  dark: {
    text: 'rgb(226 232 240)',
    textSecondary: 'rgba(226,232,240,0.4)',
    grid: 'rgba(148,163,184,0.12)',
    paperBg: '#0b0e14',
    plotBg: '#0b0e14',
    chartBorder: 'rgba(148,163,184,0.15)',
    legendBg: 'rgba(15,23,42,0.85)',
    legendBorder: 'rgba(148,163,184,0.12)',
    hoverBg: 'rgba(11,14,20,0.96)',
    spikeColor: 'rgba(148,163,184,0.20)',
  },
};

/**
 * Scale the alpha of an rgba() string by a given factor (clamped to [0, 1]).
 * Falls back to the original string if parsing fails.
 */
function scaleRgbaAlpha(color: string, scale: number): string {
  const match = color.match(/^rgba\(([^,]+),([^,]+),([^,]+),([^)]+)\)$/);
  if (!match) return color;
  const alpha = Math.min(1, Math.max(0, parseFloat(match[4]) * scale));
  return `rgba(${match[1]},${match[2]},${match[3]},${alpha})`;
}

function axisKeyToTraceRef(axisKey: string): string | null {
  const match = axisKey.match(AXIS_KEY_REGEX);
  if (!match) return null;
  return `${match[1]}${match[2] || ''}`;
}

function traceTargetsAxis(trace: any, axisRef: string, axisLetter: 'x' | 'y'): boolean {
  const traceAxis = typeof trace?.[`${axisLetter}axis`] === 'string' ? trace[`${axisLetter}axis`] : axisLetter;
  return traceAxis === axisRef;
}

function hasPositiveFiniteValue(values: unknown): boolean {
  if (values == null) return false;
  if (typeof values === 'number') return Number.isFinite(values) && values > 0;
  if (typeof values === 'string') {
    const num = Number(values);
    return Number.isFinite(num) && num > 0;
  }
  if (Array.isArray(values)) {
    for (let i = 0; i < values.length; i += 1) {
      if (hasPositiveFiniteValue(values[i])) return true;
    }
    return false;
  }
  if (ArrayBuffer.isView(values)) {
    const view = values as unknown as ArrayLike<unknown>;
    for (let i = 0; i < view.length; i += 1) {
      if (hasPositiveFiniteValue(view[i])) return true;
    }
  }
  return false;
}

function axisHasPositiveData(data: any[], axisKey: string): boolean {
  const axisRef = axisKeyToTraceRef(axisKey);
  if (!axisRef) return true;
  const axisLetter = axisRef.startsWith('x') ? 'x' : 'y';

  for (const trace of data) {
    if (!traceTargetsAxis(trace, axisRef, axisLetter)) continue;

    if (axisLetter === 'x') {
      if (hasPositiveFiniteValue(trace?.x)) return true;
      continue;
    }

    if (
      hasPositiveFiniteValue(trace?.y) ||
      hasPositiveFiniteValue(trace?.open) ||
      hasPositiveFiniteValue(trace?.high) ||
      hasPositiveFiniteValue(trace?.low) ||
      hasPositiveFiniteValue(trace?.close)
    ) {
      return true;
    }
  }

  return false;
}

function sanitizeAxisRange(axis: any) {
  if (!Array.isArray(axis?.range)) return;
  if (axis.range.length < 2) {
    delete axis.range;
    axis.autorange = true;
    return;
  }

  const [start, end] = axis.range;
  let isValid = true;

  if (axis.type === 'date') {
    isValid =
      !Number.isNaN(Date.parse(String(start))) &&
      !Number.isNaN(Date.parse(String(end))) &&
      String(start) !== String(end);
  } else if (axis.type === 'category' || axis.type === 'multicategory') {
    isValid = true;
  } else {
    const min = Number(start);
    const max = Number(end);
    isValid = Number.isFinite(min) && Number.isFinite(max) && min !== max;
  }

  if (!isValid) {
    delete axis.range;
    axis.autorange = true;
  } else if (axis.type === 'date') {
    // PAD RIGHT BY 5%
    const tStart = Date.parse(String(start));
    let tEnd = Date.parse(String(end));
    
    const isReversed = tStart > tEnd;
    const dur = Math.abs(tEnd - tStart);
    const pad = dur * 0.05;

    if (isReversed) {
      tEnd -= pad;
    } else {
      tEnd += pad;
    }
    
    axis.range = [
        new Date(tStart).toISOString(),
        new Date(tEnd).toISOString()
    ];
  }
}

/**
 * Count visible traces to decide legend visibility automatically.
 */
function shouldShowLegend(data: any[]): boolean | undefined {
  if (!data || data.length === 0) return false;

  // Types that always need legends
  const alwaysLegendTypes = new Set(['pie', 'funnelarea', 'sunburst', 'treemap', 'icicle']);
  for (const trace of data) {
    if (trace.visible === false) continue;
    if (alwaysLegendTypes.has(trace.type)) return true;
  }

  let visibleCount = 0;
  const names = new Set<string>();
  for (const trace of data) {
    if (trace.visible === false) continue;
    if (trace.showlegend === false) continue;
    visibleCount++;
    const nm = (trace.name || '').trim();
    if (nm) names.add(nm);
  }

  if (visibleCount <= 1) return false;
  if (names.size <= 1 && visibleCount <= 2) return false;
  return undefined; // let Plotly decide
}

export function applyChartTheme(
  figure: any,
  theme: UiTheme,
  options: ApplyChartThemeOptions = {}
) {
  if (!figure) return figure;

  const cleaned =
    typeof structuredClone === 'function'
      ? structuredClone(figure)
      : JSON.parse(JSON.stringify(figure));
  const tokens = THEME_TOKENS[theme];
  const transparent = options.transparentBackground ?? false;
  const data = Array.isArray(cleaned.data) ? cleaned.data : [];

  const styleKey = (options.chartStyle ?? 'default') as ChartStyle;
  const style = CHART_STYLE_CONFIGS[styleKey] ?? CHART_STYLE_CONFIGS.default;
  const scaledGrid = scaleRgbaAlpha(tokens.grid, style.gridOpacityScale);

  if (!cleaned.layout) {
    cleaned.layout = {};
  }

  cleaned.layout.autosize = true;
  cleaned.layout.width = undefined;
  cleaned.layout.height = undefined;
  cleaned.layout.paper_bgcolor = transparent ? 'rgba(0,0,0,0)' : tokens.paperBg;
  cleaned.layout.plot_bgcolor = transparent ? 'rgba(0,0,0,0)' : tokens.plotBg;
  cleaned.layout.font = {
    ...cleaned.layout.font,
    color: tokens.text,
    size: style.baseFontSize,
    family: style.fontFamily,
  };

  // Colorway — unified palette across all charts
  cleaned.layout.colorway = COLORWAY;

  cleaned.layout.hovermode = 'x unified';
  cleaned.layout.dragmode = 'zoom';
  cleaned.layout.hoverdistance = 20;
  cleaned.layout.spikedistance = -1;

  // Auto-detect legend visibility
  const autoLegend = shouldShowLegend(data);
  if (autoLegend !== undefined) {
    cleaned.layout.showlegend = autoLegend;
  }

  cleaned.layout.title = {
    ...(cleaned.layout.title || {}),
    x: 0.01,
    y: 0.98,
    xanchor: 'left',
    yanchor: 'top',
    font: {
      ...(cleaned.layout.title?.font || {}),
      size: style.titleFontSize,
      color: tokens.text,
      family: style.fontFamily,
    },
    pad: { t: 4, l: 4 },
  };

  if (Array.isArray(cleaned.layout.annotations)) {
    cleaned.layout.annotations = cleaned.layout.annotations.map((annotation: any) => ({
      ...annotation,
      font: {
        ...(annotation?.font || {}),
        size: annotation?.font?.size || style.baseFontSize,
        color: tokens.text,
        family: style.fontFamily,
      },
    }));
  }

  // ── Axis styling ──
  const axisKeys = Object.keys(cleaned.layout).filter((key) => /^xaxis\d*$|^yaxis\d*$/.test(key));

  // Ensure at least xaxis and yaxis exist
  if (!axisKeys.includes('xaxis')) { cleaned.layout.xaxis = cleaned.layout.xaxis || {}; axisKeys.push('xaxis'); }
  if (!axisKeys.includes('yaxis')) { cleaned.layout.yaxis = cleaned.layout.yaxis || {}; axisKeys.push('yaxis'); }

  axisKeys.forEach((axisKey) => {
    const axis = cleaned.layout[axisKey];
    if (!axis || typeof axis !== 'object' || Array.isArray(axis)) return;

    const isXAxis = axisKey.startsWith('x');

    // Scale-linked axes are a common source of Plotly relayout crashes.
    delete axis.scaleanchor;
    delete axis.scaleratio;

    sanitizeAxisRange(axis);

    if (axis.type === 'log' && !axisHasPositiveData(data, axisKey)) {
      axis.type = 'linear';
      delete axis.range;
      axis.autorange = true;
    }

    // Grid
    axis.showgrid = isXAxis ? style.showXGrid : style.showGrid;
    axis.zeroline = isXAxis ? false : style.showZeroline;
    axis.showline = style.showLine;
    axis.mirror = style.mirror;

    // Colors
    axis.gridcolor = scaledGrid;
    axis.griddash = 'dot';
    axis.gridwidth = 1;
    axis.zerolinecolor = scaledGrid;
    axis.zerolinewidth = 1;
    axis.linecolor = tokens.chartBorder;
    axis.linewidth = 1;

    // Ticks
    if (style.ticksOutside) {
      axis.ticks = 'outside';
      axis.ticklen = 4;
      axis.tickcolor = tokens.chartBorder;
    } else {
      axis.ticks = '';
    }

    axis.tickfont = {
      ...axis.tickfont,
      color: tokens.textSecondary,
      size: style.baseFontSize,
      family: style.fontFamily,
    };

    // Spikes (cross-hair on hover)
    if (style.showSpikes) {
      axis.showspikes = true;
      axis.spikecolor = tokens.spikeColor;
      axis.spikethickness = 0.5;
      axis.spikedash = 'dot';
      axis.spikemode = 'across';
      axis.spikesnap = 'cursor';
    } else {
      axis.showspikes = false;
    }

    // Date formatting
    if (isXAxis && axis.type === 'date') {
      axis.tickformat = DATE_TICK_FORMAT;
    }

    // Remove rangeslider for cleaner look
    if (isXAxis) {
      axis.rangeslider = { visible: false };
    }

    // Axis titles
    if (typeof axis.title === 'string') {
      axis.title = {
        text: axis.title,
        font: { color: tokens.textSecondary, size: style.baseFontSize, family: style.fontFamily },
        standoff: 8,
      };
    } else if (axis.title && typeof axis.title === 'object') {
      axis.title = {
        ...axis.title,
        font: { ...axis.title.font, color: tokens.textSecondary, size: style.baseFontSize, family: style.fontFamily },
        standoff: axis.title.standoff ?? 8,
      };
    }
  });

  // ── Legend ──
  cleaned.layout.legend = {
    ...(cleaned.layout.legend || {}),
    orientation: style.legend.orientation,
    x: style.legend.x,
    y: style.legend.y,
    xanchor: style.legend.xanchor,
    yanchor: style.legend.yanchor,
    bgcolor: tokens.legendBg,
    bordercolor: tokens.legendBorder,
    borderwidth: style.legendBorderWidth,
    tracegroupgap: 2,
    itemwidth: 30,
    itemsizing: 'constant',
    font: {
      ...cleaned.layout.legend?.font,
      color: tokens.text,
      size: style.baseFontSize,
      family: style.fontFamily,
    },
  };

  // ── Hover label ──
  cleaned.layout.hoverlabel = {
    ...(cleaned.layout.hoverlabel || {}),
    bgcolor: tokens.hoverBg,
    bordercolor: tokens.legendBorder,
    font: {
      ...(cleaned.layout.hoverlabel?.font || {}),
      color: tokens.text,
      family: style.fontFamily,
      size: style.baseFontSize,
    },
    align: cleaned.layout.hoverlabel?.align || 'left',
    namelength: -1,
  };

  // ── Margins ──
  cleaned.layout.margin = style.margin;

  // ── Modebar styling ──
  cleaned.layout.modebar = {
    bgcolor: 'rgba(0,0,0,0)',
    color: tokens.textSecondary,
    activecolor: tokens.text,
    orientation: 'v',
  };

  return cleaned;
}
