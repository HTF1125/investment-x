"""Playwright test for Lightweight Charts dashboard integration."""
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

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/lc-dashboard"
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
            print("\n=== 1. Dashboard Load ===")
            page.goto(BASE)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            shot(page, "01-dashboard-loaded")

            # Check for canvas elements (LC renders to canvas)
            canvases = page.locator("canvas")
            n_canvas = canvases.count()
            print(f"  Canvas elements: {n_canvas}")

            # Check toolbar elements
            print(f"  Index picker visible: {page.locator('text=S&P 500').first.is_visible()}")
            print(f"  Period pills visible: {page.locator('text=1Y').first.is_visible()}")

            print("\n=== 2. Wait for chart rendering ===")
            page.wait_for_timeout(3000)
            shot(page, "02-chart-rendered")

            print("\n=== 3. Change period ===")
            page.locator('button:has-text("3M")').first.click()
            page.wait_for_timeout(2000)
            shot(page, "03-period-3m")
            print("  Changed to 3M")

            page.locator('button:has-text("5Y")').first.click()
            page.wait_for_timeout(2000)
            shot(page, "04-period-5y")
            print("  Changed to 5Y")

            page.locator('button:has-text("1Y")').first.click()
            page.wait_for_timeout(1000)

            print("\n=== 4. Change index ===")
            page.locator('text=S&P 500').first.click()
            page.wait_for_timeout(500)
            shot(page, "05-picker-open")

            nasdaq = page.locator('button:has-text("Nasdaq")').first
            if nasdaq.is_visible(timeout=3000):
                nasdaq.click()
                page.wait_for_timeout(4000)
                shot(page, "06-nasdaq")
                print("  Switched to Nasdaq")

            # Switch to Gold
            page.locator('text=Nasdaq').first.click()
            page.wait_for_timeout(500)
            gold = page.locator('button:has-text("Gold")').first
            if gold.is_visible(timeout=2000):
                gold.click()
                page.wait_for_timeout(4000)
                shot(page, "07-gold")
                print("  Switched to Gold")

            # Switch to Bitcoin
            page.locator('text=Gold').first.click()
            page.wait_for_timeout(500)
            btc = page.locator('button:has-text("Bitcoin")').first
            if btc.is_visible(timeout=2000):
                btc.click()
                page.wait_for_timeout(4000)
                shot(page, "08-bitcoin")
                print("  Switched to Bitcoin")

            print("\n=== 5. Light theme ===")
            # Toggle theme
            theme_btn = page.locator('button[title*="theme"], button:has(.lucide-sun), button:has(.lucide-moon)').first
            if theme_btn.is_visible(timeout=2000):
                theme_btn.click()
                page.wait_for_timeout(3000)
                shot(page, "09-light-theme")
                print("  Light theme")

                # Toggle back
                theme_btn.click()
                page.wait_for_timeout(2000)

            print("\n=== 6. VOMO score ===")
            vomo = page.locator('text=VOMO').first
            print(f"  VOMO visible: {vomo.is_visible()}")

            print("\n=== 7. Info popover ===")
            info_btn = page.locator('button[title="About indicators"]').first
            if info_btn.is_visible():
                info_btn.click()
                page.wait_for_timeout(500)
                shot(page, "10-info-popover")
                print("  Info popover shown")
                page.keyboard.press("Escape")

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
