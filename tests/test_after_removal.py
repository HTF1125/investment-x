"""Playwright test: verify app works after Custom Charts removal."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ix.db.conn import conn
conn.connect()
from ix.common.security.auth import create_user_token
from sqlalchemy.orm import Session
from ix.db.models import User

with Session(conn.engine) as s:
    owner = s.query(User).filter(User.role == "owner").first()
    TOKEN = create_user_token(str(owner.email), role="owner")
    print(f"Auth: {owner.email}")

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/after-removal"
os.makedirs(SHOTS, exist_ok=True)
errors = []

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path)
    print(f"  [screenshot] {name}")

def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        errors.append(label)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        ctx.add_cookies([{"name": "access_token", "value": TOKEN, "domain": "localhost", "path": "/"}])
        page = ctx.new_page()
        page.set_default_timeout(15000)

        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        try:
            # ── 1. Dashboard ──
            print("\n=== 1. Dashboard ===")
            page.goto(f"{BASE}/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "01-dashboard")
            check("Dashboard loads", page.locator('text=DASHBOARD').first.is_visible())

            # ── 2. ChartPack page ──
            print("\n=== 2. ChartPack ===")
            page.goto(f"{BASE}/chartpack")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            shot(page, "02-chartpack")
            check("ChartPack page loads", not page.locator('text=Application error').is_visible(timeout=2000))

            # ── 3. Reports page ──
            print("\n=== 3. Reports ===")
            page.goto(f"{BASE}/reports")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "03-reports")
            check("Reports page loads", page.locator('text=Reports').first.is_visible())

            # Open existing report
            report_card = page.locator('[class*="cursor-pointer"][class*="rounded"]').first
            if report_card.is_visible(timeout=3000):
                report_card.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                shot(page, "04-report-editor")
                check("Report editor opens", page.locator('[class*="aspect-[16/9]"]').first.is_visible(timeout=5000))

                # ── 4. Chart picker in reports ──
                print("\n=== 4. Report Chart Picker ===")
                # Find a chart placeholder
                add_chart = page.locator('button:has-text("Click to add chart")').first
                if add_chart.is_visible(timeout=3000):
                    add_chart.click()
                    page.wait_for_timeout(1500)
                    shot(page, "05-chart-picker")
                    check("Chart picker opens", page.locator('text=Insert Chart').first.is_visible())

                    # Should show pack list (not custom charts)
                    check("Shows pack list", page.locator('text=My Packs').first.is_visible(timeout=3000) or
                          page.locator('text=Published').first.is_visible(timeout=1000))

                    # Click a pack
                    pack_btn = page.locator('button:has(.lucide-file-text)').first
                    if pack_btn.is_visible(timeout=3000):
                        pack_btn.click()
                        page.wait_for_timeout(1500)
                        shot(page, "06-pack-charts")
                        check("Pack charts listed", page.locator('button:has(.lucide-line-chart)').count() > 0)

                        # Preview a chart
                        chart_btn = page.locator('button:has(.lucide-line-chart)').first
                        chart_btn.click()
                        page.wait_for_timeout(2000)
                        shot(page, "07-chart-preview")
                        check("Chart preview shown", page.locator('button:has-text("Insert Chart")').first.is_visible())

                    # Close
                    close = page.locator('button[aria-label="Close"]').first
                    if close.is_visible(timeout=1000):
                        close.click()
                        page.wait_for_timeout(300)

                # ── 5. Present mode ──
                print("\n=== 5. Present Mode ===")
                present = page.locator('button:has-text("Present")').first
                if present.is_visible():
                    present.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(3000)
                    shot(page, "08-present")
                    check("Presentation loads", page.locator('[class*="fixed inset-0"]').first.is_visible())

                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(800)
                    shot(page, "09-present-slide2")

                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1500)

            # ── 6. Studio should 404 ──
            print("\n=== 6. Studio removed ===")
            page.goto(f"{BASE}/studio")
            page.wait_for_timeout(2000)
            shot(page, "10-studio-404")
            check("Studio returns 404", page.locator('text=404').is_visible(timeout=3000) or
                  "studio" not in page.url or page.url.endswith("/studio"))

            # ── 7. Navbar has no Charts link ──
            print("\n=== 7. Navbar ===")
            page.goto(f"{BASE}/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            check("No Charts nav link", not page.locator('a[href="/charts"]').first.is_visible(timeout=1000))
            check("ChartPack nav link exists", page.locator('a[href="/chartpack"]').first.is_visible())
            check("Reports nav link exists", page.locator('a[href="/reports"]').first.is_visible())

            # ── 8. Other pages ──
            print("\n=== 8. Other Pages ===")
            for route, label in [("/research", "Research"), ("/macro", "Macro"), ("/screener", "Screener"), ("/whiteboard", "Whiteboard")]:
                page.goto(f"{BASE}{route}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1500)
                no_error = not page.locator('text=Application error').is_visible(timeout=1000)
                check(f"{label} page loads", no_error)
            shot(page, "11-other-pages")

            # ── Summary ──
            print("\n=============================")
            if errors:
                print(f"FAILURES: {len(errors)}")
                for e in errors:
                    print(f"  - {e}")
            else:
                print("ALL TESTS PASSED")
            print("=============================")

            # Console errors
            real_errors = [e for e in console_errors if "favicon" not in e.lower() and "hydration" not in e.lower()]
            if real_errors:
                print(f"\nConsole errors ({len(real_errors)}):")
                for e in real_errors[:10]:
                    print(f"  {e[:120]}")

            print(f"\nScreenshots: {SHOTS}/")

        except Exception as e:
            print(f"\nFATAL ERROR: {e}")
            import traceback; traceback.print_exc()
            shot(page, "error")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
