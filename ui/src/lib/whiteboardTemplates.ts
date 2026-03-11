/**
 * Pre-built Excalidraw templates for the whiteboard page.
 * Each template is a scene_data object: { elements, appState, files }.
 */

// Helper to generate unique-ish IDs (not crypto-random, just for static templates)
let _idCounter = 0;
const tid = () => `tmpl_${++_idCounter}`;

// Shared element defaults
const BASE = {
  fillStyle: 'hachure' as const,
  strokeWidth: 2,
  strokeStyle: 'solid' as const,
  roughness: 1,
  opacity: 100,
  angle: 0,
  isDeleted: false,
  groupIds: [] as string[],
  frameId: null,
  index: null,
  link: null,
  locked: false,
  version: 1,
  versionNonce: 1,
};

function rect(
  id: string,
  x: number,
  y: number,
  w: number,
  h: number,
  bg: string,
  stroke: string,
  boundElementIds: string[] = [],
) {
  return {
    ...BASE,
    id,
    type: 'rectangle' as const,
    x,
    y,
    width: w,
    height: h,
    strokeColor: stroke,
    backgroundColor: bg,
    seed: Math.floor(Math.random() * 2e9),
    roundness: { type: 3 },
    boundElements: [
      ...boundElementIds.map((eid) => ({ id: eid, type: 'text' as const })),
    ],
  };
}

function text(
  id: string,
  x: number,
  y: number,
  w: number,
  h: number,
  content: string,
  fontSize: number = 16,
  containerId: string | null = null,
  color: string = '#1e1e1e',
) {
  return {
    ...BASE,
    id,
    type: 'text' as const,
    x,
    y,
    width: w,
    height: h,
    strokeColor: color,
    backgroundColor: 'transparent',
    text: content,
    fontSize,
    fontFamily: 1, // Virgil (hand-drawn)
    textAlign: 'center' as const,
    verticalAlign: containerId ? ('middle' as const) : ('top' as const),
    containerId,
    originalText: content,
    autoResize: true,
    lineHeight: 1.25,
    seed: Math.floor(Math.random() * 2e9),
    roundness: null,
    boundElements: null,
  };
}

function arrow(
  id: string,
  points: [number, number][],
  x: number,
  y: number,
  startId: string | null = null,
  endId: string | null = null,
  color: string = '#1e1e1e',
) {
  return {
    ...BASE,
    id,
    type: 'arrow' as const,
    x,
    y,
    width: Math.abs(points[points.length - 1][0] - points[0][0]),
    height: Math.abs(points[points.length - 1][1] - points[0][1]),
    strokeColor: color,
    backgroundColor: 'transparent',
    points,
    seed: Math.floor(Math.random() * 2e9),
    roundness: { type: 2 },
    boundElements: null,
    startBinding: startId
      ? { elementId: startId, focus: 0, gap: 8, fixedPoint: null }
      : null,
    endBinding: endId
      ? { elementId: endId, focus: 0, gap: 8, fixedPoint: null }
      : null,
    startArrowhead: null,
    endArrowhead: 'arrow' as const,
    elbowed: false,
  };
}

// ── Investment Thesis Framework Template ──

// IDs
const TITLE_ID = tid();
const BOX_MACRO = tid();
const BOX_SIGNALS = tid();
const BOX_ALLOC = tid();
const BOX_DATA = tid();
const BOX_EXEC = tid();
const TXT_MACRO = tid();
const TXT_SIGNALS = tid();
const TXT_ALLOC = tid();
const TXT_DATA = tid();
const TXT_EXEC = tid();
const ARROW_1 = tid();
const ARROW_2 = tid();
const ARROW_3 = tid();
const ARROW_4 = tid();

// Layout constants
const BOX_W = 220;
const BOX_H = 150;
const GAP_X = 80;
const GAP_Y = 60;
const START_X = 100;
const START_Y = 120;

const row1Y = START_Y;
const row2Y = START_Y + BOX_H + GAP_Y;

const col1X = START_X;
const col2X = START_X + BOX_W + GAP_X;
const col3X = START_X + (BOX_W + GAP_X) * 2;

export const WELCOME_TEMPLATE = {
  elements: [
    // Title
    text(
      TITLE_ID,
      col1X,
      START_Y - 70,
      600,
      36,
      'Investment Thesis Framework',
      28,
      null,
      '#1e1e1e',
    ),

    // Row 1: Macro Outlook → Signals → Allocation
    rect(BOX_MACRO, col1X, row1Y, BOX_W, BOX_H, '#a5d8ff', '#1971c2', [TXT_MACRO]),
    text(
      TXT_MACRO,
      col1X,
      row1Y,
      BOX_W,
      BOX_H,
      'MACRO OUTLOOK\n\n• GDP / CPI\n• Fed Policy\n• Credit Spreads',
      16,
      BOX_MACRO,
    ),

    rect(BOX_SIGNALS, col2X, row1Y, BOX_W, BOX_H, '#b2f2bb', '#2f9e44', [TXT_SIGNALS]),
    text(
      TXT_SIGNALS,
      col2X,
      row1Y,
      BOX_W,
      BOX_H,
      'SIGNALS\n\n• Trend (40w SMA)\n• Macro Composite\n• VIX Regime',
      16,
      BOX_SIGNALS,
    ),

    rect(BOX_ALLOC, col3X, row1Y, BOX_W, BOX_H, '#ffd8a8', '#e8590c', [TXT_ALLOC]),
    text(
      TXT_ALLOC,
      col3X,
      row1Y,
      BOX_W,
      BOX_H,
      'ALLOCATION\n\n90% Risk-On\n50% Neutral\n10% Risk-Off',
      16,
      BOX_ALLOC,
    ),

    // Row 2: Data Sources, Execution
    rect(BOX_DATA, col1X, row2Y, BOX_W, BOX_H, '#d0bfff', '#7048e8', [TXT_DATA]),
    text(
      TXT_DATA,
      col1X,
      row2Y,
      BOX_W,
      BOX_H,
      'DATA SOURCES\n\n• FRED\n• Yahoo Finance\n• Bloomberg',
      16,
      BOX_DATA,
    ),

    rect(BOX_EXEC, col3X, row2Y, BOX_W, BOX_H, '#ffc9c9', '#e03131', [TXT_EXEC]),
    text(
      TXT_EXEC,
      col3X,
      row2Y,
      BOX_W,
      BOX_H,
      'EXECUTION\n\n• Rebalance\n• Backtest\n• Monitor',
      16,
      BOX_EXEC,
    ),

    // Arrows: Macro → Signals
    arrow(
      ARROW_1,
      [[0, 0], [GAP_X, 0]],
      col1X + BOX_W,
      row1Y + BOX_H / 2,
      BOX_MACRO,
      BOX_SIGNALS,
    ),

    // Arrows: Signals → Allocation
    arrow(
      ARROW_2,
      [[0, 0], [GAP_X, 0]],
      col2X + BOX_W,
      row1Y + BOX_H / 2,
      BOX_SIGNALS,
      BOX_ALLOC,
    ),

    // Arrows: Macro → Data Sources (down)
    arrow(
      ARROW_3,
      [[0, 0], [0, GAP_Y]],
      col1X + BOX_W / 2,
      row1Y + BOX_H,
      BOX_MACRO,
      BOX_DATA,
    ),

    // Arrows: Allocation → Execution (down)
    arrow(
      ARROW_4,
      [[0, 0], [0, GAP_Y]],
      col3X + BOX_W / 2,
      row1Y + BOX_H,
      BOX_ALLOC,
      BOX_EXEC,
    ),
  ],
  appState: {
    viewBackgroundColor: '#ffffff',
    gridSize: null,
  },
  files: {},
};
