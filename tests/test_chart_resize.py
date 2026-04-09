"""Test: verify chart resize handle works."""
import os, subprocess
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SHOTS = "/tmp/reports_audit"
os.makedirs(SHOTS, exist_ok=True)

def get_token():
    result = subprocess.run(
        ["python", "-c",
         "from ix.common.security.auth import create_user_token; print(create_user_token('roberthan1125@gmail.com', role='owner'))"],
        capture_output=True, text=True, cwd="D:/investment-x"
    )
    return result.stdout.strip()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        # Setup: create report + slide + chart
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)

        # Add chart via picker
        chart_btn = page.locator("button:has-text('Chart')").last
        chart_btn.scroll_into_view_if_needed()
        chart_btn.click()
        page.wait_for_timeout(1500)

        modal_btns = page.locator(".fixed button")
        for i in range(modal_btns.count()):
            if "Macro Radar" in (modal_btns.nth(i).text_content() or ""):
                modal_btns.nth(i).click()
                break
        page.wait_for_timeout(2000)

        modal_btns2 = page.locator(".fixed button")
        for i in range(modal_btns2.count()):
            text = (modal_btns2.nth(i).text_content() or "").strip()
            if len(text) > 15 and all(x not in text for x in ["Close", "Back", "Insert", "My Packs", "Macro Radar"]):
                modal_btns2.nth(i).click()
                print(f"  Picked: {text[:50]}")
                break
        page.wait_for_timeout(5000)

        page.screenshot(path=f"{SHOTS}/resize_01_before.png")

        # Get chart container height before resize
        chart_div = page.evaluate("""
            (() => {
                const plotly = document.querySelector('.js-plotly-plot');
                if (!plotly) return null;
                const container = plotly.parentElement;
                return { height: container.offsetHeight, tag: container.tagName };
            })()
        """)
        print(f"  Chart container before: {chart_div}")

        # Find and use the resize handle
        handle = page.locator("[data-resize-handle='chart']")
        print(f"  Resize handles: {handle.count()}")

        if handle.count() > 0:
            # Hover over chart area to reveal handle
            chart_group = page.locator("[class*='group/chart']").first
            chart_group.hover()
            page.wait_for_timeout(300)

            # Get handle position
            hbox = handle.first.bounding_box()
            if hbox:
                cx = hbox['x'] + hbox['width'] / 2
                cy = hbox['y'] + hbox['height'] / 2
                print(f"  Handle center: ({cx:.0f}, {cy:.0f})")

                # Drag down 150px
                page.mouse.move(cx, cy)
                page.mouse.down()
                for step in range(15):
                    page.mouse.move(cx, cy + (step + 1) * 10)
                page.mouse.up()
                page.wait_for_timeout(500)

                # Check new height
                chart_div2 = page.evaluate("""
                    (() => {
                        const plotly = document.querySelector('.js-plotly-plot');
                        if (!plotly) return null;
                        const container = plotly.parentElement;
                        return { height: container.offsetHeight };
                    })()
                """)
                print(f"  Chart container after +150px drag: {chart_div2}")

                page.screenshot(path=f"{SHOTS}/resize_02_after.png")

                if chart_div and chart_div2:
                    diff = (chart_div2['height'] or 0) - (chart_div['height'] or 0)
                    print(f"  Height change: {diff}px ({'[OK]' if diff > 50 else '[FAIL]'})")
            else:
                print("  [FAIL] Handle has no bounding box (invisible?)")
        else:
            print("  [FAIL] No resize handle found")

        browser.close()

if __name__ == "__main__":
    main()
