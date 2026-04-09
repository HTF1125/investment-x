"""Check: does the template layout actually persist and render correctly?"""
import os, subprocess
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SHOTS = "/tmp/reports_tpl_check"
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

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # Create report
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)

        # ── Add a TITLE slide ──
        print("=== 1. Add TITLE slide ===")
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)
        # Check layout picker appeared
        picker = page.locator("text=Choose Layout")
        print(f"  Picker visible: {picker.count() > 0}")
        shot(page, "01_picker")

        # Click TITLE
        page.locator("text=TITLE").first.click()
        page.wait_for_timeout(1000)
        shot(page, "02_title_slide")

        # Check what's inside the canvas
        canvas = page.locator("[class*='aspect-\\[16\\/9\\]']")
        canvas_html = page.evaluate("""
            (() => {
                const c = document.querySelector('[class*="aspect-[16/9]"]');
                if (!c) return 'NO CANVAS';
                return {
                    childCount: c.children.length,
                    inputs: c.querySelectorAll('input').length,
                    placeholders: Array.from(c.querySelectorAll('input')).map(i => i.placeholder),
                    text: c.textContent?.slice(0, 200),
                };
            })()
        """)
        print(f"  Canvas content: {canvas_html}")

        # Fill title
        pres_input = page.locator("input[placeholder='Presentation Title']")
        if pres_input.count() > 0:
            pres_input.first.fill("Test Title Slide")
            print("  [OK] Title filled")
        else:
            print("  [FAIL] No 'Presentation Title' input")
            # Check all inputs
            all_inputs = page.locator("input").all()
            for inp in all_inputs[:5]:
                ph = inp.get_attribute("placeholder") or ""
                val = inp.input_value()
                print(f"    input: placeholder='{ph}' value='{val}'")

        subtitle_input = page.locator("input[placeholder='Subtitle or date']")
        if subtitle_input.count() > 0:
            subtitle_input.first.fill("April 2026")
            print("  [OK] Subtitle filled")
        else:
            print("  [FAIL] No subtitle input")

        shot(page, "03_title_filled")

        # ── Add a CHART slide ──
        print("\n=== 2. Add CHART slide ===")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Choose Layout", timeout=5000)

        # Pick CHART layout — use the modal specifically
        picker_modal = page.locator("text=Choose Layout").locator("..").locator("..")
        chart_layout = picker_modal.locator("text=CHART").first
        if chart_layout.count() > 0:
            chart_layout.click()
            page.wait_for_timeout(1000)
            shot(page, "04_chart_slide_empty")

            # Check for "Click to add chart" placeholder
            placeholder = page.locator("text=Click to add chart")
            print(f"  Chart placeholder: {placeholder.count() > 0}")

            # Check for tiptap (narrative zone)
            tiptap = page.locator(".tiptap-wrapper")
            print(f"  Tiptap (narrative): {tiptap.count() > 0}")
        else:
            print("  [FAIL] No CHART layout option")

        # ── Add a TEXT slide ──
        print("\n=== 3. Add TEXT slide ===")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)
        page.wait_for_selector("text=Choose Layout", timeout=5000)

        picker_modal3 = page.locator("text=Choose Layout").locator("..").locator("..")
        text_layout = picker_modal3.locator("span:has-text('TEXT')").first
        if text_layout.count() > 0:
            text_layout.click()
            page.wait_for_timeout(1000)
            shot(page, "05_text_slide")

            tiptap2 = page.locator(".tiptap-wrapper")
            print(f"  Tiptap editors: {tiptap2.count()}")

            # Type some text
            editor = page.locator(".tiptap-content").last
            if editor.count() > 0:
                editor.click()
                page.keyboard.type("This is a full-text slide with rich text editing.")
                page.wait_for_timeout(300)
                print("  [OK] Typed text")
        else:
            print("  [FAIL] No TEXT layout option")

        # ── Switch slide 2 to CHART+TEXT layout ──
        print("\n=== 4. Switch layout ===")
        # Go back to slide 2
        thumbs = page.locator("[class*='cursor-pointer'][class*='rounded'][class*='border']")
        print(f"  Thumbnails: {thumbs.count()}")
        if thumbs.count() >= 2:
            thumbs.nth(1).click()  # slide 2
            page.wait_for_timeout(1000)
            shot(page, "06_slide2_before_switch")

            # Find layout switcher buttons (title attributes)
            switcher = page.locator("[title='Chart with side text']")
            if switcher.count() > 0:
                switcher.first.click()
                page.wait_for_timeout(1000)
                shot(page, "07_slide2_after_switch")

                # Check both chart zone and text zone exist
                placeholder2 = page.locator("text=Click to add chart")
                tiptap3 = page.locator(".tiptap-wrapper")
                print(f"  After switch: chart_placeholder={placeholder2.count() > 0} tiptap={tiptap3.count() > 0}")
                if placeholder2.count() > 0 and tiptap3.count() > 0:
                    print("  [OK] Layout switched to Chart+Text")
                else:
                    print("  [WARN] Layout switch might not have worked properly")
            else:
                print("  [FAIL] Layout switcher 'Chart with side text' not found")
                # Check what layout buttons exist
                all_btns = page.locator("button[title]").all()
                for btn in all_btns[:10]:
                    title = btn.get_attribute("title") or ""
                    if title:
                        print(f"    button title: '{title}'")

        # ── Wait for auto-save then reload to test persistence ──
        print("\n=== 5. Persistence test ===")
        page.wait_for_timeout(2000)  # auto-save

        # Get current URL (report ID)
        url = page.url
        print(f"  URL: {url}")

        # Hard reload
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        shot(page, "08_after_reload")

        # Check slides still exist
        thumbs2 = page.locator("[class*='cursor-pointer'][class*='rounded'][class*='border']")
        print(f"  Thumbnails after reload: {thumbs2.count()}")

        # Check slide 1 still has title
        if thumbs2.count() >= 1:
            thumbs2.first.click()
            page.wait_for_timeout(1000)
            title_val = page.evaluate("""
                (() => {
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {
                        if (inp.value && inp.value.includes('Test Title')) return inp.value;
                    }
                    return 'NOT FOUND';
                })()
            """)
            print(f"  Slide 1 title after reload: '{title_val}'")

        # Console
        relevant = [e for e in errors if not any(x in e for x in ["401", "favicon", "RSC", "CORS"])]
        if relevant:
            print(f"\n  Console errors ({len(relevant)}):")
            for e in relevant[:5]:
                print(f"    {e[:150]}")
        else:
            print(f"\n  Console: clean")

        browser.close()

if __name__ == "__main__":
    main()
