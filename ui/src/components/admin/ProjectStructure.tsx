'use client';

import { useState, useMemo } from 'react';
import { ChevronRight, Folder, FolderOpen, FileCode, FileText, Paintbrush, Layers, GitBranch, Cpu, Search } from 'lucide-react';

/* ── Tree data ──────────────────────────────────────────────────────────────── */

interface TreeNode {
  name: string;
  desc?: string;
  children?: TreeNode[];
}

const TREE: TreeNode[] = [
  {
    name: 'app/', desc: 'Pages (Next.js App Router)', children: [
      { name: 'layout.tsx', desc: 'Root layout \u2014 providers, auth, theme, error boundary' },
      { name: 'page.tsx', desc: 'Dashboard \u2014 scorecards, VAMS momentum, market pulse, intel brief' },
      { name: 'globals.css', desc: 'CSS variables, design tokens, utility classes' },
      { name: 'error.tsx', desc: 'Global error fallback' },
      { name: 'not-found.tsx', desc: '404 page' },
      {
        name: 'login/', desc: 'Login (public)', children: [
          { name: 'page.tsx', desc: 'Login form' },
        ]
      },
      {
        name: 'register/', desc: 'Registration (public)', children: [
          { name: 'page.tsx', desc: 'Registration form' },
        ]
      },
      {
        name: 'charts/', desc: 'Chart gallery \u2014 browse & search saved charts', children: [
          { name: 'page.tsx', desc: 'Chart gallery grid' },
          { name: 'packs/', desc: 'Chart pack viewer \u2014 grouped chart collections' },
        ]
      },
      { name: 'chartpack/', desc: 'Chart pack editor \u2014 build & arrange chart packs' },
      { name: 'studio/', desc: 'Chart studio \u2014 full chart creation IDE with Monaco editor' },
      { name: 'macro/', desc: 'Macro strategy \u2014 regime detection, backtests, factor analysis' },
      { name: 'intel/', desc: 'Intelligence \u2014 briefings, wartime alerts, stress tests' },
      { name: 'research/', desc: 'Research library \u2014 reports, PDFs, briefing archive' },
      { name: 'screener/', desc: 'Stock screener \u2014 rankings, fund flows, methodology' },
      { name: 'technical/', desc: 'Technical analysis \u2014 Elliott Wave, TD Sequential, overlays' },
      { name: 'quant/', desc: 'Quantitative tools \u2014 correlation, regression, PCA, VaR' },
      { name: 'wartime/', desc: 'Wartime dashboard \u2014 crisis monitoring & stress scenarios' },
      { name: 'whiteboard/', desc: 'Excalidraw whiteboard \u2014 freeform diagramming' },
      { name: 'datatool/', desc: 'Data tools \u2014 template upload/download, series management' },
      {
        name: 'admin/', desc: 'Admin panel', children: [
          { name: 'timeseries/', desc: 'Series CRUD, user management, system logs' },
        ]
      },
    ]
  },
  {
    name: 'components/', desc: 'React components', children: [
      {
        name: 'layout/', desc: 'App chrome \u2014 always visible', children: [
          { name: 'AppShell.tsx', desc: 'Page wrapper \u2014 navbar + footer + Ctrl+K palette' },
          { name: 'Navbar.tsx', desc: 'Top navigation bar (40px fixed)' },
          { name: 'Footer.tsx', desc: 'Page footer' },
          { name: 'NavigatorShell.tsx', desc: 'Collapsible sidebar layout (technical, quant)' },
          { name: 'PageSkeleton.tsx', desc: 'Full-page loading skeleton' },
        ]
      },
      {
        name: 'shared/', desc: 'Reusable across any feature', children: [
          { name: 'Chart.tsx', desc: 'Plotly chart renderer with theme integration' },
          { name: 'ChartErrorBoundary.tsx', desc: 'Error boundary for individual charts' },
          { name: 'ErrorBoundary.tsx', desc: 'App-wide React error boundary' },
          { name: 'Modal.tsx', desc: 'Accessible modal dialog with focus trap' },
          { name: 'GlobalSearchPalette.tsx', desc: 'Ctrl+K command palette for navigation' },
        ]
      },
      {
        name: 'auth/', desc: 'Authentication UI', children: [
          { name: 'AuthGuard.tsx', desc: 'Route guard \u2014 redirects unauthenticated users' },
          { name: 'SessionExpiredModal.tsx', desc: 'Re-auth prompt on token expiry' },
        ]
      },
      {
        name: 'tasks/', desc: 'Background job system', children: [
          { name: 'TaskProvider.tsx', desc: 'Context provider \u2014 polls /api/jobs, exposes useTasks()' },
          { name: 'TaskNotifications.tsx', desc: 'Navbar dropdown showing running/completed tasks' },
        ]
      },
      {
        name: 'admin/', desc: 'Admin-only components', children: [
          { name: 'AdminLogViewer.tsx', desc: 'System log viewer' },
          { name: 'TimeseriesManager.tsx', desc: 'Series CRUD, bulk import, sync controls' },
          { name: 'UserManager.tsx', desc: 'User account management' },
          { name: 'ProjectStructure.tsx', desc: 'This page \u2014 project structure viewer' },
        ]
      },
      {
        name: 'dashboard/', desc: 'Dashboard page widgets', children: [
          { name: 'Scorecards.tsx', desc: 'RRG-style asset scorecards with tactical/dynamic phases' },
          { name: 'Technicals.tsx', desc: 'Technical momentum regime chart' },
          { name: 'MarketPulse.tsx', desc: 'Cross-asset market pulse heatmap' },
        ]
      },
      {
        name: 'chart-editor/', desc: 'Chart studio internals', children: [
          { name: 'index.tsx', desc: 'Main editor component (CustomChartEditor)' },
          { name: 'EditorPanel.tsx', desc: 'Monaco code editor for chart expressions' },
          { name: 'SidebarPanel.tsx', desc: 'Series selector & chart list sidebar' },
          { name: 'PreviewPanel.tsx', desc: 'Live chart preview' },
          { name: 'FormatPanel.tsx', desc: 'Chart formatting controls' },
          { name: 'PropertiesDrawer.tsx', desc: 'Chart metadata & settings drawer' },
          { name: 'ActivityBar.tsx', desc: 'Left icon bar (files, search, settings)' },
          { name: 'WorkspaceHeader.tsx', desc: 'Editor toolbar with save/export actions' },
          { name: 'DeleteModal.tsx', desc: 'Chart deletion confirmation' },
          { name: 'PdfNotification.tsx', desc: 'PDF export status toast' },
        ]
      },
      {
        name: 'chartpack/', desc: 'Chart pack editor components', children: [
          { name: 'ChartEditOverlay.tsx', desc: 'Inline chart edit overlay within packs' },
        ]
      },
      {
        name: 'macro/', desc: 'Macro strategy tab system', children: [
          { name: 'OverviewTab.tsx', desc: 'Summary \u2014 regime probabilities, cross-market, robustness' },
          { name: 'RegimeTab.tsx', desc: 'Growth/inflation regime detail with indicator waterfall' },
          { name: 'StrategyTab.tsx', desc: 'Backtest results \u2014 equity curves, drawdowns, stats' },
          { name: 'StrategyFactorsTab.tsx', desc: 'Factor decomposition & contribution analysis' },
          { name: 'RegimeStrategyRegimeTab.tsx', desc: 'Regime-conditional strategy performance' },
          { name: 'CrossMarketTab.tsx', desc: 'Cross-asset regime correlation' },
          { name: 'RobustnessTab.tsx', desc: 'Robustness checks & sensitivity analysis' },
          { name: 'MethodologyTab.tsx', desc: 'Strategy methodology documentation' },
          { name: 'ComponentBacktest.tsx', desc: 'Single-component backtest chart' },
          { name: 'IndicatorWaterfall.tsx', desc: 'Indicator waterfall visualization' },
          { name: 'SharedComponents.tsx', desc: 'LoadingSpinner, ErrorBox, RegimeProbBar, etc.' },
          { name: 'types.ts', desc: 'TypeScript interfaces for macro data' },
          { name: 'constants.ts', desc: 'Tab definitions, color maps' },
          { name: 'helpers.ts', desc: 'Formatting & calculation helpers' },
        ]
      },
      {
        name: 'intel/', desc: 'Intelligence & briefing components', children: [
          { name: 'Briefing.tsx', desc: 'AI-generated macro briefing with TTS playback' },
          { name: 'IntelHeader.tsx', desc: 'Intel page header with date/filter controls' },
          { name: 'IntelTabs.tsx', desc: 'Tab navigation for intel views' },
        ]
      },
      {
        name: 'screener/', desc: 'Stock screener tab system', children: [
          { name: 'RankingsTab.tsx', desc: 'Asset rankings table' },
          { name: 'FlowsTab.tsx', desc: 'Fund flow analysis' },
          { name: 'MethodologyTab.tsx', desc: 'Screener methodology docs' },
          { name: 'types.ts', desc: 'Screener type definitions' },
          { name: 'constants.ts', desc: 'Screener constants' },
        ]
      },
      {
        name: 'wartime/', desc: 'Crisis & stress test components', children: [
          { name: 'WartimeContent.tsx', desc: 'Wartime intelligence dashboard' },
          { name: 'StressTestContent.tsx', desc: 'Portfolio stress test scenarios' },
        ]
      },
      {
        name: 'whiteboard/', desc: 'Whiteboard components', children: [
          { name: 'ExcalidrawEditor.tsx', desc: 'Excalidraw integration with theme sync' },
        ]
      },
    ]
  },
  {
    name: 'context/', desc: 'React contexts (app-wide state)', children: [
      { name: 'AuthContext.tsx', desc: 'JWT auth \u2014 login, logout, register, reauth, useAuth()' },
      { name: 'ThemeContext.tsx', desc: 'Dark/light theme \u2014 useTheme(), persists to localStorage' },
    ]
  },
  {
    name: 'hooks/', desc: 'Custom React hooks', children: [
      { name: 'useChartEditor.ts', desc: 'Chart studio state machine (series, layout, save/load)' },
      { name: 'useCountUp.ts', desc: 'Animated number counter' },
      { name: 'useDebounce.ts', desc: 'Debounced value for search inputs' },
      { name: 'useFocusTrap.ts', desc: 'Accessibility focus trap for modals' },
      { name: 'useIntelState.ts', desc: 'Intel page tab/filter state' },
      { name: 'useNativeInputStyle.ts', desc: 'Browser-native input styling helper' },
      { name: 'useResponsiveSidebar.ts', desc: 'Sidebar collapse state with breakpoint detection' },
    ]
  },
  {
    name: 'lib/', desc: 'Utilities & configuration', children: [
      { name: 'api.ts', desc: 'API client \u2014 apiFetch(), apiFetchJson(), cookie auth' },
      { name: 'buildChartFigure.ts', desc: 'Plotly figure builder from chart expression DSL' },
      { name: 'chartTheme.ts', desc: 'Plotly theme \u2014 applyChartTheme() for dark/light' },
      { name: 'constants.ts', desc: 'App-wide constants (API base URL, etc.)' },
      { name: 'monacoCompletions.ts', desc: 'Monaco editor autocomplete for chart DSL' },
      { name: 'whiteboardTemplates.ts', desc: 'Excalidraw template definitions' },
    ]
  },
  {
    name: 'providers/', desc: 'React providers', children: [
      { name: 'QueryProvider.tsx', desc: 'TanStack Query client + devtools' },
    ]
  },
  {
    name: 'types/', desc: 'Type definitions', children: [
      { name: 'chart.ts', desc: 'ChartMeta, CustomChartListItem interfaces' },
    ]
  },
];

/* ── Stats ───────────────────────────────────────────────────────────────────── */

function countNodes(nodes: TreeNode[]): { folders: number; files: number } {
  let folders = 0, files = 0;
  for (const n of nodes) {
    if (n.children) { folders++; const c = countNodes(n.children); folders += c.folders; files += c.files; }
    else files++;
  }
  return { folders, files };
}

/* ── Tree node component ─────────────────────────────────────────────────────── */

function TreeNodeRow({ node, depth, filter }: { node: TreeNode; depth: number; filter: string }) {
  const [open, setOpen] = useState(depth < 1);
  const isDir = !!node.children;
  const isTsx = node.name.endsWith('.tsx');
  const isTs = node.name.endsWith('.ts');
  const isCss = node.name.endsWith('.css');

  const matchesFilter = filter
    ? node.name.toLowerCase().includes(filter) || (node.desc?.toLowerCase().includes(filter) ?? false)
    : true;

  const childMatches = filter && node.children
    ? node.children.some(function check(c: TreeNode): boolean {
        if (c.name.toLowerCase().includes(filter) || (c.desc?.toLowerCase().includes(filter) ?? false)) return true;
        return c.children?.some(check) ?? false;
      })
    : false;

  const shouldShow = !filter || matchesFilter || childMatches;
  const shouldForceOpen = filter && childMatches;

  if (!shouldShow) return null;

  return (
    <>
      <div
        className={`group flex items-center gap-1.5 py-[3px] cursor-default transition-colors rounded-sm hover:bg-foreground/[0.03] ${
          matchesFilter && filter ? 'bg-primary/[0.04]' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => isDir && setOpen(!open)}
      >
        {/* Expand chevron */}
        {isDir ? (
          <ChevronRight className={`w-3 h-3 text-muted-foreground/30 transition-transform duration-150 flex-shrink-0 ${
            (open || shouldForceOpen) ? 'rotate-90' : ''
          }`} />
        ) : (
          <span className="w-3 flex-shrink-0" />
        )}

        {/* Icon */}
        {isDir ? (
          (open || shouldForceOpen)
            ? <FolderOpen className="w-3.5 h-3.5 text-primary/50 flex-shrink-0" />
            : <Folder className="w-3.5 h-3.5 text-primary/40 flex-shrink-0" />
        ) : isTsx ? (
          <FileCode className="w-3.5 h-3.5 text-sky-400/50 flex-shrink-0" />
        ) : isTs ? (
          <FileCode className="w-3.5 h-3.5 text-emerald-400/40 flex-shrink-0" />
        ) : isCss ? (
          <Paintbrush className="w-3.5 h-3.5 text-violet-400/40 flex-shrink-0" />
        ) : (
          <FileText className="w-3.5 h-3.5 text-muted-foreground/30 flex-shrink-0" />
        )}

        {/* Name */}
        <span className={`text-[12px] font-mono ${isDir ? 'font-semibold text-foreground/80' : 'text-foreground/60'}`}>
          {node.name}
        </span>

        {/* Description */}
        {node.desc && (
          <span className="text-[10px] text-muted-foreground/35 truncate ml-1 hidden sm:inline">
            {node.desc}
          </span>
        )}
      </div>

      {/* Children */}
      {isDir && (open || shouldForceOpen) && node.children?.map((child) => (
        <TreeNodeRow key={child.name} node={child} depth={depth + 1} filter={filter} />
      ))}
    </>
  );
}

/* ── Architecture cards ──────────────────────────────────────────────────────── */

const PROVIDER_CHAIN = [
  'QueryProvider', 'AuthProvider', 'ThemeProvider', 'TaskProvider', 'ErrorBoundary', 'SessionExpiredModal', '[pages]'
];

const KEY_PATTERNS = [
  { label: 'Data fetching', value: 'TanStack Query + apiFetchJson()' },
  { label: 'Charts', value: 'Plotly via react-plotly.js, themed with applyChartTheme()' },
  { label: 'Auth', value: 'JWT in HttpOnly cookies, useAuth() context' },
  { label: 'Chart DSL', value: 'Monaco editor, server-side eval with auth guard' },
  { label: 'Background tasks', value: 'TaskProvider polls /api/jobs, navbar notifications' },
];

const DESIGN_TOKENS = [
  { label: 'Aesthetic', value: 'Dark-first quant terminal (Koyfin/Bloomberg)' },
  { label: 'Primary', value: 'Electric blue rgb(var(--primary))' },
  { label: 'Fonts', value: 'Inter (body) + Space Mono (code/data)' },
  { label: 'Radius', value: '0.5rem (8px)' },
  { label: 'Shadows', value: 'shadow-md max for cards, shadow-lg for modals' },
];

/* ── Main component ──────────────────────────────────────────────────────────── */

export default function ProjectStructure() {
  const [filter, setFilter] = useState('');
  const stats = useMemo(() => countNodes(TREE), []);
  const normalizedFilter = filter.toLowerCase().trim();

  return (
    <div className="space-y-4">
      {/* ── Stats row ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-3 px-3 py-2 rounded-[var(--radius)] border border-border/30 bg-card">
          <div className="text-center">
            <div className="text-[15px] font-semibold font-mono text-foreground tabular-nums">{stats.folders}</div>
            <div className="stat-label">Folders</div>
          </div>
          <div className="w-px h-6 bg-border/20" />
          <div className="text-center">
            <div className="text-[15px] font-semibold font-mono text-foreground tabular-nums">{stats.files}</div>
            <div className="stat-label">Files</div>
          </div>
        </div>

        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground/30" />
          <input
            type="text"
            placeholder="Filter files..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-7 pl-7 pr-3 text-[11px] font-mono bg-background border border-border/40 rounded-[var(--radius)] text-foreground placeholder:text-muted-foreground/25 focus:outline-none focus:border-primary/40 w-48"
          />
        </div>
      </div>

      {/* ── File tree ──────────────────────────────────────────── */}
      <div className="panel-card p-2 overflow-x-auto max-h-[520px] overflow-y-auto no-scrollbar">
        <div className="min-w-[400px]">
          <div className="flex items-center gap-1.5 px-2 py-1.5 mb-1 border-b border-border/15">
            <Layers className="w-3 h-3 text-primary/50" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/40">ui/src/</span>
          </div>
          {TREE.map((node) => (
            <TreeNodeRow key={node.name} node={node} depth={0} filter={normalizedFilter} />
          ))}
        </div>
      </div>

      {/* ── Architecture & patterns ────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Provider chain */}
        <div className="panel-card p-3">
          <div className="flex items-center gap-1.5 mb-2.5">
            <GitBranch className="w-3 h-3 text-primary/50" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/50">Provider Nesting</span>
          </div>
          <div className="flex flex-wrap items-center gap-1">
            {PROVIDER_CHAIN.map((p, i) => (
              <span key={p} className="flex items-center gap-1">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                  p === '[pages]'
                    ? 'bg-primary/10 text-primary/70 border border-primary/20'
                    : 'bg-foreground/[0.04] text-foreground/60 border border-border/20'
                }`}>
                  {p}
                </span>
                {i < PROVIDER_CHAIN.length - 1 && (
                  <ChevronRight className="w-2.5 h-2.5 text-muted-foreground/20" />
                )}
              </span>
            ))}
          </div>
        </div>

        {/* Design tokens */}
        <div className="panel-card p-3">
          <div className="flex items-center gap-1.5 mb-2.5">
            <Paintbrush className="w-3 h-3 text-primary/50" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/50">Design System</span>
          </div>
          <div className="space-y-1">
            {DESIGN_TOKENS.map((t) => (
              <div key={t.label} className="flex items-baseline gap-2">
                <span className="text-[10px] font-mono font-semibold text-muted-foreground/40 w-16 flex-shrink-0 text-right">{t.label}</span>
                <span className="text-[11px] text-foreground/60">{t.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Key patterns */}
        <div className="panel-card p-3 md:col-span-2">
          <div className="flex items-center gap-1.5 mb-2.5">
            <Cpu className="w-3 h-3 text-primary/50" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/50">Key Patterns</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-1">
            {KEY_PATTERNS.map((p) => (
              <div key={p.label} className="flex items-baseline gap-2">
                <span className="text-[10px] font-mono font-semibold text-primary/50 flex-shrink-0">{p.label}</span>
                <span className="text-[10px] text-muted-foreground/50">{p.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
