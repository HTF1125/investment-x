"""
Frontend ↔ Backend integration test.
Verifies that the Next.js frontend can reach the FastAPI backend
through the Next.js proxy, and that key pages/endpoints work.
"""
import json
import sys
import time
import traceback
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
BACKEND = "http://localhost:8000"

results = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    results.append({"name": name, "status": status, "detail": detail})
    icon = "\u2705" if passed else "\u274c"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # ── 1. Backend health check (direct) ──
        print("\n[1/7] Backend health check (direct)")
        try:
            resp = page.request.get(f"{BACKEND}/api/health", timeout=10000)
            body = resp.json()
            ok = resp.status == 200 and body.get("status") == "healthy"
            record("GET /api/health (direct)", ok, f"status={resp.status}, body={body}")
        except Exception as e:
            record("GET /api/health (direct)", False, str(e))

        # ── 2. Backend API docs reachable ──
        print("\n[2/7] Backend OpenAPI docs")
        try:
            resp = page.request.get(f"{BACKEND}/openapi.json", timeout=10000)
            body = resp.json()
            ok = resp.status == 200 and "paths" in body
            n_paths = len(body.get("paths", {}))
            record("GET /openapi.json", ok, f"{n_paths} API paths registered")
        except Exception as e:
            record("GET /openapi.json", False, str(e))

        # ── 3. Frontend loads ──
        print("\n[3/7] Frontend loads")
        try:
            page.goto(FRONTEND, wait_until="networkidle", timeout=30000)
            title = page.title()
            ok = page.locator("body").is_visible()
            record("Frontend index page", ok, f"title='{title}'")
        except Exception as e:
            record("Frontend index page", False, str(e))

        # ── 4. Frontend → Backend proxy (health via proxy) ──
        print("\n[4/7] Frontend → Backend proxy")
        try:
            resp = page.request.get(f"{FRONTEND}/api/health", timeout=10000)
            body = resp.json()
            ok = resp.status == 200 and body.get("status") == "healthy"
            record("GET /api/health (via proxy)", ok, f"status={resp.status}")
        except Exception as e:
            record("GET /api/health (via proxy)", False, str(e))

        # ── 5. Key API endpoints (via proxy) ──
        print("\n[5/7] Key API endpoints via frontend proxy")
        endpoints = [
            ("GET", "/api/timeseries", "Timeseries list"),
            ("GET", "/api/news", "Briefings/news"),
            ("GET", "/api/v1/dashboard/gallery", "Dashboard gallery"),
            ("GET", "/api/screener/rankings", "Screener rankings"),
        ]
        for method, path, label in endpoints:
            try:
                resp = page.request.get(f"{FRONTEND}{path}", timeout=15000)
                # 200 = data, 401 = auth required (still means backend is responding)
                ok = resp.status in (200, 401, 422)
                record(f"{label} ({path})", ok, f"status={resp.status}")
            except Exception as e:
                record(f"{label} ({path})", False, str(e))

        # ── 6. Page navigation ──
        print("\n[6/7] Frontend page navigation")
        pages_to_check = [
            ("/", "Dashboard"),
            ("/macro", "Macro"),
            ("/screener", "Screener"),
            ("/research", "Research"),
            ("/chartpack", "Chartpack"),
        ]
        for path, label in pages_to_check:
            try:
                page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=20000)
                visible = page.locator("body").is_visible()
                # Check no full-page crash
                crash = page.locator("text=Application error").count() > 0
                ok = visible and not crash
                detail = "crashed" if crash else "OK"
                record(f"Page: {label} ({path})", ok, detail)
            except Exception as e:
                record(f"Page: {label} ({path})", False, str(e))

        # ── 7. Console errors summary ──
        print("\n[7/7] Console errors")
        serious = [e for e in console_errors if "chunk" not in e.lower() and "404" not in e]
        if serious:
            record("Console errors", False, f"{len(serious)} error(s): {serious[:3]}")
        else:
            record("Console errors", len(serious) == 0, f"{len(console_errors)} total, {len(serious)} serious")

        # Take a screenshot for reference
        try:
            page.goto(FRONTEND, wait_until="networkidle", timeout=15000)
            page.screenshot(path="/tmp/ix_integration.png", full_page=False)
            print("\n  Screenshot saved to /tmp/ix_integration.png")
        except Exception:
            pass

        browser.close()

    # ── Summary ──
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(results)} total")
    print(f"{'='*60}")

    if failed > 0:
        print("\n  Failed tests:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    \u274c {r['name']}: {r['detail']}")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    print("=" * 60)
    print("  Investment-X Integration Test")
    print("  Frontend: " + FRONTEND)
    print("  Backend:  " + BACKEND)
    print("=" * 60)
    try:
        sys.exit(run_tests())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
