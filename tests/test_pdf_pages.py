"""Test: export PDF from real report, verify each slide = one page."""
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
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        # Create report
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Set title
        title_input = page.locator("input[placeholder*='title' i]")
        if title_input.count() > 0:
            title_input.first.fill("")
            title_input.first.fill("PDF Page Test")

        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)

        # Slide 1: text only
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)
        h = page.locator("input[placeholder*='Heading']").first
        h.fill("Title Slide")
        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(800)
        page.locator(".tiptap-content").last.click()
        page.keyboard.type("Some narrative text here.")

        # Slide 2: chart + text
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)
        page.locator("input[placeholder*='Heading']").last.fill("Chart Slide")
        name = pick_chart(page, "Macro Radar", 0)
        print(f"  Chart: {name}")
        # Wait for resolve
        for s in range(15):
            page.wait_for_timeout(1000)
            if page.evaluate("document.querySelectorAll('.js-plotly-plot').length") > 0:
                print(f"  Resolved in {s+1}s")
                break

        # Add text below chart
        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(800)
        page.locator(".tiptap-content").last.click()
        page.keyboard.type("Commentary below the chart.")

        # Slide 3: another chart
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)
        page.locator("input[placeholder*='Heading']").last.fill("Second Chart")
        name2 = pick_chart(page, "Macro Radar", 3)
        print(f"  Chart 2: {name2}")
        for s in range(15):
            page.wait_for_timeout(1000)
            if page.evaluate("document.querySelectorAll('.js-plotly-plot').length") > 0:
                print(f"  Resolved in {s+1}s")
                break

        page.wait_for_timeout(2000)  # auto-save

        # Export PDF
        print("\n=== Export PDF ===")
        try:
            with page.expect_download(timeout=120000) as dl:
                page.locator("button:has-text('PDF')").first.click()
            download = dl.value
            pdf_path = f"{SHOTS}/page_test.pdf"
            download.save_as(pdf_path)
            size = os.path.getsize(pdf_path)
            print(f"  Downloaded: {size:,} bytes")

            # Analyze pages
            import subprocess as sp
            result = sp.run(["python", "-c", f"""
import fitz
doc = fitz.open('{pdf_path.replace(chr(92), "/")}')
print(f'Pages: {{len(doc)}}')
for i, pg in enumerate(doc):
    r = pg.rect
    text = pg.get_text().strip()[:80]
    print(f'  Page {{i+1}}: {{r.width:.0f}}x{{r.height:.0f}}pt text={{text}}')
"""], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")

            # Expected: 4 pages (cover + 3 slides), NOT 5+
            page_count = int(result.stdout.split("Pages: ")[1].split("\n")[0])
            expected = 4  # cover + 3 slides
            if page_count == expected:
                print(f"  [PASS] {page_count} pages (expected {expected})")
            else:
                print(f"  [FAIL] {page_count} pages (expected {expected}) — slide split detected!")

        except Exception as e:
            print(f"  FAIL: {e}")

        browser.close()

if __name__ == "__main__":
    main()
