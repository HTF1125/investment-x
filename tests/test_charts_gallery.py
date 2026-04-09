"""Playwright E2E test for the Charts gallery page."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ix.db.conn import conn
conn.connect()
from ix.common.security.auth import create_user_token
from sqlalchemy.orm import Session
from ix.db.models import User

with Session(conn.engine) as s:
    admin = s.query(User).filter(User.role == "owner").first()
    TOKEN = create_user_token(str(admin.email), role="owner")
    print(f"Auth: {admin.email}")

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/charts-gallery"
os.makedirs(SHOTS, exist_ok=True)

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path)
    print(f"  [screenshot] {name}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        ctx.add_cookies([{"name": "access_token", "value": TOKEN, "domain": "localhost", "path": "/"}])
        page = ctx.new_page()
        page.set_default_timeout(20000)

        try:
            # ── 1. Navigate to Charts page ──
            print("\n=== 1. Charts Page ===")
            page.goto(f"{BASE}/charts")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "01-charts-loading")

            # Wait for charts to render (Plotly needs time)
            page.wait_for_timeout(5000)
            shot(page, "02-charts-loaded")

            # ── 2. Verify page structure ──
            print("\n=== 2. Page Structure ===")
            title = page.locator('h1:has-text("Charts")').first
            print(f"  Title visible: {title.is_visible()}")

            search = page.locator('input[placeholder="Search charts..."]').first
            print(f"  Search visible: {search.is_visible()}")

            # Count category chips
            chips = page.locator('button:has-text("All (")')
            all_chip = chips.first
            print(f"  'All' chip visible: {all_chip.is_visible()}")
            shot(page, "03-structure-verified")

            # ── 3. Category filtering ──
            print("\n=== 3. Category Filter ===")
            macro_chip = page.locator('button:has-text("Macro Radar")').first
            if macro_chip.is_visible(timeout=3000):
                macro_chip.click()
                page.wait_for_timeout(3000)
                shot(page, "04-macro-radar-filter")
                print("  Filtered by Macro Radar")

                # Reset
                page.locator('button:has-text("All (")').first.click()
                page.wait_for_timeout(1000)

            # ── 4. Search ──
            print("\n=== 4. Search ===")
            search.fill("credit")
            page.wait_for_timeout(2000)
            shot(page, "05-search-credit")
            print("  Searched 'credit'")

            # Count results
            count_label = page.locator('text=/\\d+ of \\d+/')
            if count_label.first.is_visible(timeout=2000):
                print(f"  Count: {count_label.first.text_content()}")

            # Clear search
            search.fill("")
            page.wait_for_timeout(1000)

            # ── 5. Pagination ──
            print("\n=== 5. Pagination ===")
            page2_btn = page.locator('button:has-text("2")').first
            if page2_btn.is_visible(timeout=3000):
                page2_btn.click()
                page.wait_for_timeout(4000)
                shot(page, "06-page-2")
                print("  Navigated to page 2")

                # Check page indicator
                range_label = page.locator('text=/^25/')
                if range_label.first.is_visible(timeout=2000):
                    print(f"  Range: {range_label.first.text_content()}")

                # Go to next page
                next_btn = page.locator('button:has(.lucide-chevron-right)').first
                if next_btn.is_visible():
                    next_btn.click()
                    page.wait_for_timeout(4000)
                    shot(page, "07-page-3")
                    print("  Navigated to page 3")
            else:
                print("  No page 2 button (fewer than 24 charts)")

            # ── 6. Compact view ──
            print("\n=== 6. Compact View ===")
            # Go back to page 1
            page1_btn = page.locator('button:has-text("1")').first
            if page1_btn.is_visible(timeout=2000):
                page1_btn.click()
                page.wait_for_timeout(3000)

            compact_btn = page.locator('button[title="Compact grid"]').first
            if compact_btn.is_visible(timeout=3000):
                compact_btn.click()
                page.wait_for_timeout(3000)
                shot(page, "08-compact-view")
                print("  Switched to compact grid")

                # Back to standard
                standard_btn = page.locator('button[title="Standard grid"]').first
                if standard_btn.is_visible():
                    standard_btn.click()
                    page.wait_for_timeout(1000)

            # ── 7. Page size change ──
            print("\n=== 7. Page Size ===")
            select = page.locator('select').first
            if select.is_visible(timeout=3000):
                select.select_option("48")
                page.wait_for_timeout(5000)
                shot(page, "09-48-per-page")
                print("  Changed to 48 per page")

            # ── 8. Check navbar has Charts link ──
            print("\n=== 8. Navbar ===")
            nav_charts = page.locator('a[href="/charts"]').first
            print(f"  Charts nav link visible: {nav_charts.is_visible()}")
            shot(page, "10-final-state")

            # ── 9. Scroll to see more charts ──
            print("\n=== 9. Scroll test ===")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(3000)
            shot(page, "11-scrolled-mid")

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            shot(page, "12-scrolled-bottom")

            print("\n=== ALL TESTS COMPLETE ===")
            print(f"Screenshots: {SHOTS}/")

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback; traceback.print_exc()
            shot(page, "error")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
