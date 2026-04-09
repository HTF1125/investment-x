"""E2E test: template-based slide editor."""
import os, subprocess
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SHOTS = "/tmp/reports_templates"
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

def pick_chart_into(page, pack_name, chart_idx=0):
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
        if 5 < len(text) < 80 and not any(s in text for s in skip) and "Close" not in (btns2.nth(i).get_attribute("aria-label") or ""):
            if picked == chart_idx:
                btns2.nth(i).click()
                return text[:50]
            picked += 1
    return None

def main():
    passed = 0
    failed = 0
    issues = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        # Create report
        print("=== Setup ===")
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)

        title_input = page.locator("input[placeholder*='title' i]")
        if title_input.count() > 0:
            title_input.first.fill("Template Test")

        # ═══ TEST 1: Layout picker appears ═══
        print("\n═══ TEST 1: Layout picker ═══")
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)
        picker = page.locator("text=Choose Layout")
        if picker.count() > 0:
            print("  [OK] Layout picker modal appeared")
            # Count layout options
            layout_buttons = page.locator(".fixed button:has(svg)")
            # Filter to just the layout buttons (those inside the picker)
            picker_btns = page.locator("text=Choose Layout").locator("..").locator("..").locator("button")
            print(f"  Layout buttons: {picker_btns.count()}")
            passed += 1
            shot(page, "01_layout_picker")
        else:
            failed += 1
            issues.append("Layout picker didn't appear")
            print("  FAIL")

        # ═══ TEST 2: Title slide ═══
        print("\n═══ TEST 2: Title slide ═══")
        # Click the "Title" layout (first button)
        title_layout = page.locator("text=TITLE").first
        if title_layout.count() > 0:
            title_layout.click()
            page.wait_for_timeout(1000)

            # Check centered title input
            pres_title = page.locator("input[placeholder*='Presentation Title']")
            if pres_title.count() > 0:
                pres_title.first.fill("Q2 2026 Macro Intelligence")
                print("  [OK] Title slide with centered input")
                passed += 1
            else:
                failed += 1
                issues.append("Title slide missing 'Presentation Title' input")
            shot(page, "02_title_slide")
        else:
            failed += 1
            issues.append("Could not click Title layout")

        # ═══ TEST 3: Chart+Text slide ═══
        print("\n═══ TEST 3: Chart+Text slide ═══")
        page.locator("button:has-text('New Slide')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('New Slide')").last.click()
        page.wait_for_timeout(1000)

        # Pick "Chart + Text" layout
        ct = page.locator("text=CHART + TEXT")
        if ct.count() > 0:
            ct.first.click()
            page.wait_for_timeout(1000)

            # Check for chart placeholder and text zone
            chart_placeholder = page.locator("text=Click to add chart")
            tiptap = page.locator(".tiptap-wrapper")
            print(f"  Chart placeholder: {chart_placeholder.count()}")
            print(f"  Tiptap editor: {tiptap.count()}")
            if chart_placeholder.count() > 0 and tiptap.count() > 0:
                passed += 1
                print("  [OK] Chart+Text layout with both zones")
            else:
                failed += 1
                issues.append("Chart+Text layout missing zones")
            shot(page, "03_chart_text_empty")
        else:
            failed += 1
            issues.append("Could not find Chart+Text layout")

        # ═══ TEST 4: Insert chart ═══
        print("\n═══ TEST 4: Insert chart ═══")
        placeholder = page.locator("text=Click to add chart")
        if placeholder.count() > 0:
            placeholder.first.click()
            page.wait_for_timeout(1500)

            name = pick_chart_into(page, "Macro Radar", 0)
            print(f"  Picked: {name}")
            # Wait for resolve
            for s in range(15):
                page.wait_for_timeout(1000)
                if page.evaluate("document.querySelectorAll('.js-plotly-plot').length > 0"):
                    print(f"  Resolved in {s+1}s")
                    passed += 1
                    break
            else:
                failed += 1
                issues.append("Chart didn't resolve")
            shot(page, "04_chart_inserted")

        # Type in text zone
        tiptap2 = page.locator(".tiptap-content").last
        if tiptap2.count() > 0:
            tiptap2.click()
            page.keyboard.type("Fed liquidity declining. Watch TGA rebuild.")
            page.wait_for_timeout(300)
            print("  [OK] Typed in text zone")

        # ═══ TEST 5: Layout switcher ═══
        print("\n═══ TEST 5: Layout switcher ═══")
        # The small layout buttons above the canvas
        switcher_btns = page.locator("[title*='Full-width chart'], [title*='Chart with side text']")
        if switcher_btns.count() > 0:
            print(f"  Switcher buttons: {switcher_btns.count()}")
            passed += 1
        else:
            # Try any small layout icon buttons
            small_layouts = page.locator("button:has(svg[viewBox])").filter(has=page.locator("rect"))
            print(f"  Small layout SVGs: {small_layouts.count()}")
            if small_layouts.count() >= 3:
                passed += 1
            else:
                failed += 1
                issues.append("Layout switcher not found")
        shot(page, "05_with_switcher")

        # ═══ TEST 6: 16:9 canvas ═══
        print("\n═══ TEST 6: 16:9 canvas ═══")
        canvas = page.locator("[class*='aspect-\\[16\\/9\\]']")
        if canvas.count() > 0:
            box = canvas.first.bounding_box()
            if box:
                ratio = box["width"] / box["height"]
                print(f"  Canvas: {box['width']:.0f}x{box['height']:.0f} ratio={ratio:.2f}")
                if 1.7 < ratio < 1.8:
                    passed += 1
                else:
                    failed += 1
                    issues.append(f"Wrong ratio: {ratio:.2f}")
        else:
            failed += 1
            issues.append("No 16:9 canvas")

        # ═══ TEST 7: Export PPTX ═══
        print("\n═══ TEST 7: Export PPTX ═══")
        page.wait_for_timeout(2000)  # auto-save
        try:
            with page.expect_download(timeout=120000) as dl:
                page.locator("button:has-text('PPTX')").first.click()
            print(f"  Downloaded: {dl.value.suggested_filename}")
            passed += 1
        except Exception as e:
            failed += 1
            issues.append(f"PPTX: {e}")

        page.wait_for_timeout(2000)

        # ═══ TEST 8: Export PDF ═══
        print("\n═══ TEST 8: Export PDF ═══")
        try:
            with page.expect_download(timeout=120000) as dl:
                page.locator("button:has-text('PDF')").first.click()
            print(f"  Downloaded: {dl.value.suggested_filename}")
            passed += 1
        except Exception as e:
            failed += 1
            issues.append(f"PDF: {e}")

        # ═══ TEST 9: Console errors ═══
        print("\n═══ TEST 9: Console ═══")
        relevant = [e for e in errors if not any(x in e for x in ["401", "favicon", "RSC", "CORS"])]
        if not relevant:
            passed += 1
            print("  Clean")
        else:
            failed += 1
            for e in relevant[:3]:
                print(f"  {e[:150]}")
            issues.append(f"{len(relevant)} console errors")

        # Summary
        total = passed + failed
        print(f"\n{'='*50}")
        print(f"RESULTS: {passed}/{total} passed, {failed} failed")
        print(f"{'='*50}")
        if issues:
            for i, iss in enumerate(issues, 1):
                print(f"  {i}. {iss}")

        print(f"\nScreenshots: {SHOTS}/")
        browser.close()

if __name__ == "__main__":
    main()
