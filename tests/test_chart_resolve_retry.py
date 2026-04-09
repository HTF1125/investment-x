"""Test: add two charts from Macro Radar, verify BOTH resolve."""
import os, subprocess
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SHOTS = "/tmp/reports_real"
os.makedirs(SHOTS, exist_ok=True)

def get_token():
    result = subprocess.run(
        ["python", "-c",
         "from ix.common.security.auth import create_user_token; from datetime import timedelta; print(create_user_token('roberthan1125@gmail.com', role='owner', expires_delta=timedelta(hours=24)))"],
        capture_output=True, text=True, cwd="D:/investment-x"
    )
    return result.stdout.strip()

def pick_chart(page, pack_name, chart_index=0):
    page.locator("button:has-text('Chart')").last.scroll_into_view_if_needed()
    page.locator("button:has-text('Chart')").last.click()
    page.wait_for_timeout(1500)
    page.wait_for_selector("text=Insert Chart", timeout=5000)
    overlay = page.locator(".fixed.inset-0").last
    btns = overlay.locator("button")
    for i in range(btns.count()):
        if pack_name in (btns.nth(i).text_content() or ""):
            btns.nth(i).click()
            break
    page.wait_for_timeout(2000)
    btns2 = overlay.locator("button")
    skip = ["Close", "Back", "Insert Chart", "My Packs", "Published", pack_name]
    picked = 0
    for i in range(btns2.count()):
        text = (btns2.nth(i).text_content() or "").strip()
        aria = btns2.nth(i).get_attribute("aria-label") or ""
        if 5 < len(text) < 80 and not any(s in text for s in skip) and "Close" not in aria:
            if picked == chart_index:
                btns2.nth(i).click()
                return text[:60]
            picked += 1
    return None

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        # Create report + slide
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)

        # Add chart 1
        print("=== Chart 1 ===")
        name1 = pick_chart(page, "Macro Radar", 0)
        print(f"  Picked: {name1}")
        for s in range(20):
            page.wait_for_timeout(1000)
            c = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
            if c > 0:
                print(f"  Resolved in {s+1}s")
                break
        else:
            print("  TIMEOUT")

        # Add slide 2 with chart 2
        print("\n=== Chart 2 (new slide) ===")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)

        name2 = pick_chart(page, "Macro Radar", 6)
        print(f"  Picked: {name2}")

        # Wait for chart 2 to resolve — stay on this slide
        for s in range(20):
            page.wait_for_timeout(1000)
            c = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
            loading = page.evaluate("document.body.textContent.includes('Loading chart data')")
            print(f"  [{s+1:2d}s] plotly={c} loading={loading}")
            if c > 0:
                print(f"  Resolved!")
                break
        else:
            print("  TIMEOUT — chart 2 didn't resolve")

        page.screenshot(path=f"{SHOTS}/two_charts.png")

        # Switch back to slide 1 and verify chart is still there
        print("\n=== Verify slide 1 still has chart ===")
        thumbs = page.locator("[class*='cursor-pointer'][class*='rounded'][class*='border']")
        if thumbs.count() >= 2:
            thumbs.first.click()
            page.wait_for_timeout(2000)
            c1 = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
            print(f"  Slide 1 plotly: {c1}")
            page.screenshot(path=f"{SHOTS}/slide1_verify.png")

        browser.close()

if __name__ == "__main__":
    main()
