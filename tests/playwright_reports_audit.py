"""
Playwright audit of the Reports page.
Servers must be running: frontend :3000, backend :8001.
"""
import os, subprocess
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

FRONTEND = "http://localhost:3000"
SHOTS = "/tmp/reports_audit"
os.makedirs(SHOTS, exist_ok=True)

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  [SHOT] {path}")

def safe_click(page, selector, timeout=5000):
    loc = page.locator(selector).last
    if loc.count() == 0:
        return False
    try:
        loc.scroll_into_view_if_needed(timeout=3000)
        loc.click(timeout=timeout)
        return True
    except PWTimeout:
        return False

def get_token():
    result = subprocess.run(
        ["python", "-c",
         "from ix.common.security.auth import create_user_token; print(create_user_token('roberthan1125@gmail.com', role='owner'))"],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
    )
    return result.stdout.strip()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()
        findings = []

        # === 1. Reports list ===
        print("\n=== 1. Reports list ===")
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        shot(page, "01_list")

        h1 = page.locator("h1")
        print(f"  h1: '{h1.first.text_content() if h1.count() > 0 else 'NONE'}'")
        has_new = page.locator("button:has-text('New Report')").count() > 0
        print(f"  New Report btn: {has_new}")
        if not has_new:
            findings.append("CRITICAL: Not authenticated or New Report button missing")
            browser.close()
            return

        # Check existing reports
        existing_cards = page.locator("h3").all_text_contents()
        print(f"  Existing reports: {existing_cards}")

        # === 2. Create report ===
        print("\n=== 2. Create report ===")
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        shot(page, "02_new_report")
        print(f"  URL: {page.url}")

        # === 3. Editor structure ===
        print("\n=== 3. Editor structure ===")
        elements = {
            "Title input": page.locator("input[placeholder*='title' i]").count(),
            "Back btn": page.locator("button:has-text('Reports')").count(),
            "New Slide": page.locator("button:has-text('New Slide')").count(),
            "PPTX": page.locator("button:has-text('PPTX')").count(),
            "PDF": page.locator("button:has-text('PDF')").count(),
            "Theme sun": page.locator("button svg").count(),
        }
        for k, v in elements.items():
            status = "[OK]" if v > 0 else "[MISSING]"
            print(f"  {status} {k}: {v}")
            if v == 0:
                findings.append(f"MISSING: {k}")

        # === 4. Create first slide ===
        print("\n=== 4. Add slide ===")
        # Click "New Slide" button (in the sidebar or empty state)
        ns = page.locator("button:has-text('New Slide')")
        if ns.count() > 0:
            ns.first.click()
            page.wait_for_timeout(1500)
            shot(page, "03_first_slide")
            print("  [OK] First slide created")

        # Check slide count
        slide_counter = page.text_content("body") or ""
        if "1 slides" in slide_counter or "1 slide" in slide_counter.lower():
            print("  [OK] Slide count shows 1")

        # === 5. Test block toolbar ===
        print("\n=== 5. Block toolbar ===")
        for bt in ["Heading", "Text", "Chart", "Divider"]:
            c = page.locator(f"button:has-text('{bt}')").count()
            print(f"  Add {bt}: {c}")
            if c == 0:
                findings.append(f"MISSING: Add {bt} button after creating slide")

        # === 6. Add heading block ===
        print("\n=== 6. Add Heading block ===")
        if safe_click(page, "button:has-text('Heading')"):
            page.wait_for_timeout(500)
            h_inputs = page.locator("input[placeholder*='Heading' i]")
            if h_inputs.count() > 0:
                h_inputs.last.fill("Macro Outlook Q2 2026")
                print("  [OK] Typed heading text")
            h_toggles = page.locator("button:has-text('H1'), button:has-text('H2'), button:has-text('H3')")
            print(f"  H-level toggles: {h_toggles.count()}")
            if h_toggles.count() < 3:
                findings.append(f"ISSUE: Only {h_toggles.count()} heading toggles (expected 3+)")
            shot(page, "04_heading_block")
        else:
            findings.append("ISSUE: Could not click Add Heading button")

        # === 7. Add text block ===
        print("\n=== 7. Add Text block ===")
        if safe_click(page, "button:has-text('Text')"):
            page.wait_for_timeout(800)
            tiptap = page.locator(".tiptap-wrapper")
            if tiptap.count() > 0:
                print(f"  [OK] Tiptap editor(s): {tiptap.count()}")
                # Toolbar buttons
                tb = tiptap.last.locator("button")
                print(f"  Toolbar buttons: {tb.count()}")
                if tb.count() < 4:
                    findings.append(f"ISSUE: Tiptap toolbar has {tb.count()} buttons (expected 4)")

                # Type formatted text
                editor = page.locator(".tiptap-content").last
                editor.click()
                page.keyboard.type("The macro environment is shifting. ")
                page.keyboard.press("Control+b")
                page.keyboard.type("Key risks:")
                page.keyboard.press("Control+b")
                page.keyboard.type(" inflation persistence, credit tightening.")
                page.wait_for_timeout(300)
                print("  [OK] Typed rich text with bold")

                # Test bullet list
                page.keyboard.press("Enter")
                # Click bullet list button
                if tb.count() >= 3:
                    tb.nth(2).click()  # 3rd button = bullet list
                    page.keyboard.type("Rates staying higher for longer")
                    page.keyboard.press("Enter")
                    page.keyboard.type("Credit spreads widening")
                    page.wait_for_timeout(300)
                    print("  [OK] Added bullet list items")

                shot(page, "05_text_block")
            else:
                findings.append("ISSUE: Tiptap editor did not render")
        else:
            findings.append("ISSUE: Could not click Add Text button")

        # === 8. Add divider ===
        print("\n=== 8. Add Divider ===")
        if safe_click(page, "button:has-text('Divider')"):
            page.wait_for_timeout(300)
            hrs = page.locator("hr")
            print(f"  [OK] Divider added (hr count: {hrs.count()})")
        else:
            findings.append("ISSUE: Could not click Divider button")

        shot(page, "06_all_blocks")

        # === 9. Block controls (hover) ===
        print("\n=== 9. Block hover controls ===")
        groups = page.locator("[class*='group relative']")
        print(f"  Block groups: {groups.count()}")
        if groups.count() > 0:
            groups.first.hover()
            page.wait_for_timeout(300)
            shot(page, "07_block_hover")
            # Check grip handle visibility
            grips = page.locator("[class*='cursor-grab']")
            print(f"  Drag handles: {grips.count()}")
            trash = page.locator("[title='Remove block']")
            print(f"  Remove buttons: {trash.count()}")

        # === 10. Chart picker ===
        print("\n=== 10. Chart picker ===")
        if safe_click(page, "button:has-text('Chart')"):
            page.wait_for_timeout(1500)
            shot(page, "08_chart_picker")
            modal = page.locator("text=Insert Chart")
            if modal.count() > 0:
                print("  [OK] Chart picker modal opened")
                # Check for packs
                sections = page.locator("text=My Packs").count() + page.locator("text=Published").count()
                print(f"  Pack sections: {sections}")

                # Try clicking a pack
                pack_buttons = page.locator(".fixed button:has(svg)").all()
                clickable_packs = [b for b in pack_buttons if "Chart" not in (b.text_content() or "") and "Close" not in (b.get_attribute("aria-label") or "")]
                print(f"  Clickable pack rows: {len(clickable_packs)}")

                if len(clickable_packs) > 0:
                    clickable_packs[0].click()
                    page.wait_for_timeout(1500)
                    shot(page, "09_pack_charts")

                    # Check for chart items
                    chart_rows = page.locator(".fixed button:has(svg)").all()
                    print(f"  Chart rows after pack click: {len(chart_rows)}")

                    # Try inserting a chart
                    insertable = [b for b in chart_rows if "Close" not in (b.get_attribute("aria-label") or "") and "Back" not in (b.text_content() or "")]
                    if len(insertable) > 0:
                        insertable[0].click()
                        page.wait_for_timeout(2000)
                        shot(page, "10_chart_inserted")
                        print("  [OK] Chart inserted")

                        # Check if Plotly chart rendered
                        plotly = page.locator(".js-plotly-plot, [class*='plotly']")
                        print(f"  Plotly charts on page: {plotly.count()}")
                        if plotly.count() == 0:
                            findings.append("ISSUE: Chart block added but Plotly not rendered")

                # Close picker if still open
                close = page.locator("[aria-label='Close']").last
                if close.count() > 0 and page.locator("text=Insert Chart").count() > 0:
                    close.click()
                    page.wait_for_timeout(300)
            else:
                findings.append("ISSUE: Chart picker modal did not open")
        else:
            findings.append("ISSUE: Could not click Chart button")

        # === 11. Slide sidebar ===
        print("\n=== 11. Slide sidebar ===")
        ns2 = page.locator("button:has-text('New Slide')").last
        if ns2.count() > 0:
            ns2.scroll_into_view_if_needed()
            ns2.click()
            page.wait_for_timeout(800)
            print("  [OK] Second slide added")
            shot(page, "11_two_slides")

            # Count slide thumbnails
            thumbs = page.locator("[class*='cursor-pointer'][class*='rounded'][class*='border']")
            print(f"  Slide thumbnails: {thumbs.count()}")

        # === 12. Auto-save check ===
        print("\n=== 12. Auto-save ===")
        page.wait_for_timeout(2000)
        body_text = page.text_content("body") or ""
        has_saved = "Saved" in body_text
        has_saving = "Saving" in body_text
        has_slides = "slides" in body_text
        print(f"  Saved: {has_saved}, Saving: {has_saving}, 'slides' text: {has_slides}")

        # === 13. Export buttons ===
        print("\n=== 13. Export buttons ===")
        pptx = page.locator("button:has-text('PPTX')").first
        pdf = page.locator("button:has-text('PDF')").first
        if pptx.count() > 0:
            print(f"  PPTX disabled: {pptx.is_disabled()}")
        if pdf.count() > 0:
            print(f"  PDF disabled: {pdf.is_disabled()}")

        # === 14. Responsive ===
        print("\n=== 14. Responsive ===")
        for name, w, h in [("tablet", 768, 1024), ("mobile", 375, 812)]:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(500)
            shot(page, f"12_{name}")
            print(f"  {name}: {w}x{h}")
        page.set_viewport_size({"width": 1440, "height": 900})

        # === 15. Back to list ===
        print("\n=== 15. Back to list ===")
        if safe_click(page, "button:has-text('Reports')"):
            page.wait_for_timeout(2000)
            shot(page, "13_list_final")
            cards = page.locator("h3").all_text_contents()
            print(f"  Reports in list: {cards}")

        # === REPORT ===
        print("\n" + "=" * 60)
        print("AUDIT REPORT")
        print("=" * 60)
        print(f"\nFindings ({len(findings)}):")
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
        if not findings:
            print("  None — all checks passed!")

        print(f"\nScreenshots ({SHOTS}/):")
        for f in sorted(os.listdir(SHOTS)):
            if f.endswith(".png"):
                print(f"  {f} ({os.path.getsize(f'{SHOTS}/{f}') // 1024}KB)")

        browser.close()

if __name__ == "__main__":
    main()
