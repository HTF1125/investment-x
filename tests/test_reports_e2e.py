"""Playwright E2E test for the redesigned Report system."""
import os, sys

# Generate auth token before launching browser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ix.db.conn import conn
conn.connect()
from ix.common.security.auth import create_user_token
from sqlalchemy.orm import Session
from ix.db.models import User

with Session(conn.engine) as s:
    admin = s.query(User).filter(User.role == "admin").first()
    TOKEN = create_user_token(str(admin.email), role="admin")
    print(f"Auth token generated for {admin.email}")

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/report-tests"
os.makedirs(SHOTS, exist_ok=True)

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path)
    print(f"  [screenshot] {name}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="dark",
        )
        # Inject auth cookie
        ctx.add_cookies([{
            "name": "access_token",
            "value": TOKEN,
            "domain": "localhost",
            "path": "/",
        }])
        page = ctx.new_page()
        page.set_default_timeout(15000)

        try:
            # ── Step 1: Reports page (should be authenticated) ──
            print("\n=== Step 1: Reports Page ===")
            page.goto(f"{BASE}/reports")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "01-reports-list")

            # ── Step 2: Template Picker ──
            print("\n=== Step 2: Template Picker ===")
            new_btn = page.locator('button:has-text("New Report")').first
            if new_btn.is_visible(timeout=5000):
                new_btn.click()
                page.wait_for_timeout(1000)
                shot(page, "02-template-picker")
                print("  Template picker opened")

                # Pick Macro Outlook
                macro_btn = page.locator('button:has-text("Macro Outlook")').first
                if macro_btn.is_visible(timeout=3000):
                    macro_btn.click()
                    print("  Selected Macro Outlook")
                else:
                    page.locator('button:has-text("Blank")').first.click()
                    print("  Selected Blank (fallback)")

                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                shot(page, "03-report-editor")
            else:
                print("  ERROR: New Report button not found")
                shot(page, "02-error-no-button")
                return

            # ── Step 3: Editor — verify canvas ──
            print("\n=== Step 3: Editor Canvas ===")
            canvas = page.locator('[class*="aspect-[16/9]"]').first
            if not canvas.is_visible(timeout=5000):
                print("  ERROR: Editor canvas not visible")
                shot(page, "03-error-no-canvas")
                return
            print("  Editor canvas visible")

            # Edit the title slide
            title_input = page.locator('input[placeholder*="Title"], input[placeholder*="title"]').first
            if title_input.is_visible(timeout=3000):
                title_input.fill("Q2 2026 Macro Outlook")
                print("  Title filled")
            shot(page, "04-title-filled")

            # ── Step 4: Navigate slide thumbnails ──
            print("\n=== Step 4: Slide Navigation ===")
            thumbnails = page.locator('.space-y-1\\.5 > div[class*="rounded"]')
            count = thumbnails.count()
            if count == 0:
                # Try alternate selector
                thumbnails = page.locator('[class*="cursor-pointer"][class*="border"][class*="rounded"]')
                count = thumbnails.count()
            print(f"  Found {count} slide thumbnails")

            # Visit each slide type
            for idx in range(min(count, 6)):
                thumbnails.nth(idx).click()
                page.wait_for_timeout(600)
                shot(page, f"05-slide-{idx+1}")
                print(f"  Slide {idx+1} rendered")

            # ── Step 5: Layout Picker ──
            print("\n=== Step 5: Layout Picker ===")
            new_slide_btn = page.locator('button:has-text("New Slide")').first
            if new_slide_btn.is_visible(timeout=3000):
                new_slide_btn.click()
                page.wait_for_timeout(1000)
                shot(page, "06-layout-picker")
                print("  Layout picker opened")

                # Check for layout groups
                for group in ["Structure", "Charts", "Content"]:
                    vis = page.locator(f'text="{group}"').first.is_visible(timeout=1000)
                    print(f"  Group '{group}': {'visible' if vis else 'not found'}")

                # Pick a layout (e.g. "Comparison")
                comp_btn = page.locator('button:has-text("Comparison")').first
                if comp_btn.is_visible(timeout=2000):
                    comp_btn.click()
                    page.wait_for_timeout(500)
                    shot(page, "07-comparison-slide")
                    print("  Comparison slide added")
                else:
                    # Fallback: close
                    page.keyboard.press("Escape")

            # ── Step 6: Chart Picker ──
            print("\n=== Step 6: Chart Picker ===")
            # Go to a chart slide
            thumbnails = page.locator('.space-y-1\\.5 > div[class*="rounded"]')
            count = thumbnails.count()
            if count == 0:
                thumbnails = page.locator('[class*="cursor-pointer"][class*="border"][class*="rounded"]')
                count = thumbnails.count()

            # Find a slide with "Click to add chart"
            found_chart_placeholder = False
            for idx in range(min(count, 10)):
                thumbnails.nth(idx).click()
                page.wait_for_timeout(400)
                placeholder = page.locator('button:has-text("Click to add chart")').first
                if placeholder.is_visible(timeout=500):
                    found_chart_placeholder = True
                    placeholder.click()
                    page.wait_for_timeout(2000)
                    shot(page, "08-chart-picker")
                    print("  Chart picker opened")

                    # Check search
                    search = page.locator('input[placeholder*="Search"]').first
                    print(f"  Search visible: {search.is_visible()}")

                    # Count charts
                    chart_items = page.locator('button:has(.lucide-line-chart)')
                    n = chart_items.count()
                    print(f"  Charts available: {n}")

                    if n > 0:
                        chart_items.first.click()
                        page.wait_for_timeout(2500)
                        shot(page, "09-chart-preview")
                        print("  Chart preview shown")

                        insert_btn = page.locator('button:has-text("Insert Chart")').first
                        if insert_btn.is_visible(timeout=3000):
                            insert_btn.click()
                            page.wait_for_timeout(2000)
                            shot(page, "10-chart-inserted")
                            print("  Chart inserted!")
                    else:
                        # Close
                        close = page.locator('button[aria-label="Close"]').first
                        if close.is_visible(timeout=1000):
                            close.click()
                    break

            if not found_chart_placeholder:
                print("  No chart placeholder found on any slide")

            # ── Step 7: Properties Panel ──
            print("\n=== Step 7: Properties Panel ===")
            props_btn = page.locator('button[title*="properties"]').first
            if props_btn.is_visible(timeout=2000):
                props_btn.click()
                page.wait_for_timeout(500)
                shot(page, "11-properties-panel")
                print("  Properties panel opened")

                notes = page.locator('textarea[placeholder*="Notes"]').first
                if notes.is_visible(timeout=2000):
                    notes.fill("Test speaker note for this slide")
                    print("  Speaker notes filled")
                    shot(page, "12-speaker-notes")

            # ── Step 8: Duplicate slide ──
            print("\n=== Step 8: Duplicate Slide ===")
            dup_btn = page.locator('button[title*="Duplicate"]').first
            if dup_btn.is_visible(timeout=2000):
                dup_btn.click()
                page.wait_for_timeout(500)
                shot(page, "13-after-duplicate")
                # Re-count
                thumbnails2 = page.locator('.space-y-1\\.5 > div[class*="rounded"]')
                c2 = thumbnails2.count()
                if c2 == 0:
                    thumbnails2 = page.locator('[class*="cursor-pointer"][class*="border"][class*="rounded"]')
                    c2 = thumbnails2.count()
                print(f"  Slides after duplicate: {c2}")

            # ── Step 9: Export Buttons ──
            print("\n=== Step 9: Export Buttons ===")
            pptx = page.locator('button:has-text("PPTX")').first
            pdf = page.locator('button:has-text("PDF")').first
            present = page.locator('button:has-text("Present")').first
            print(f"  PPTX visible: {pptx.is_visible()}")
            print(f"  PDF visible: {pdf.is_visible()}")
            print(f"  Present visible: {present.is_visible()}")
            shot(page, "14-toolbar")

            # ── Step 10: Present Mode ──
            print("\n=== Step 10: Present Mode ===")
            if present.is_visible():
                present.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                shot(page, "15-present-slide-1")
                print("  Presentation mode active")

                for i in range(4):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(800)
                    shot(page, f"16-present-slide-{i+2}")
                print("  Navigated through slides")

                page.keyboard.press("Escape")
                page.wait_for_timeout(1500)
                shot(page, "17-back-from-present")
                print("  Exited presentation")

            print("\n=============================")
            print("=== ALL TESTS COMPLETE ===")
            print("=============================")
            print(f"Screenshots at: {SHOTS}/")

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback; traceback.print_exc()
            shot(page, "error-state")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
