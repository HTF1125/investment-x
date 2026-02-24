type UiTheme = 'light' | 'dark';

interface ApplyChartThemeOptions {
  transparentBackground?: boolean;
}

const DATE_TICK_FORMAT = '%Y-%m-%d';
const BASE_FONT_SIZE = 10;
const TITLE_FONT_SIZE = 14;
const TITLE_X = 0.01;
const TITLE_Y = 0.98;
const LEGEND_X = 0.01;
const LEGEND_Y = 0.99;
const LEGEND_GAP = 2;
const AXIS_KEY_REGEX = /^(x|y)axis(\d*)$/;

const THEME_TOKENS: Record<UiTheme, {
  text: string;
  grid: string;
  paperBg: string;
  plotBg: string;
  chartBorder: string;
  legendBg: string;
  legendBorder: string;
  hoverBg: string;
}> = {
  light: {
    text: 'rgb(15 23 42)',
    grid: 'rgba(15,23,42,0.12)',
    paperBg: '#ffffff',
    plotBg: '#ffffff',
    chartBorder: 'rgba(255,255,255,0.95)',
    legendBg: 'rgba(255,255,255,0.92)',
    legendBorder: 'rgba(15,23,42,0.15)',
    hoverBg: 'rgba(255,255,255,0.98)',
  },
  dark: {
    text: 'rgb(226 232 240)',
    grid: 'rgba(148,163,184,0.2)',
    paperBg: '#0b0e14',
    plotBg: '#0b0e14',
    chartBorder: 'rgba(255,255,255,0.95)',
    legendBg: 'rgba(15,23,42,0.78)',
    legendBorder: 'rgba(148,163,184,0.35)',
    hoverBg: 'rgba(11,14,20,0.95)',
  },
};

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
  if (Array.isArray(values) || ArrayBuffer.isView(values)) {
    for (const value of values as Iterable<unknown>) {
      if (hasPositiveFiniteValue(value)) return true;
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
  }
}

export function applyChartTheme(
  figure: any,
  theme: UiTheme,
  options: ApplyChartThemeOptions = {}
) {
  if (!figure) return figure;

  // Prefer structuredClone to preserve NaN/Infinity and typed structures used by Plotly.
  const cleaned =
    typeof structuredClone === 'function'
      ? structuredClone(figure)
      : JSON.parse(JSON.stringify(figure));
  const tokens = THEME_TOKENS[theme];
  const transparent = options.transparentBackground ?? false;
  const data = Array.isArray(cleaned.data) ? cleaned.data : [];

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
    size: BASE_FONT_SIZE,
    family: cleaned.layout.font?.family || 'Inter, sans-serif',
  };
  cleaned.layout.hovermode = 'x';
  cleaned.layout.title = {
    ...(cleaned.layout.title || {}),
    x: TITLE_X,
    y: TITLE_Y,
    xanchor: 'left',
    yanchor: 'top',
    font: {
      ...(cleaned.layout.title?.font || {}),
      size: TITLE_FONT_SIZE,
      color: theme === 'light' ? '#000000' : tokens.text,
    },
  };

  if (Array.isArray(cleaned.layout.annotations)) {
    cleaned.layout.annotations = cleaned.layout.annotations.map((annotation: any) => ({
      ...annotation,
      font: {
        ...(annotation?.font || {}),
        size: BASE_FONT_SIZE,
        color: theme === 'light' ? '#000000' : tokens.text,
      },
    }));
  }

  const axisKeys = Object.keys(cleaned.layout).filter((key) => /^xaxis\d*$|^yaxis\d*$/.test(key));
  axisKeys.forEach((axisKey) => {
    const axis = cleaned.layout[axisKey];
    if (!axis || typeof axis !== 'object' || Array.isArray(axis)) return;

    // Scale-linked axes are a common source of Plotly relayout crashes.
    // Drop hard constraints and keep responsive autoscaling stable.
    delete axis.scaleanchor;
    delete axis.scaleratio;

    sanitizeAxisRange(axis);

    if (axis.type === 'log' && !axisHasPositiveData(data, axisKey)) {
      axis.type = 'linear';
      delete axis.range;
      axis.autorange = true;
    }

    axis.gridcolor = axis.gridcolor || tokens.grid;
    axis.zerolinecolor = axis.zerolinecolor || tokens.grid;
    axis.showline = true;
    axis.linecolor = tokens.chartBorder;
    axis.linewidth = axis.linewidth || 1;
    axis.mirror = true;
    axis.tickfont = { ...axis.tickfont, color: tokens.text, size: BASE_FONT_SIZE };
    if (axisKey.startsWith('xaxis') && axis.type === 'date') {
      axis.tickformat = DATE_TICK_FORMAT;
    }
    if (typeof axis.title === 'string') {
      axis.title = {
        text: axis.title,
        font: { color: tokens.text, size: BASE_FONT_SIZE },
      };
    } else if (axis.title && typeof axis.title === 'object') {
      axis.title = {
        ...axis.title,
        font: { ...axis.title.font, color: tokens.text, size: BASE_FONT_SIZE },
      };
    }
  });

  cleaned.layout.legend = {
    ...(cleaned.layout.legend || {}),
    orientation: 'v',
    x: LEGEND_X,
    y: LEGEND_Y,
    xanchor: 'left',
    yanchor: 'top',
    bgcolor: tokens.legendBg,
    bordercolor: tokens.legendBorder,
    borderwidth: cleaned.layout.legend?.borderwidth ?? 1,
    tracegroupgap: LEGEND_GAP,
    itemwidth: 40,
    itemsizing: 'constant',
    font: { ...cleaned.layout.legend?.font, color: tokens.text, size: BASE_FONT_SIZE },
  };

  cleaned.layout.hoverlabel = {
    ...(cleaned.layout.hoverlabel || {}),
    bgcolor: tokens.hoverBg,
    bordercolor: tokens.legendBorder,
    font: {
      ...(cleaned.layout.hoverlabel?.font || {}),
      color: tokens.text,
      family: cleaned.layout.hoverlabel?.font?.family || 'Inter, sans-serif',
      size: BASE_FONT_SIZE,
    },
    align: cleaned.layout.hoverlabel?.align || 'left',
  };

  cleaned.layout.margin = { t: 50, l: 0, r: 0, b: 0 };

  return cleaned;
}
