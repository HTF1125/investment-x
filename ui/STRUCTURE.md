# Investment-X Frontend Structure

Macro research & portfolio intelligence platform.
Next.js 14 (App Router) + React + TanStack Query + Plotly + Tailwind CSS.

```
ui/src/
│
├── app/                          # Pages (Next.js App Router)
│   ├── layout.tsx                # Root layout — providers, auth, theme, error boundary
│   ├── page.tsx                  # Dashboard — scorecards, VAMS momentum, market pulse, intel brief
│   ├── error.tsx                 # Global error fallback
│   ├── not-found.tsx             # 404 page
│   ├── globals.css               # CSS variables, design tokens, utility classes
│   │
│   ├── login/                    # Login page (public)
│   ├── register/                 # Registration page (public)
│   │
│   ├── charts/                   # Chart gallery — browse & search saved charts
│   │   └── packs/               # Chart pack viewer — grouped chart collections
│   ├── chartpack/                # Chart pack editor — build & arrange chart packs
│   ├── studio/                   # Chart studio — full chart creation IDE with Monaco editor
│   │
│   ├── macro/                    # Macro strategy — regime detection, backtests, factor analysis
│   ├── intel/                    # Intelligence — briefings, wartime alerts, stress tests
│   ├── research/                 # Research library — reports, PDFs, briefing archive
│   ├── screener/                 # Stock screener — rankings, fund flows, methodology
│   │
│   ├── technical/                # Technical analysis — Elliott Wave, TD Sequential, overlays
│   ├── quant/                    # Quantitative tools — correlation, regression, PCA, VaR
│   ├── wartime/                  # Wartime dashboard — crisis monitoring & stress scenarios
│   ├── whiteboard/               # Excalidraw whiteboard — freeform diagramming
│   ├── datatool/                 # Data tools — template upload/download, series management
│   │
│   └── admin/
│       └── timeseries/           # Admin panel — series CRUD, user management, system logs
│
├── components/
│   ├── layout/                   # App chrome — always visible
│   │   ├── AppShell.tsx          # Page wrapper — navbar + footer + Ctrl+K palette
│   │   ├── Navbar.tsx            # Top navigation bar (40px fixed)
│   │   ├── Footer.tsx            # Page footer
│   │   ├── NavigatorShell.tsx    # Collapsible sidebar layout (technical, quant pages)
│   │   └── PageSkeleton.tsx      # Full-page loading skeleton
│   │
│   ├── shared/                   # Reusable across any feature
│   │   ├── Chart.tsx             # Plotly chart renderer with theme integration
│   │   ├── ChartErrorBoundary.tsx# Error boundary for individual charts
│   │   ├── ErrorBoundary.tsx     # App-wide React error boundary
│   │   ├── Modal.tsx             # Accessible modal dialog with focus trap
│   │   └── GlobalSearchPalette.tsx # Ctrl+K command palette for navigation
│   │
│   ├── auth/                     # Authentication UI
│   │   ├── AuthGuard.tsx         # Route guard — redirects unauthenticated users
│   │   └── SessionExpiredModal.tsx # Re-auth prompt on token expiry
│   │
│   ├── tasks/                    # Background job system
│   │   ├── TaskProvider.tsx      # Context provider — polls /api/jobs, exposes useTasks()
│   │   └── TaskNotifications.tsx # Navbar dropdown showing running/completed tasks
│   │
│   ├── admin/                    # Admin-only components
│   │   ├── AdminLogViewer.tsx    # System log viewer
│   │   ├── TimeseriesManager.tsx # Series CRUD, bulk import, sync controls
│   │   └── UserManager.tsx       # User account management
│   │
│   ├── dashboard/                # Dashboard page widgets
│   │   ├── Scorecards.tsx        # RRG-style asset scorecards with tactical/dynamic phases
│   │   ├── Technicals.tsx        # Technical momentum regime chart
│   │   └── MarketPulse.tsx       # Cross-asset market pulse heatmap
│   │
│   ├── chart-editor/             # Chart studio internals
│   │   ├── index.tsx             # Main editor component (CustomChartEditor)
│   │   ├── EditorPanel.tsx       # Monaco code editor for chart expressions
│   │   ├── SidebarPanel.tsx      # Series selector & chart list sidebar
│   │   ├── PreviewPanel.tsx      # Live chart preview
│   │   ├── FormatPanel.tsx       # Chart formatting controls
│   │   ├── PropertiesDrawer.tsx  # Chart metadata & settings drawer
│   │   ├── ActivityBar.tsx       # Left icon bar (files, search, settings)
│   │   ├── WorkspaceHeader.tsx   # Editor toolbar with save/export actions
│   │   ├── DeleteModal.tsx       # Chart deletion confirmation
│   │   └── PdfNotification.tsx   # PDF export status toast
│   │
│   ├── chartpack/                # Chart pack editor components
│   │   └── ChartEditOverlay.tsx  # Inline chart edit overlay within packs
│   │
│   ├── macro/                    # Macro strategy tab system
│   │   ├── index.ts              # Barrel exports
│   │   ├── OverviewTab.tsx       # Summary — regime probabilities, cross-market, robustness
│   │   ├── RegimeTab.tsx         # Growth/inflation regime detail with indicator waterfall
│   │   ├── StrategyTab.tsx       # Backtest results — equity curves, drawdowns, stats
│   │   ├── StrategyFactorsTab.tsx# Factor decomposition & contribution analysis
│   │   ├── RegimeStrategyRegimeTab.tsx # Regime-conditional strategy performance
│   │   ├── CrossMarketTab.tsx    # Cross-asset regime correlation
│   │   ├── RobustnessTab.tsx     # Robustness checks & sensitivity analysis
│   │   ├── MethodologyTab.tsx    # Strategy methodology documentation
│   │   ├── ComponentBacktest.tsx # Single-component backtest chart
│   │   ├── IndicatorWaterfall.tsx# Indicator waterfall visualization
│   │   ├── SharedComponents.tsx  # LoadingSpinner, ErrorBox, RegimeProbBar, etc.
│   │   ├── types.ts              # TypeScript interfaces for macro data
│   │   ├── constants.ts          # Tab definitions, color maps
│   │   └── helpers.ts            # Formatting & calculation helpers
│   │
│   ├── intel/                    # Intelligence & briefing components
│   │   ├── IntelBriefing.tsx     # AI-generated macro briefing with TTS playback
│   │   ├── IntelHeader.tsx       # Intel page header with date/filter controls
│   │   └── IntelTabs.tsx         # Tab navigation for intel views
│   │
│   ├── screener/                 # Stock screener tab system
│   │   ├── index.ts              # Barrel exports
│   │   ├── RankingsTab.tsx       # Asset rankings table
│   │   ├── FlowsTab.tsx          # Fund flow analysis
│   │   ├── MethodologyTab.tsx    # Screener methodology docs
│   │   ├── types.ts              # Screener type definitions
│   │   └── constants.ts          # Screener constants
│   │
│   ├── wartime/                  # Crisis & stress test components
│   │   ├── WartimeContent.tsx    # Wartime intelligence dashboard
│   │   └── StressTestContent.tsx # Portfolio stress test scenarios
│   │
│   └── whiteboard/               # Whiteboard components
│       └── ExcalidrawEditor.tsx  # Excalidraw integration with theme sync
│
├── context/                      # React contexts (app-wide state)
│   ├── AuthContext.tsx            # JWT auth — login, logout, register, reauth, useAuth()
│   └── ThemeContext.tsx           # Dark/light theme — useTheme(), persists to localStorage
│
├── hooks/                        # Custom React hooks
│   ├── useChartEditor.ts         # Chart studio state machine (series, layout, save/load)
│   ├── useCountUp.ts             # Animated number counter
│   ├── useDebounce.ts            # Debounced value for search inputs
│   ├── useFocusTrap.ts           # Accessibility focus trap for modals
│   ├── useIntelState.ts          # Intel page tab/filter state
│   ├── useNativeInputStyle.ts    # Browser-native input styling helper
│   └── useResponsiveSidebar.ts   # Sidebar collapse state with breakpoint detection
│
├── lib/                          # Utilities & configuration
│   ├── api.ts                    # API client — apiFetch(), apiFetchJson(), cookie auth
│   ├── buildChartFigure.ts       # Plotly figure builder from chart expression DSL
│   ├── chartTheme.ts             # Plotly theme — applyChartTheme() for dark/light
│   ├── constants.ts              # App-wide constants (API base URL, etc.)
│   ├── monacoCompletions.ts      # Monaco editor autocomplete for chart DSL
│   └── whiteboardTemplates.ts    # Excalidraw template definitions
│
├── providers/
│   └── QueryProvider.tsx         # TanStack Query client + devtools
│
├── types/
│   └── chart.ts                  # ChartMeta, CustomChartListItem interfaces
│
└── test/
    └── setup.ts                  # Vitest/Jest test setup
```

## Provider nesting (root layout)

```
QueryProvider → AuthProvider → ThemeProvider → TaskProvider → ErrorBoundary → SessionExpiredModal → [pages]
```

## Design system

- Dark-first quant terminal aesthetic (Koyfin/Bloomberg reference)
- CSS variables in `globals.css` — all colors via Tailwind utilities (`bg-background`, `text-foreground`, `border-border`)
- Fonts: Inter (body), Space Mono (code/data)
- Primary: electric blue `rgb(var(--primary))`
- Utility classes: `.panel-card`, `.stat-label`, `.btn-toolbar`, `.btn-icon`, `.tab-link`

## Key patterns

- **Data fetching:** TanStack Query (`useQuery`) + `apiFetchJson()` — no raw fetch calls
- **Charts:** Plotly via `react-plotly.js`, themed with `applyChartTheme()`
- **Auth:** JWT in HttpOnly cookies, `useAuth()` context, `AuthGuard` for protected routes
- **Chart DSL:** Monaco editor with custom expression language, evaluated server-side
- **Background tasks:** `TaskProvider` polls `/api/jobs`, notifications in navbar
