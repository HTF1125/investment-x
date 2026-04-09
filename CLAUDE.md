# Investment-X

Quantitative macro research platform — regime-based asset allocation across global equity indices.

## Stack
FastAPI backend (`ix/`), Next.js 14 frontend (`ui/`), PostgreSQL, SQLAlchemy, TanStack Query, Tailwind CSS, Plotly.

## Hard Rules
1. `eval()` in chart/series DSL is intentional — always behind `Depends(get_current_user)`
2. Walk-forward or expanding-window backtests only — never full-sample optimization
3. Do NOT invert VIX/FCI/put-call — they are contrarian (high fear = bullish)
4. Do NOT include Global M2 — zero IC, pure noise
5. IC-weight indicators by empirical predictive power — never equal-weight
6. Never hard-delete user data — always soft-delete
7. Blocking DB routes must be `def` not `async def`; pure I/O-free routes can be `async def`

## Design System (Quant Terminal)
- **Navbar:** `h-[56px]`, content offset `pt-[56px]`
- **CTAs:** `bg-foreground text-background` (monochrome hierarchy)
- **Shadows:** `shadow-sm` cards, `shadow-2xl` modals, `shadow-lg` dropdowns
- **Border opacity:** `/50` cards+inputs, `/40` toolbars, `/30` section headers, `/20` faint
- **CSS vars via Tailwind:** `text-foreground`, `bg-background`, `border-border` — no hardcoded hex
- **`.tab-link` active:** `bg-primary` underline. **Navbar active:** `bg-foreground` underline (separate systems)
- No gradient backgrounds, no glow animations, no backdrop-blur on cards

## Key Entry Points
| Component | File |
|-----------|------|
| Backend app | `ix/api/main.py` |
| Frontend layout | `ui/src/app/layout.tsx` |
| CSS variables | `ui/src/app/globals.css` |
| Navbar / AppShell | `ui/src/components/layout/` |
| API client | `ui/src/lib/api.ts` |
| Auth context | `ui/src/context/AuthContext.tsx` |
| Chart theme | `ui/src/lib/chartTheme.ts` |
| Indicators | `ix/core/indicators/` (18 modules, 400+ functions) |
| Macro engine | `ix/core/macro/` |
| DB connection | `ix/db/conn.py` — `get_db()` for routers, `Session()` elsewhere |

## Shared Context
Detailed domain knowledge for skills: `.claude/context/` — research-philosophy, indicator-registry, data-sources, platform-architecture, analysis-preferences.

## Dev Servers
Frontend: `localhost:3000` | Backend: `localhost:8000`
