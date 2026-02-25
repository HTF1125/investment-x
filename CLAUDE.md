# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment-X is a full-stack macro research and quantitative intelligence platform. The backend is a Python/FastAPI service; the frontend is a Next.js 14 app. They are developed and run independently in local dev.

---

## Running the Servers

### Backend (FastAPI)
```bash
python -m uvicorn ix.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Entry point: `ix/api/main.py`. Runs on port **8000**.

### Frontend (Next.js)
```bash
cd ui
npm run dev       # dev server (port 3000, or next available)
npm run build     # production build
npm run lint      # ESLint
```
Entry point: `ui/src/app/layout.tsx`. In dev, all `/api/*` requests are proxied to `http://127.0.0.1:8000`.

### Docker (full stack)
```bash
docker-compose up --build
```

---

## Architecture

### Backend (`ix/`)

| Directory | Purpose |
|-----------|---------|
| `ix/api/main.py` | FastAPI app, middleware, lifespan, router registration |
| `ix/api/routers/` | One file per domain: `auth`, `admin`, `timeseries`, `series`, `custom`, `dashboard`, `notes`, `insights`, `technical`, `risk`, `news`, `evaluation`, `task` |
| `ix/api/dependencies.py` | FastAPI `Depends()` — `get_current_user()`, `get_current_admin_user()`, `get_db()` |
| `ix/db/conn.py` | SQLAlchemy engine + scoped session (pool: 40 base / 80 overflow) |
| `ix/db/models/` | ORM models: `User`, `Timeseries`, `TimeseriesData`, `CustomChart`, `InvestmentNote`, `InvestmentNoteImage`, `FinancialNews`, `TaskProcess`, `TelegramMessage` |
| `ix/db/query.py` | Data-fetching helpers with TTLCache (default 300s TTL, 48 series) |
| `ix/cht/` | Chart-building business logic (Plotly figures) |
| `ix/core/` | Analytics: backtesting, performance, signals, technical indicators, ML prediction |
| `ix/misc/` | Utilities: settings, email, Telegram, OpenAI/Gemini, task runners |

**Auth:** JWT tokens + HttpOnly cookies. Role hierarchy: `owner > admin > general`. Runtime DB migrations run idempotently at startup (user roles, custom chart ownership, investment notes schema).

**Middleware stack (order matters):** GZip (≥1KB) → CORS → session cleanup.

### Frontend (`ui/src/`)

| Directory | Purpose |
|-----------|---------|
| `app/` | Next.js App Router pages: `/` (dashboard), `/notes`, `/technical`, `/studio`, `/research`, `/intel`, `/slides`, `/admin`, `/login`, `/register` |
| `components/` | Shared React components |
| `context/AuthContext.tsx` | Auth state — `useAuth()` hook, JWT stored in `localStorage` + HttpOnly cookie |
| `context/ThemeContext.tsx` | Light/dark theme — `useTheme()` hook |
| `lib/api.ts` | `apiFetch()` / `apiFetchJson<T>()` — auto-injects `Authorization` header from localStorage, always sends `credentials: 'include'` |
| `lib/chartTheme.ts` | `applyChartTheme(fig, theme, opts)` — applies dark/light Plotly theme |

**Data fetching:** TanStack Query (`@tanstack/react-query`) for all server state. The dashboard home page (`app/page.tsx`) does SSR pre-fetch with a 3-second timeout; the client hydrates from `initialData`.

**Key components:**
- `DashboardContainer` — Dashboard orchestration, studio slide-over via URL params (`?chartId=` / `?new=true`)
- `DashboardGallery` — Chart grid with navigator, category filters, auto-refresh
- `CustomChartEditor` — Monaco editor + Plotly preview; Python code executed server-side via `/api/custom/preview`
- `NotesRichEditor` — Tiptap-based rich text with image upload

### API Proxy
`next.config.mjs` rewrites `/api/*` → `http://127.0.0.1:8000/api/*` in dev/SSR mode. In static-export builds (`NEXT_BUILD_MODE=export`), rewrites are disabled and the backend serves the SPA directly.

---

## Environment Variables

Backend reads from `.env` at project root (via `python-dotenv`):
- `DB_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing secret
- `ACCESS_TOKEN_EXPIRE_MINUTES` — Token TTL (default 600)
- `GEMINI_API_KEY`, `MINIMAX_API_KEY` — AI providers
- `R2_*` — Cloudflare R2 object storage
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` — Telegram integration

Frontend env (in `ui/`):
- `INTERNAL_API_URL` — Backend URL used during SSR (server-side only)
- `NEXT_PUBLIC_API_URL` — Backend URL exposed to the browser
- Both fall back to `http://127.0.0.1:8000`

---

## Key Conventions

- **Role checks** in both backend (`dependencies.py` guards) and frontend (`isOwner`, `isAdminRole`, `isGeneralRole` derived from `user.role`).
- **Custom charts** are user-owned; only the creator or `owner`-role can edit. `isOwner` bypasses all ownership checks.
- **Plotly figures** are stored as JSON in the DB alongside chart code. The `/api/custom/preview` endpoint executes Python code server-side and returns a figure JSON.
- **Chart theming** is always applied client-side via `applyChartTheme()` before rendering, never stored themed.
- **No test suite** exists in this repo. Manual testing via browser / API client.
