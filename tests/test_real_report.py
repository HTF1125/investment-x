"""Create a real report with multiple slides, charts, text, and verify everything."""
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

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  [SHOT] {name}.png")

def pick_chart(page, pack_name, chart_index=0):
    """Open picker, select pack, pick chart."""
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
    skip = ["Close", "Back", "Insert Chart", "My Packs", "Published", "Select", pack_name]
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

def wait_chart_resolve(page, timeout=15):
    for s in range(timeout):
        page.wait_for_timeout(1000)
        if page.evaluate("document.querySelectorAll('.js-plotly-plot').length") > 0:
            return True
    return False

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # ── Create report ──
        print("=== Creating report ===")
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)

        # Set report title
        title_input = page.locator("input[placeholder*='title' i]")
        if title_input.count() > 0:
            title_input.first.fill("")
            title_input.first.fill("Q2 2026 Macro Outlook")
            print("  Title set: Q2 2026 Macro Outlook")

        # ── SLIDE 1: Title slide with heading + text ──
        print("\n=== Slide 1: Title slide ===")
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)

        # Type main heading
        h = page.locator("input[placeholder*='Heading']").first
        h.fill("Q2 2026 Macro Intelligence Brief")
        print("  Heading: Q2 2026 Macro Intelligence Brief")

        # Add text block
        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(800)

        editor = page.locator(".tiptap-content").last
        editor.click()
        page.keyboard.type("Prepared by Investment-X Research Team")
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.keyboard.type("Key themes for the quarter:")
        page.keyboard.press("Enter")

        # Add bullet list
        toolbar = page.locator(".tiptap-wrapper").last.locator("button")
        if toolbar.count() >= 3:
            toolbar.nth(2).click()  # Bullet list
        page.keyboard.type("Rates staying higher for longer")
        page.keyboard.press("Enter")
        page.keyboard.type("Credit spreads widening in HY")
        page.keyboard.press("Enter")
        page.keyboard.type("Equity resilience despite macro headwinds")
        page.wait_for_timeout(300)
        print("  Text with bullet list added")

        shot(page, "01_slide1_title")

        # ── SLIDE 2: Liquidity chart ──
        print("\n=== Slide 2: Fed Liquidity chart ===")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)

        # Add heading for slide 2
        h2 = page.locator("input[placeholder*='Heading']").last
        h2.fill("Liquidity Conditions")

        # Add chart
        chart_name = pick_chart(page, "Macro Radar", chart_index=0)
        print(f"  Chart: {chart_name}")
        resolved = wait_chart_resolve(page)
        print(f"  Resolved: {resolved}")

        # Add commentary text below chart
        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(800)
        editor2 = page.locator(".tiptap-content").last
        editor2.click()
        page.keyboard.type("Fed net liquidity continues to decline as QT progresses. ")
        page.keyboard.press("Control+b")
        page.keyboard.type("Watch for TGA rebuild")
        page.keyboard.press("Control+b")
        page.keyboard.type(" post debt ceiling resolution.")
        page.wait_for_timeout(300)
        print("  Commentary added with bold text")

        shot(page, "02_slide2_liquidity")

        # ── SLIDE 3: Credit chart ──
        print("\n=== Slide 3: Credit Spreads chart ===")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)

        h3 = page.locator("input[placeholder*='Heading']").last
        h3.fill("Credit & Risk Conditions")

        # Pick a different chart (index=6 for variety)
        chart_name2 = pick_chart(page, "Macro Radar", chart_index=6)
        print(f"  Chart: {chart_name2}")
        resolved2 = wait_chart_resolve(page)
        print(f"  Resolved: {resolved2}")

        # Add divider + text
        page.locator("button:has-text('Divider')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Divider')").last.click()
        page.wait_for_timeout(300)

        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(800)
        editor3 = page.locator(".tiptap-content").last
        editor3.click()
        page.keyboard.press("Control+i")
        page.keyboard.type("Source: Bloomberg, Investment-X calculations. Data as of April 2026.")
        page.keyboard.press("Control+i")
        page.wait_for_timeout(300)
        print("  Divider + source text (italic) added")

        shot(page, "03_slide3_credit")

        # Wait for auto-save
        page.wait_for_timeout(2000)

        # ── Verify slide sidebar ──
        print("\n=== Verify structure ===")
        slide_count = page.evaluate("document.body.textContent.match(/Slide \\d+ of (\\d+)/)?.[1] || '?'")
        plotly_count = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
        tiptap_count = page.locator(".tiptap-wrapper").count()
        hr_count = page.locator("hr").count()
        print(f"  Slides: {slide_count}")
        print(f"  Plotly charts on current slide: {plotly_count}")
        print(f"  Tiptap editors on current slide: {tiptap_count}")
        print(f"  Dividers: {hr_count}")

        # ── Navigate slides ──
        print("\n=== Navigate slides ===")
        thumbs = page.locator("[class*='cursor-pointer'][class*='rounded'][class*='border']")
        print(f"  Thumbnails: {thumbs.count()}")

        # Click slide 1
        if thumbs.count() >= 3:
            thumbs.nth(0).click()
            page.wait_for_timeout(1000)
            shot(page, "04_slide1_revisit")
            s1_text = page.evaluate("document.querySelector('.tiptap-content')?.textContent?.slice(0, 100) || 'NONE'")
            print(f"  Slide 1 text: {s1_text}")

            # Click slide 2
            thumbs.nth(1).click()
            page.wait_for_timeout(2000)
            shot(page, "05_slide2_revisit")
            s2_plotly = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
            print(f"  Slide 2 plotly: {s2_plotly}")

        # ── Export PPTX ──
        print("\n=== Export PPTX ===")
        try:
            with page.expect_download(timeout=120000) as dl:
                page.locator("button:has-text('PPTX')").first.click()
            download = dl.value
            pptx_path = f"{SHOTS}/Q2_Macro_Outlook.pptx"
            download.save_as(pptx_path)
            size = os.path.getsize(pptx_path)
            print(f"  Downloaded: {download.suggested_filename} ({size:,} bytes)")
        except Exception as e:
            print(f"  FAIL: {e}")

        page.wait_for_timeout(3000)

        # ── Export PDF ──
        print("\n=== Export PDF ===")
        try:
            with page.expect_download(timeout=120000) as dl:
                page.locator("button:has-text('PDF')").first.click()
            download = dl.value
            pdf_path = f"{SHOTS}/Q2_Macro_Outlook.pdf"
            download.save_as(pdf_path)
            size = os.path.getsize(pdf_path)
            print(f"  Downloaded: {download.suggested_filename} ({size:,} bytes)")
        except Exception as e:
            print(f"  FAIL: {e}")

        # ── Console errors ──
        print("\n=== Console ===")
        relevant = [e for e in errors if not any(x in e for x in ["401", "favicon", "RSC", "CORS", "ChunkLoad"])]
        if relevant:
            print(f"  {len(relevant)} errors:")
            for e in relevant[:5]:
                print(f"    {e[:150]}")
        else:
            print("  Clean — no errors")

        # ── Final screenshot ──
        shot(page, "06_final")
        print(f"\nDone! Screenshots in {SHOTS}/")
        browser.close()

if __name__ == "__main__":
    main()
