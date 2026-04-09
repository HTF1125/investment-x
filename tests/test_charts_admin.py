"""Playwright test for Charts gallery admin features."""
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
    print(f"Auth: {owner.email} (owner)")

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/charts-admin"
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
            # ── 1. Load charts page ──
            print("\n=== 1. Charts Page ===")
            page.goto(f"{BASE}/charts")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            shot(page, "01-loaded")

            # ── 2. Check admin elements ──
            print("\n=== 2. Admin Elements ===")
            new_btn = page.locator('button:has-text("New Chart")').first
            print(f"  New Chart button: {new_btn.is_visible()}")
            shot(page, "02-new-chart-button")

            # ── 3. Hover over a chart card to see admin overlay ──
            print("\n=== 3. Admin Overlay ===")
            first_card = page.locator('[class*="cursor-pointer"][class*="group"]').first
            if first_card.is_visible(timeout=5000):
                first_card.hover()
                page.wait_for_timeout(500)
                shot(page, "03-hover-overlay")

                # Check for edit, refresh, delete buttons
                edit_btn = page.locator('button[title="Edit in Studio"]').first
                refresh_btn = page.locator('button[title="Refresh chart data"]').first
                delete_btn = page.locator('button[title="Delete chart"]').first
                print(f"  Edit button: {edit_btn.is_visible()}")
                print(f"  Refresh button: {refresh_btn.is_visible()}")
                print(f"  Delete button: {delete_btn.is_visible()}")

                # ── 4. Click edit → should navigate to studio ──
                print("\n=== 4. Edit → Studio ===")
                edit_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                shot(page, "04-studio-page")
                current_url = page.url
                print(f"  URL: {current_url}")
                assert "studio" in current_url, f"Expected studio URL, got {current_url}"
                assert "chartId=" in current_url, f"Expected chartId param, got {current_url}"
                print("  Navigated to Studio with chartId")

                # Go back
                page.go_back()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(4000)

                # ── 5. Click card directly → should also go to studio ──
                print("\n=== 5. Card Click → Studio ===")
                first_card = page.locator('[class*="cursor-pointer"][class*="group"]').first
                first_card.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                shot(page, "05-card-click-studio")
                print(f"  URL: {page.url}")
                assert "studio" in page.url
                print("  Card click navigates to Studio")

                # Go back
                page.go_back()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(4000)

                # ── 6. Test refresh button ──
                print("\n=== 6. Refresh Button ===")
                first_card = page.locator('[class*="cursor-pointer"][class*="group"]').first
                first_card.hover()
                page.wait_for_timeout(500)
                refresh_btn = page.locator('button[title="Refresh chart data"]').first
                if refresh_btn.is_visible(timeout=2000):
                    refresh_btn.click()
                    page.wait_for_timeout(3000)
                    shot(page, "06-after-refresh")
                    # Check for success flash
                    flash = page.locator('text=Chart refreshed')
                    print(f"  Refresh flash: {flash.is_visible(timeout=3000)}")

                # ── 7. Test delete confirmation ──
                print("\n=== 7. Delete Confirmation ===")
                first_card = page.locator('[class*="cursor-pointer"][class*="group"]').first
                first_card.hover()
                page.wait_for_timeout(500)
                delete_btn = page.locator('button[title="Delete chart"]').first
                if delete_btn.is_visible(timeout=2000):
                    delete_btn.click()
                    page.wait_for_timeout(500)
                    shot(page, "07-delete-dialog")

                    # Should show confirmation
                    dialog = page.locator('text=Delete chart')
                    print(f"  Delete dialog: {dialog.is_visible()}")
                    cancel_btn = page.locator('button:has-text("Cancel")').first
                    print(f"  Cancel button: {cancel_btn.is_visible()}")

                    # Cancel — don't actually delete
                    cancel_btn.click()
                    page.wait_for_timeout(500)
                    shot(page, "08-after-cancel")
                    print("  Cancelled delete")

                # ── 8. New Chart button → Studio ──
                print("\n=== 8. New Chart ===")
                new_btn = page.locator('button:has-text("New Chart")').first
                if new_btn.is_visible():
                    new_btn.click()
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                    shot(page, "09-new-chart-studio")
                    print(f"  URL: {page.url}")
                    assert "new=true" in page.url
                    print("  New Chart opens Studio in new mode")

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
