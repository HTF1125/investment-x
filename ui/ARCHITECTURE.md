# ui/ Architecture Guide

> **For AI agents and developers:** This is the definitive guide for where code belongs in the `ui/` Next.js frontend.
> When adding new functionality, consult this file before creating or modifying files.

---

## Quick Reference

| Folder | Purpose | Put here if... |
|--------|---------|----------------|
| `app/` | Pages & routing (Next.js App Router) | You're adding a new page or route |
| `app/{route}/_components/` | Route-private components | You're building a complex component used only by one route |
| `components/layout/` | Shell, Navbar, Footer, NavigatorShell | You're modifying the app frame or navigation |
| `components/shared/` | Cross-page reusable components (Chart, Modal, ErrorBoundary) | You're building something used by 2+ pages |
| `components/ui/` | Primitive UI components (button) | You're adding a low-level design-system primitive |
| `components/{domain}/` | Domain-specific components (macro, screener, admin, etc.) | You're building components for a specific feature area |
| `context/` | React Context providers (Auth, Theme) | You're adding app-wide state that many components consume |
| `hooks/` | Custom React hooks | You're extracting reusable stateful logic |
| `lib/` | Pure utilities, API client, chart helpers, constants | You're writing a stateless helper function or configuration |
| `providers/` | React provider wrappers (QueryProvider) | You're wrapping the app in a new provider |
| `types/` | Shared TypeScript type definitions | You're defining types used across multiple files |
| `test/` | Test setup and configuration | You're adding test infrastructure |

---

## Detailed Module Guide

### `app/` — Pages & Routing

Next.js 14 App Router with file-based routing. Every route folder has a `page.tsx` as its entry point.

**Route map:**

| Route | Page | Purpose | Auth |
|-------|------|---------|------|
| `/` | `page.tsx` | Dashboard — chart grid, briefing panel, regime beacon | No |
| `/login` | `login/page.tsx` | Login form | No |
| `/register` | `register/page.tsx` | Registration form | No |
| `/chartpack` | `chartpack/page.tsx` | Chart pack browser — view/manage chart packs | No |
| `/charts/packs` | `charts/packs/page.tsx` | Interactive chart builder — multi-pane, multi-series | No |
| `/reports` | `reports/page.tsx` | Report editor — slide-based presentations with charts | Login |
| `/present` | `present/page.tsx` | Fullscreen presentation viewer | Login |
| `/research` | `research/page.tsx` | Research library — PDFs, uploads, search | Login |
| `/macro` | `macro/page.tsx` | Macro regime strategy — overview, factors, regime tabs | No |
| `/strategies` | `strategies/page.tsx` | Strategy backtest results — equity curves, metrics | No |
| `/screener` | `screener/page.tsx` | VOMO stock screener — rankings, flows, methodology | No |
| `/quant` | `quant/page.tsx` | Quant analytics — correlation, regression, PCA, VaR | No |
| `/technical` | `technical/page.tsx` | Technical analysis — OHLCV charts, indicators | No |
| `/whiteboard` | `whiteboard/page.tsx` | Excalidraw whiteboard with templates | Login |
| `/wartime` | `wartime/page.tsx` | Stress testing — historical crash scenario analysis | No |
| `/datatool` | `datatool/page.tsx` | Redirects to `/admin` | Admin |
| `/admin` | `admin/page.tsx` | Admin panel — timeseries, users, logs, data tools, watchlist, system | Admin |
| `/admin/timeseries` | `admin/timeseries/page.tsx` | Timeseries manager (sub-route) | Admin |

**Patterns:**
- Pages are `'use client'` — heavy logic delegated to hooks, lib, or domain components
- Most pages wrap content in `<AppShell>` for consistent nav/footer
- Pages with sidebars use `<NavigatorShell>` inside `<AppShell>`
- Data fetching uses TanStack React Query (`useQuery`, `useMutation`) with `apiFetchJson`
- Route-private components live in `_components/` subdirectories (e.g., `charts/_components/`)
- Admin pages are wrapped with `<AuthGuard>` which redirects unauthenticated users to `/login`
- Dynamic imports (`next/dynamic`) used for heavy client-only libraries (Plotly, Excalidraw)

**Shared route files:**
- `layout.tsx` — Root layout: font loading (Inter, Space Mono), provider tree (QueryProvider > AuthProvider > ThemeProvider > ErrorBoundary)
- `error.tsx` — Global error boundary page
- `global-error.tsx` — Root error boundary
- `not-found.tsx` — 404 page

---

### `components/` — React Components

Organized by domain. Each folder groups components for a specific feature area.

#### `components/layout/` — App Frame

| Component | Purpose |
|-----------|---------|
| `AppShell` | Wraps Navbar + Footer + `pt-[40px]`, manages Ctrl+K search palette state |
| `Navbar` | Fixed 40px top bar, nav links, theme toggle, auth controls, mobile menu |
| `Footer` | Site footer |
| `NavigatorShell` | Reusable sidebar + top bar + main content layout for explorer-style pages |
| `PageSkeleton` | Loading skeleton placeholder for pages |

#### `components/shared/` — Cross-Page Reusables

| Component | Purpose |
|-----------|---------|
| `Chart` | Plotly wrapper with theme-aware rendering, loading skeleton, error states |
| `ChartErrorBoundary` | Error boundary specific to chart rendering failures |
| `ErrorBoundary` | Generic React error boundary |
| `GlobalSearchPalette` | Ctrl+K navigation palette with keyboard navigation |
| `Modal` | Generic modal dialog with focus trap |

#### `components/auth/` — Authentication

| Component | Purpose |
|-----------|---------|
| `AuthGuard` | Wraps admin pages, redirects to `/login` if unauthenticated |
| `SessionExpiredModal` | Re-authentication modal when JWT expires mid-session |
| `SignInPrompt` | Inline prompt for pages that require login |

#### `components/admin/` — Admin Panel

`TimeseriesManager`, `UserManager`, `AdminLogViewer`, `DataToolsTab`, `CreditWatchlistTab`, `ProjectStructure`

#### `components/macro/` — Macro Regime Strategy

Tabbed interface: `OverviewTab`, `StrategyTab`, `StrategyFactorsTab`, `RegimeTab`, `RegimeStrategyRegimeTab`, `MethodologyTab`, `CrossMarketTab`, `RobustnessTab`, `ComponentBacktest`, `IndicatorWaterfall`. Shared types/constants/helpers via `types.ts`, `constants.ts`, `helpers.ts`, `SharedComponents.tsx`.

#### `components/screener/` — Stock Screener

`RankingsTab`, `FlowsTab`, `MethodologyTab`, `ConsensusView`, `SectorBreakdown`, `StockDetailPanel`, `SummaryStats`, `Sparkline`. Types/constants via barrel exports (`index.ts`).

#### `components/chartpack/` — Chart Packs

`PackListView`, `PackDetailView`, `PackChart`, `PackChartGrid`, `ChartEditOverlay`, `ChartMenu`, `ReportEditor`, `ReportModal`, `ConfirmDialog`.

#### `components/reports/` — Report Builder

`ReportListView`, `ReportEditorView`, `SlideRenderer`, `PresentationSlideRenderer`, `TiptapEditor`, `ChartPicker`, `LayoutPicker`. Template/type definitions in `templates.ts`, `slideTypes.ts`, `sampleSlides.ts`.

#### `components/dashboard/` — Dashboard

`ChartGrid`, `RegimeBeacon`, `VomoSparkline`, `Technicals`. Sub-folder `chart/` contains `LightweightChart` (TradingView Lightweight Charts), `useTechnicalsChart`, `indicators`, `theme`.

#### `components/chart-editor/` — Chart Format Panel

`FormatPanel` — series formatting controls for the chart builder.

#### `components/intel/` — Intelligence

`Briefing` — macro briefing panel.

#### `components/wartime/` — Stress Testing

`WartimeContent`, `StressTestContent` — historical crash analysis UI.

#### `components/whiteboard/` — Whiteboard

`ExcalidrawEditor` — Excalidraw integration wrapper.

#### `components/ui/` — Primitives

`button` — base button component. Low-level design system primitives go here.

---

### `context/` — Global State

#### `AuthContext.tsx` — Authentication

**Provider:** `AuthProvider` — wraps the entire app.

**State:** `user`, `token`, `loading`, `isSessionExpired`, `viewAsUser` (admin impersonation).

**Key features:**
- HttpOnly cookie auth (no token in localStorage)
- Silent token refresh every 30 minutes
- Auto-refresh on init if token expired (<7 days)
- Session-expired event listener (`ix:session-expired`) dispatched by `apiFetch`
- `reauth()` for re-login without losing page state
- `viewAsUser` toggle for admin to preview general-user experience

**Hook:** `useAuth()` — returns `{ user, login, logout, register, isAuthenticated, token, viewAsUser, toggleViewAsUser, isSessionExpired, dismissSessionExpired, reauth }`.

#### `ThemeContext.tsx` — Theme

**Provider:** `ThemeProvider` — manages `light`/`dark` toggle.

**Mechanism:** Adds `light` or `dark` class to `<html>`, sets `colorScheme` CSS property. Reads from `localStorage('theme')`, falls back to `prefers-color-scheme`. Hides content until mounted to prevent flash.

**Hook:** `useTheme()` — returns `{ theme, toggleTheme }`.

---

### `hooks/` — Custom React Hooks

| Hook | Purpose |
|------|---------|
| `useDebounce(value, delay)` | Debounce a value by `delay` ms — used for search inputs |
| `useCountUp(target, duration)` | Animated number counter with easeOutCubic — used for dashboard stats |
| `useFocusTrap(isActive, onEscape)` | Trap Tab/Shift+Tab focus inside a container, restore on deactivation — used by modals |
| `useNativeInputStyle()` | Returns inline style for native form elements (`colorScheme`, `backgroundColor`, `color`) that need explicit theme values |
| `useResponsiveSidebar(initialOpen)` | Sidebar state with auto-collapse below 1024px, respects manual toggle |

**Put here:** Reusable stateful logic shared across 2+ components. One hook per file, named `use{Name}.ts`.

---

### `lib/` — Utilities

| File | Purpose |
|------|---------|
| `api.ts` | `apiFetch()` and `apiFetchJson<T>()` — shared fetch wrappers with HttpOnly cookie auth, timeout, abort, and session-expired event dispatch. `ApiError` class for typed error handling. `getDirectApiBase()` for bypassing Next.js proxy on long requests. |
| `buildChartFigure.ts` | Plotly figure builder — multi-pane, multi-axis (Y1/Y2/Y3), transforms, annotations, date ranges. Used by chart builder and pack chart viewer. |
| `chartTheme.ts` | `applyChartTheme(fig, theme, opts)` — applies consistent Plotly styling (colors, fonts, grid, background) based on current light/dark theme. Exports `COLORWAY` palette. |
| `constants.ts` | `RANGE_MAP` / `RANGE_PRESETS` (date range presets), `DEFAULT_CHART_CODE` (editor boilerplate), `queryKeys` (TanStack Query key factories) |
| `monacoCompletions.ts` | Monaco Editor IntelliSense for the chart expression DSL — completions for `Series()`, transforms, Plotly, pandas, quant functions |
| `whiteboardTemplates.ts` | Pre-built Excalidraw scene templates for the whiteboard page |
| `utils.ts` | `cn()` — Tailwind class merge utility (`clsx` + `twMerge`) |

**Put here:** Stateless helper functions, configuration, constants, type utilities. No React state or effects.

---

### `providers/` — React Providers

| Provider | Purpose |
|----------|---------|
| `QueryProvider` | TanStack React Query — `staleTime: 5min`, `refetchOnWindowFocus: false`, `retry: 1` |

**Provider tree** (defined in `app/layout.tsx`):
```
QueryProvider > AuthProvider > ThemeProvider > ErrorBoundary > {children} + SessionExpiredModal
```

---

### `types/` — Shared Type Definitions

| File | Purpose |
|------|---------|
| `chart.ts` | `ChartMeta`, `CustomChartListItem` — chart metadata types from the API |

**Put here:** TypeScript interfaces/types used by 3+ files. Domain-specific types that are only used within one component folder should stay in that folder's `types.ts`.

---

### `declarations.d.ts` — Module Declarations

Type declarations for untyped npm packages (`plotly.js-dist-min`, `react-plotly.js`).

---

## Decision Tree: "Where does my code go?"

```
Is it a new page / route?
  -> app/{route}/page.tsx
  (wrap in AppShell, keep logic in hooks/lib/components)

Is it a component used only by one route?
  -> app/{route}/_components/
  (prefixed with _ to signal route-private)

Is it a component used across multiple pages?
  -> components/shared/

Is it a component for a specific domain (macro, screener, admin)?
  -> components/{domain}/

Is it part of the app frame (nav, footer, sidebar layout)?
  -> components/layout/

Is it a low-level UI primitive (button, input, badge)?
  -> components/ui/

Is it app-wide state consumed by many components?
  -> context/{Name}Context.tsx
  (export Provider + useHook)

Is it reusable stateful logic (useState/useEffect pattern)?
  -> hooks/use{Name}.ts

Is it a stateless helper, constant, or configuration?
  -> lib/

Is it a type definition used across 3+ files?
  -> types/

Is it a React provider wrapping the app?
  -> providers/
```

---

## Design System Reference

### Fonts
- **Body:** Inter (`font-sans`, `--font-body`) — weights 400, 500, 600, 700
- **Code/Labels:** Space Mono (`font-mono`, `--font-mono`) — weights 400, 700

### Colors (CSS Variables via Tailwind)
All colors defined as space-separated RGB triplets in `globals.css`, consumed via Tailwind utilities.

| Token | Usage | Tailwind |
|-------|-------|----------|
| `--background` | Page background | `bg-background` |
| `--foreground` | Primary text | `text-foreground` |
| `--card` | Card/panel surface | `bg-card` |
| `--surface` | Elevated surface | `bg-surface` |
| `--primary` | Electric blue accent | `text-primary`, `bg-primary` |
| `--muted-foreground` | Secondary text | `text-muted-foreground` |
| `--border` | Borders & dividers | `border-border` |
| `--destructive` | Error/delete actions | `text-destructive` |
| `--success` | Success states | `text-success` |
| `--warning` | Caution/favorites | `text-warning` |

**Border opacity conventions:** `/30` for cards, `/50` for inputs, `/20` for subtle dividers.

### Theme
- Dark-first quant terminal aesthetic (Koyfin/Bloomberg/FactSet reference)
- `darkMode: 'class'` in Tailwind config — toggled by adding `light`/`dark` class to `<html>`
- Always use CSS vars via Tailwind (`text-foreground`, `bg-background`). **Never hardcode colors.**
- Native form elements need explicit `colorScheme` — use `useNativeInputStyle()` hook

### Utility Classes (globals.css)

| Class | Description |
|-------|-------------|
| `.panel-card` | `rounded-[var(--radius)] border border-border/50 bg-card shadow-sm` |
| `.stat-label` | `text-[11.5px] font-mono uppercase tracking-[0.10em] text-muted-foreground` |
| `.page-title` | `text-lg font-semibold text-foreground tracking-[-0.02em]` |
| `.tab-link` | Tab with underline indicator, `active` class or `aria-selected` for active state |
| `.btn-toolbar` | Compact action button `h-8 px-3` with border and hover states |
| `.btn-icon` | Square icon button `w-8 h-8` with hover highlight |
| `.glass-card` | Flat elevated card `bg-card border border-border/0.5` (no blur) |
| `.no-scrollbar` | Hide scrollbar (webkit + Firefox) |

### Typography Scale
- Nav links: `text-[12.5px] font-semibold uppercase tracking-[0.05em]`
- Stat labels: `text-[11.5px] font-mono uppercase tracking-[0.10em]`
- Page titles: `text-lg font-semibold tracking-[-0.02em]`
- Body text: default `text-sm` or `text-base`

---

## Key Architectural Rules

1. **Pages are thin.** Route `page.tsx` files handle layout and state coordination. Heavy rendering logic lives in domain components. Data fetching logic uses TanStack Query with `apiFetchJson`. Business logic lives in `lib/`.

2. **All API calls go through `apiFetchJson()`** (or `apiFetch()` for non-JSON responses). Never use raw `fetch()` for API calls — the wrapper handles credentials, timeout, abort, and session-expired events. Exception: `AuthContext` uses raw `fetch()` for login/refresh flows.

3. **Auth via `useAuth()` hook from `AuthContext`.** Check `isAuthenticated` or `user` for conditional rendering. Wrap admin pages with `<AuthGuard>`. The token is an opaque `'cookie'` marker — actual auth uses HttpOnly cookies.

4. **Theme via `useTheme()` — always use CSS vars, never hardcode colors.** Use Tailwind utilities (`text-foreground`, `bg-background`, `border-border`) everywhere. For Plotly charts, call `applyChartTheme(fig, theme)` to match the current theme.

5. **Charts use `applyChartTheme()` for consistent styling.** Import from `lib/chartTheme`. Call after building the figure. For the chart builder, use `buildChartFigure()` from `lib/buildChartFigure` which handles multi-pane layout.

6. **Components use Tailwind utility classes.** No CSS modules, no styled-components. Custom utility classes defined in `globals.css` (`.panel-card`, `.btn-toolbar`, etc.). Use `cn()` from `lib/utils` for conditional class merging.

7. **Dynamic imports for heavy libraries.** Plotly, Excalidraw, Monaco, and other large client-only packages use `next/dynamic` with `{ ssr: false }` to keep the initial bundle small.

8. **API proxy via Next.js rewrites.** All `/api/*` requests are proxied to the FastAPI backend via `next.config.mjs` rewrites. Use `getDirectApiBase()` only for long-running requests that would exceed proxy timeout (PDF exports, etc.).

9. **Query keys are centralized.** Use `queryKeys` from `lib/constants` for TanStack Query cache keys to avoid key collisions and enable targeted invalidation.

10. **No decorative excess.** No gradient card backgrounds, no backdrop-blur on cards, no glow animations, no `shadow-xl` or `shadow-2xl`. Maximum `shadow-md` for cards, `shadow-lg` for modals/dropdowns. Data over decoration.
