type UiTheme = 'light' | 'dark';

/** @deprecated Kept for backward compatibility with DB values. Only 'default' is used. */
export type ChartStyle = 'default' | 'minimal' | 'terminal' | 'presentation';

/** Loose Plotly figure shape — full Plotly types are too strict for server-generated figures. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface PlotlyFigure {
  data?: any[];
  layout?: any;
  frames?: any[];
  [key: string]: any;
}

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

const STYLE: ChartStyleConfig = {
  showGrid: false,
  showXGrid: false,
  showZeroline: false,
  showLine: false,
  mirror: false,
  fontFamily: '-apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif',
  baseFontSize: 11,
  titleFontSize: 13,
  legend: { x: 0.01, y: 0.99, xanchor: 'left', yanchor: 'top', orientation: 'h' },
  margin: { t: 30, l: 0, r: 0, b: 0 },
  gridOpacityScale: 0,
  showSpikes: true,
  ticksOutside: false,
  legendBorderWidth: 0,
};

interface ApplyChartThemeOptions {
  transparentBackground?: boolean;
  /** @deprecated No longer used — single unified style is applied. */
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
    // Matches --foreground: 9 9 11 and --muted-foreground: 113 113 122
    text: 'rgb(9,9,11)',
    textSecondary: 'rgba(113,113,122,0.9)',
    grid: 'rgba(9,9,11,0.06)',
    // Matches --card: 255 255 255 and --background: 250 250 250
    paperBg: 'rgb(255,255,255)',
    plotBg: 'rgb(255,255,255)',
    chartBorder: 'rgba(9,9,11,0.08)',
    legendBg: 'rgba(0,0,0,0)',
    legendBorder: 'rgba(0,0,0,0)',
    hoverBg: 'rgba(255,255,255,0.98)',
    spikeColor: 'rgba(9,9,11,0.08)',
  },
  dark: {
    // Matches --foreground: 248 250 252 and --muted-foreground: 161 161 170
    text: 'rgb(226,232,240)',
    textSecondary: 'rgba(161,161,170,0.9)',
    grid: 'rgba(39,39,42,0.8)',
    // Matches --card: 15 15 18 and --background: 9 9 11
    paperBg: 'rgb(15,15,18)',
    plotBg: 'rgb(15,15,18)',
    chartBorder: 'rgba(39,39,42,0.9)',
    legendBg: 'rgba(0,0,0,0)',
    legendBorder: 'rgba(0,0,0,0)',
    hoverBg: 'rgba(9,9,11,0.96)',
    spikeColor: 'rgba(161,161,170,0.15)',
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

  // Backend sets autorange=false with an explicit padded range — trust it.
  if (axis.autorange === false) return;

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
  figure: PlotlyFigure | null | undefined,
  theme: UiTheme,
  options: ApplyChartThemeOptions = {}
): PlotlyFigure | null | undefined {
  if (!figure) return figure;

  const cleaned = structuredClone(figure);
  const tokens = THEME_TOKENS[theme];
  const transparent = options.transparentBackground ?? false;
  const data = Array.isArray(cleaned.data) ? cleaned.data : [];

  const style = STYLE;
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

  // Detect if chart has any non-date/non-category x-axis (e.g. scatter quadrant charts)
  const isScatterLayout = (() => {
    const xKeys = Object.keys(cleaned.layout).filter((k) => /^xaxis\d*$/.test(k));
    if (xKeys.length === 0) xKeys.push('xaxis');
    for (const k of xKeys) {
      const ax = cleaned.layout[k];
      if (!ax || typeof ax !== 'object') continue;
      if (ax.type === 'linear' || ax.type === 'log') return true;
      // If type isn't set, check if trace data is numeric (not date strings)
      if (!ax.type) {
        for (const trace of data) {
          const ref = `x${k === 'xaxis' ? '' : k.replace('xaxis', '')}`;
          const traceXAxis = trace?.xaxis || 'x';
          if (traceXAxis !== ref) continue;
          if (Array.isArray(trace?.x) && trace.x.length > 0 && typeof trace.x[0] === 'number') return true;
        }
      }
    }
    return false;
  })();

  cleaned.layout.hovermode = isScatterLayout ? 'closest' : 'x unified';
  cleaned.layout.dragmode = 'pan';
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

    // Scale-linked axes can cause Plotly relayout crashes, but are needed
    // for quadrant/scatter charts that require square aspect ratios.
    if (!isScatterLayout) {
      delete axis.scaleanchor;
      delete axis.scaleratio;
    }

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

    // Date formatting — only enforce on confirmed date axes
    if (isXAxis && axis.type === 'date') {
      axis.tickformat = DATE_TICK_FORMAT;
    }

    // Remove rangeslider for cleaner look (only on date/timeseries axes)
    if (isXAxis && !isScatterLayout) {
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

  // ── Re-color year-end boundary shapes for current theme ──
  if (Array.isArray(cleaned.layout.shapes)) {
    cleaned.layout.shapes = cleaned.layout.shapes.map((shape: any) => {
      if (shape?.name === 'year_boundary') {
        return {
          ...shape,
          line: { ...shape.line, color: tokens.grid },
        };
      }
      return shape;
    });
  }

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
    borderwidth: 0,
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
