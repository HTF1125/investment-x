"""Create a Macro Outlook report with charts via Playwright."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ix.db.conn import conn
conn.connect()
from ix.common.security.auth import create_user_token
from sqlalchemy.orm import Session
from ix.db.models import User

with Session(conn.engine) as s:
    admin = s.query(User).filter(User.role == "admin").first()
    TOKEN = create_user_token(str(admin.email), role="admin")
    print(f"Auth: {admin.email}")

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
SHOTS = "/tmp/report-create"
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
        page.set_default_timeout(15000)

        try:
            # ── 1. Go to reports ──
            print("\n=== 1. Reports page ===")
            page.goto(f"{BASE}/reports")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            shot(page, "01-empty-reports")

            # ── 2. New Report → Macro Outlook ──
            print("\n=== 2. Create from Macro Outlook template ===")
            page.locator('button:has-text("New Report")').first.click()
            page.wait_for_timeout(1000)
            shot(page, "02-template-picker")

            page.locator('button:has-text("Macro Outlook")').first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            shot(page, "03-editor-loaded")

            # ── 3. Edit report title ──
            print("\n=== 3. Edit title ===")
            title_bar = page.locator('input[placeholder="Report title..."]').first
            if title_bar.is_visible(timeout=3000):
                title_bar.click(click_count=3)
                title_bar.fill("Q2 2026 Macro Outlook")
                print("  Report title set")

            # ── 4. Edit slide 1 title ──
            print("\n=== 4. Edit title slide ===")
            title_input = page.locator('input[placeholder="Presentation Title"]').first
            if title_input.is_visible(timeout=3000):
                title_input.click(click_count=3)
                title_input.fill("Macro Regime Monitor")
                print("  Slide title: Macro Regime Monitor")

            subtitle_input = page.locator('input[placeholder="Subtitle or date"]').first
            if subtitle_input.is_visible(timeout=2000):
                subtitle_input.click(click_count=3)
                subtitle_input.fill("Investment Strategy Group  |  Q2 2026")
                print("  Subtitle set")
            shot(page, "04-title-slide-edited")

            # ── 5. Go to slide 2 (KPIs) — edit values ──
            print("\n=== 5. Edit KPI slide ===")
            thumbnails = page.locator('.space-y-1\\.5 > div[class*="rounded"]')
            if thumbnails.count() == 0:
                thumbnails = page.locator('[class*="cursor-pointer"][class*="border"][class*="rounded"]')

            thumbnails.nth(1).click()
            page.wait_for_timeout(600)

            # Fill KPI values
            kpi_values = page.locator('input[placeholder="—"]')
            kpi_count = kpi_values.count()
            values = ["2.8%", "3.2%", "3.9%", "4.25%"]
            for i in range(min(kpi_count, len(values))):
                kpi_values.nth(i).click(click_count=3)
                kpi_values.nth(i).fill(values[i])

            # Fill KPI changes
            kpi_changes = page.locator('input[placeholder="Change"]')
            changes = ["+0.3%", "-0.1%", "-0.2%", "+15bps"]
            for i in range(min(kpi_changes.count(), len(changes))):
                kpi_changes.nth(i).fill(changes[i])

            shot(page, "05-kpis-filled")
            print(f"  Filled {min(kpi_count, len(values))} KPI values")

            # ── 6. Go to slide 4 (chart_text) — insert a chart ──
            print("\n=== 6. Insert chart ===")
            thumbnails.nth(3).click()
            page.wait_for_timeout(600)

            add_chart = page.locator('button:has-text("Click to add chart")').first
            if add_chart.is_visible(timeout=3000):
                add_chart.click()
                page.wait_for_timeout(2000)
                shot(page, "06-chart-picker-open")

                # Find and select a chart
                chart_items = page.locator('button:has(.lucide-line-chart)')
                n = chart_items.count()
                print(f"  Charts available: {n}")

                if n > 0:
                    chart_items.first.click()
                    page.wait_for_timeout(2500)
                    shot(page, "07-chart-preview")

                    insert_btn = page.locator('button:has-text("Insert Chart")').first
                    if insert_btn.is_visible(timeout=3000):
                        insert_btn.click()
                        page.wait_for_timeout(3000)
                        shot(page, "08-chart-inserted")
                        print("  Chart inserted!")
                else:
                    print("  No charts available (create some Custom Charts first)")
                    close = page.locator('button[aria-label="Close"]').first
                    if close.is_visible(timeout=1000):
                        close.click()
            else:
                print("  No chart placeholder on this slide")

            # ── 7. Visit all slide types for final screenshots ──
            print("\n=== 7. Final slide tour ===")
            thumbnails2 = page.locator('.space-y-1\\.5 > div[class*="rounded"]')
            if thumbnails2.count() == 0:
                thumbnails2 = page.locator('[class*="cursor-pointer"][class*="border"][class*="rounded"]')

            slide_names = []
            for i in range(min(thumbnails2.count(), 10)):
                thumbnails2.nth(i).click()
                page.wait_for_timeout(400)
                # Read slide title from thumbnail
                name_el = thumbnails2.nth(i).locator('p').first
                name = name_el.text_content() if name_el.is_visible(timeout=500) else f"Slide {i+1}"
                slide_names.append(name)
                shot(page, f"09-tour-{i+1:02d}-{name.replace(' ', '_')[:20]}")

            print(f"  Toured {len(slide_names)} slides: {', '.join(slide_names)}")

            # ── 8. Wait for auto-save then present ──
            print("\n=== 8. Present mode ===")
            page.wait_for_timeout(2000)  # Let auto-save complete

            present_btn = page.locator('button:has-text("Present")').first
            if present_btn.is_visible():
                present_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)

                # Screenshot all slides in presentation
                for i in range(min(len(slide_names), 10)):
                    shot(page, f"10-present-{i+1:02d}")
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(800)

                print(f"  Presented {len(slide_names)} slides")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)

            print("\n=== DONE ===")
            print(f"Screenshots: {SHOTS}/")

        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback; traceback.print_exc()
            shot(page, "error")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
