"""Quick test: verify the new PowerPoint-style slide canvas layout."""
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

        # Create report + slide
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)

        # Type a heading
        h = page.locator("input[placeholder*='Heading']")
        if h.count() > 0:
            h.first.fill("Q2 2026 Macro Outlook")

        # Add text block
        text_btn = page.locator("button:has-text('Text')").last
        text_btn.scroll_into_view_if_needed()
        text_btn.click()
        page.wait_for_timeout(800)
        editor = page.locator(".tiptap-content").last
        if editor.count() > 0:
            editor.click()
            page.keyboard.type("Key themes: rates higher for longer, credit tightening, equity resilience.")

        page.wait_for_timeout(500)
        page.screenshot(path=f"{SHOTS}/layout_01_canvas.png")
        print("[OK] Slide canvas screenshot saved")

        # Add a chart
        chart_btn = page.locator("button:has-text('Chart')").last
        chart_btn.scroll_into_view_if_needed()
        chart_btn.click()
        page.wait_for_timeout(1500)

        # Click Macro Radar
        modal_btns = page.locator(".fixed button")
        for i in range(modal_btns.count()):
            if "Macro Radar" in (modal_btns.nth(i).text_content() or ""):
                modal_btns.nth(i).click()
                break
        page.wait_for_timeout(2000)

        # Click first chart
        modal_btns2 = page.locator(".fixed button")
        for i in range(modal_btns2.count()):
            text = (modal_btns2.nth(i).text_content() or "").strip()
            if len(text) > 15 and "Close" not in text and "Back" not in text and "Insert" not in text and "My Packs" not in text and "Published" not in text and "Macro Radar" not in text:
                modal_btns2.nth(i).click()
                print(f"  Picked: {text[:50]}")
                break
        page.wait_for_timeout(5000)  # Wait for resolution

        page.screenshot(path=f"{SHOTS}/layout_02_with_chart.png")
        print("[OK] With chart screenshot saved")

        # Check slide canvas dimensions
        canvas = page.locator("[class*='aspect-\\[16\\/9\\]']")
        if canvas.count() > 0:
            box = canvas.first.bounding_box()
            if box:
                ratio = box["width"] / box["height"] if box["height"] > 0 else 0
                print(f"  Canvas: {box['width']:.0f}x{box['height']:.0f} (ratio: {ratio:.2f}, expected ~1.78)")
        else:
            print("  [WARN] No 16:9 canvas found")

        browser.close()

if __name__ == "__main__":
    main()
