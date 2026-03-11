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


// ── Macro Research Pipeline Template ──

// Layout
const MR_BOX_W = 180;
const MR_BOX_H = 120;
const MR_GAP_X = 60;
const MR_GAP_Y = 50;
const MR_START_X = 60;
const MR_START_Y = 100;

// Source row (row 1) — 7 boxes
const mr_srcY = MR_START_Y;
const mr_srcX = (i: number) => MR_START_X + i * (MR_BOX_W + 20);

// Processing row (row 2)
const mr_procY = MR_START_Y + MR_BOX_H + MR_GAP_Y;

// Analysis row (row 3)
const mr_analysisY = mr_procY + MR_BOX_H + MR_GAP_Y;

// Output row (row 4)
const mr_outputY = mr_analysisY + MR_BOX_H + MR_GAP_Y;

// IDs
const MR_TITLE = tid();

// Sources
const MR_YT = tid(); const MR_YT_T = tid();
const MR_CB = tid(); const MR_CB_T = tid();
const MR_NEWS = tid(); const MR_NEWS_T = tid();
const MR_TG = tid(); const MR_TG_T = tid();
const MR_DATA = tid(); const MR_DATA_T = tid();
const MR_DRIVE = tid(); const MR_DRIVE_T = tid();
const MR_REPORTS = tid(); const MR_REPORTS_T = tid();

// Processing
const MR_NLM = tid(); const MR_NLM_T = tid();

// Analysis
const MR_BRIEF = tid(); const MR_BRIEF_T = tid();
const MR_RISK = tid(); const MR_RISK_T = tid();
const MR_TAKE = tid(); const MR_TAKE_T = tid();

// Outputs
const MR_INFOG = tid(); const MR_INFOG_T = tid();
const MR_SLIDES = tid(); const MR_SLIDES_T = tid();
const MR_DB = tid(); const MR_DB_T = tid();
const MR_VAULT = tid(); const MR_VAULT_T = tid();

// Arrows
const MR_A1 = tid(); const MR_A2 = tid(); const MR_A3 = tid();
const MR_A4 = tid(); const MR_A5 = tid(); const MR_A6 = tid();
const MR_A7 = tid();
const MR_A8 = tid(); const MR_A9 = tid(); const MR_A10 = tid();
const MR_A11 = tid(); const MR_A12 = tid();
const MR_A13 = tid(); const MR_A14 = tid();

// Source section label
const MR_SRC_LABEL = tid();
const MR_PROC_LABEL = tid();
const MR_ANALYSIS_LABEL = tid();
const MR_OUT_LABEL = tid();

// Narrower boxes for source row
const SRC_W = 140;
const SRC_H = 90;

// NotebookLM box — wide
const NLM_W = 500;
const NLM_H = 100;

// Analysis boxes
const AN_W = 200;
const AN_H = 100;

// Output boxes
const OUT_W = 160;
const OUT_H = 80;

// Source positions (7 across)
const srcX = (i: number) => MR_START_X + i * (SRC_W + 14);
const srcCenterX = MR_START_X + (7 * (SRC_W + 14) - 14) / 2;

// NotebookLM centered
const nlmX = srcCenterX - NLM_W / 2;

// Analysis 3 boxes centered
const anTotalW = 3 * AN_W + 2 * 40;
const anStartX = srcCenterX - anTotalW / 2;
const anX = (i: number) => anStartX + i * (AN_W + 40);

// Output 4 boxes centered
const outTotalW = 4 * OUT_W + 3 * 30;
const outStartX = srcCenterX - outTotalW / 2;
const outX = (i: number) => outStartX + i * (OUT_W + 30);

export const MACRO_RESEARCH_TEMPLATE = {
  elements: [
    // Title
    text(MR_TITLE, MR_START_X, MR_START_Y - 60, 800, 36,
      'Macro Research Pipeline', 28, null, '#1e1e1e'),

    // Section labels
    text(MR_SRC_LABEL, MR_START_X, mr_srcY - 24, 200, 20,
      'SOURCES', 14, null, '#868e96'),
    text(MR_PROC_LABEL, MR_START_X, mr_procY - 24, 200, 20,
      'PROCESSING', 14, null, '#868e96'),
    text(MR_ANALYSIS_LABEL, MR_START_X, mr_analysisY - 24, 200, 20,
      'ANALYSIS', 14, null, '#868e96'),
    text(MR_OUT_LABEL, MR_START_X, mr_outputY - 24, 200, 20,
      'OUTPUTS', 14, null, '#868e96'),

    // ── Row 1: Sources ──
    rect(MR_YT, srcX(0), mr_srcY, SRC_W, SRC_H, '#a5d8ff', '#1971c2', [MR_YT_T]),
    text(MR_YT_T, srcX(0), mr_srcY, SRC_W, SRC_H,
      'YouTube\n\n35 channels\n20 top videos', 13, MR_YT),

    rect(MR_CB, srcX(1), mr_srcY, SRC_W, SRC_H, '#b2f2bb', '#2f9e44', [MR_CB_T]),
    text(MR_CB_T, srcX(1), mr_srcY, SRC_W, SRC_H,
      'Central Banks\n\nFed, BoE, ECB\nMinutes & Stmts', 13, MR_CB),

    rect(MR_NEWS, srcX(2), mr_srcY, SRC_W, SRC_H, '#ffd8a8', '#e8590c', [MR_NEWS_T]),
    text(MR_NEWS_T, srcX(2), mr_srcY, SRC_W, SRC_H,
      'News RSS\n\n176 articles\nMultiple feeds', 13, MR_NEWS),

    rect(MR_TG, srcX(3), mr_srcY, SRC_W, SRC_H, '#d0bfff', '#7048e8', [MR_TG_T]),
    text(MR_TG_T, srcX(3), mr_srcY, SRC_W, SRC_H,
      'Telegram\n\n536 messages\nMacro channels', 13, MR_TG),

    rect(MR_DATA, srcX(4), mr_srcY, SRC_W, SRC_H, '#ffc9c9', '#e03131', [MR_DATA_T]),
    text(MR_DATA_T, srcX(4), mr_srcY, SRC_W, SRC_H,
      'Macro Data\n\n29 indicators\nTimeseries DB', 13, MR_DATA),

    rect(MR_DRIVE, srcX(5), mr_srcY, SRC_W, SRC_H, '#99e9f2', '#0c8599', [MR_DRIVE_T]),
    text(MR_DRIVE_T, srcX(5), mr_srcY, SRC_W, SRC_H,
      'Google Drive\n\nRecent files\nResearch docs', 13, MR_DRIVE),

    rect(MR_REPORTS, srcX(6), mr_srcY, SRC_W, SRC_H, '#eebefa', '#9c36b5', [MR_REPORTS_T]),
    text(MR_REPORTS_T, srcX(6), mr_srcY, SRC_W, SRC_H,
      'Reports\n\n80 research URLs\nBuyside/Sellside', 13, MR_REPORTS),

    // ── Row 2: NotebookLM ──
    rect(MR_NLM, nlmX, mr_procY, NLM_W, NLM_H, '#fff3bf', '#f08c00', [MR_NLM_T]),
    text(MR_NLM_T, nlmX, mr_procY, NLM_W, NLM_H,
      'Google NotebookLM\n\nIngest all sources → Generate briefing, risk scorecard, takeaways\nGenerate infographic & slide deck', 14, MR_NLM),

    // ── Row 3: Analysis Outputs ──
    rect(MR_BRIEF, anX(0), mr_analysisY, AN_W, AN_H, '#d3f9d8', '#37b24d', [MR_BRIEF_T]),
    text(MR_BRIEF_T, anX(0), mr_analysisY, AN_W, AN_H,
      'Briefing\n\nMarket state, themes\ngeopolitics, policy', 13, MR_BRIEF),

    rect(MR_RISK, anX(1), mr_analysisY, AN_W, AN_H, '#ffe3e3', '#f03e3e', [MR_RISK_T]),
    text(MR_RISK_T, anX(1), mr_analysisY, AN_W, AN_H,
      'Risk Scorecard\n\nGeopolitical, Credit\nLiquidity, Inflation', 13, MR_RISK),

    rect(MR_TAKE, anX(2), mr_analysisY, AN_W, AN_H, '#e7f5ff', '#1c7ed6', [MR_TAKE_T]),
    text(MR_TAKE_T, anX(2), mr_analysisY, AN_W, AN_H,
      'Takeaways\n\nAsset positioning\nActionable insights', 13, MR_TAKE),

    // ── Row 4: Final Outputs ──
    rect(MR_INFOG, outX(0), mr_outputY, OUT_W, OUT_H, '#fff4e6', '#e8590c', [MR_INFOG_T]),
    text(MR_INFOG_T, outX(0), mr_outputY, OUT_W, OUT_H,
      'Infographic\nPNG', 13, MR_INFOG),

    rect(MR_SLIDES, outX(1), mr_outputY, OUT_W, OUT_H, '#f3f0ff', '#7048e8', [MR_SLIDES_T]),
    text(MR_SLIDES_T, outX(1), mr_outputY, OUT_W, OUT_H,
      'Slide Deck\nPDF', 13, MR_SLIDES),

    rect(MR_DB, outX(2), mr_outputY, OUT_W, OUT_H, '#e6fcf5', '#0ca678', [MR_DB_T]),
    text(MR_DB_T, outX(2), mr_outputY, OUT_W, OUT_H,
      'PostgreSQL\nDB Storage', 13, MR_DB),

    rect(MR_VAULT, outX(3), mr_outputY, OUT_W, OUT_H, '#f8f0fc', '#ae3ec9', [MR_VAULT_T]),
    text(MR_VAULT_T, outX(3), mr_outputY, OUT_W, OUT_H,
      'Obsidian Vault\nMarkdown', 13, MR_VAULT),

    // ── Arrows: Sources → NotebookLM ──
    arrow(MR_A1, [[0, 0], [0, MR_GAP_Y]], srcX(0) + SRC_W / 2, mr_srcY + SRC_H, MR_YT, MR_NLM),
    arrow(MR_A2, [[0, 0], [0, MR_GAP_Y]], srcX(1) + SRC_W / 2, mr_srcY + SRC_H, MR_CB, MR_NLM),
    arrow(MR_A3, [[0, 0], [0, MR_GAP_Y]], srcX(2) + SRC_W / 2, mr_srcY + SRC_H, MR_NEWS, MR_NLM),
    arrow(MR_A4, [[0, 0], [0, MR_GAP_Y]], srcX(3) + SRC_W / 2, mr_srcY + SRC_H, MR_TG, MR_NLM),
    arrow(MR_A5, [[0, 0], [0, MR_GAP_Y]], srcX(4) + SRC_W / 2, mr_srcY + SRC_H, MR_DATA, MR_NLM),
    arrow(MR_A6, [[0, 0], [0, MR_GAP_Y]], srcX(5) + SRC_W / 2, mr_srcY + SRC_H, MR_DRIVE, MR_NLM),
    arrow(MR_A7, [[0, 0], [0, MR_GAP_Y]], srcX(6) + SRC_W / 2, mr_srcY + SRC_H, MR_REPORTS, MR_NLM),

    // NotebookLM → Analysis
    arrow(MR_A8, [[0, 0], [0, MR_GAP_Y]], nlmX + NLM_W * 0.25, mr_procY + NLM_H, MR_NLM, MR_BRIEF),
    arrow(MR_A9, [[0, 0], [0, MR_GAP_Y]], nlmX + NLM_W * 0.5, mr_procY + NLM_H, MR_NLM, MR_RISK),
    arrow(MR_A10, [[0, 0], [0, MR_GAP_Y]], nlmX + NLM_W * 0.75, mr_procY + NLM_H, MR_NLM, MR_TAKE),

    // Analysis → Outputs
    arrow(MR_A11, [[0, 0], [0, MR_GAP_Y]], anX(0) + AN_W / 2, mr_analysisY + AN_H, MR_BRIEF, MR_DB),
    arrow(MR_A12, [[0, 0], [0, MR_GAP_Y]], anX(1) + AN_W / 2, mr_analysisY + AN_H, MR_RISK, MR_INFOG),
    arrow(MR_A13, [[0, 0], [0, MR_GAP_Y]], anX(2) + AN_W / 2, mr_analysisY + AN_H, MR_TAKE, MR_SLIDES),
    arrow(MR_A14, [[0, 0], [0, MR_GAP_Y]], anX(2) + AN_W / 2 + 60, mr_analysisY + AN_H, MR_TAKE, MR_VAULT),
  ],
  appState: {
    viewBackgroundColor: '#ffffff',
    gridSize: null,
  },
  files: {},
};
