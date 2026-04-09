"""Test: create report, add code-based chart, verify it resolves."""
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

        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type in ("error", "warning") else None)

        # 1. Create report + add slide
        print("=== Setup ===")
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)
        print(f"  Report created, slide added")

        # 2. Open chart picker
        print("\n=== Open chart picker ===")
        add_chart = page.locator("button:has-text('Chart')").last
        add_chart.scroll_into_view_if_needed()
        add_chart.click()
        page.wait_for_timeout(1500)

        # 3. Click "Macro Radar" pack — use the modal specifically
        print("\n=== Select Macro Radar pack ===")
        # The modal has class "fixed" — find buttons inside it
        modal_buttons = page.locator(".fixed button")
        pack_clicked = False
        for i in range(modal_buttons.count()):
            btn = modal_buttons.nth(i)
            text = (btn.text_content() or "").strip()
            if "Macro Radar" in text:
                btn.click()
                pack_clicked = True
                print(f"  Clicked: {text[:50]}")
                break
        if not pack_clicked:
            print("  [FAIL] Macro Radar not found in modal")
            browser.close()
            return

        page.wait_for_timeout(2000)
        page.screenshot(path=f"{SHOTS}/resolve_01_pack.png")

        # 4. Click "Fed Net Liquidity" chart (it has code, no cached figure)
        print("\n=== Select chart ===")
        modal_buttons2 = page.locator(".fixed button")
        chart_clicked = False
        for i in range(modal_buttons2.count()):
            btn = modal_buttons2.nth(i)
            text = (btn.text_content() or "").strip()
            if "Fed Net Liquidity" in text:
                btn.click()
                chart_clicked = True
                print(f"  Clicked: {text[:60]}")
                break

        if not chart_clicked:
            # Try any chart that's not a nav button
            for i in range(modal_buttons2.count()):
                btn = modal_buttons2.nth(i)
                text = (btn.text_content() or "").strip()
                aria = btn.get_attribute("aria-label") or ""
                if len(text) > 10 and "Close" not in aria and "Back" not in text and "Insert" not in text and "My Packs" not in text and "Published" not in text:
                    btn.click()
                    chart_clicked = True
                    print(f"  Clicked fallback: {text[:60]}")
                    break

        if not chart_clicked:
            print("  [FAIL] No chart to click")
            browser.close()
            return

        # 5. Wait for resolution
        print("\n=== Waiting for chart resolution ===")
        for sec in range(20):
            page.wait_for_timeout(1000)

            # Check states
            plotly_count = page.evaluate("document.querySelectorAll('.js-plotly-plot').length")
            loading_text = page.evaluate("document.body.textContent.includes('Loading chart data')")
            spinner_count = page.evaluate("document.querySelectorAll('.animate-spin').length")
            source_text = page.evaluate("document.body.textContent.includes('Source:')")

            status = f"plotly={plotly_count} loading={loading_text} spinner={spinner_count} source={source_text}"
            print(f"  [{sec+1:2d}s] {status}")

            if plotly_count > 0:
                print("  [SUCCESS] Chart rendered!")
                break
            if not loading_text and spinner_count == 0 and sec > 3:
                # Check if chart block exists but is empty
                chart_area = page.evaluate("""
                    (() => {
                        const blocks = document.querySelectorAll('[class*="aspect-"]');
                        if (blocks.length === 0) return 'no chart blocks';
                        return blocks[0].innerHTML.slice(0, 150);
                    })()
                """)
                print(f"  Chart block HTML: {chart_area}")

                # Also check for errors in state
                block_errors = [e for e in errors if "BlockEditor" in e or "buildChart" in e or "timeseries" in e]
                if block_errors:
                    print(f"  Related errors:")
                    for e in block_errors[:3]:
                        print(f"    {e[:200]}")
                break

        page.screenshot(path=f"{SHOTS}/resolve_02_result.png")

        # 6. Console summary
        print("\n=== Console ===")
        relevant = [e for e in errors if "401" not in e and "favicon" not in e and "RSC" not in e and "CORS" not in e]
        if relevant:
            print(f"  {len(relevant)} messages:")
            for e in relevant[:10]:
                print(f"    {e[:200]}")
        else:
            print("  Clean (no relevant errors)")

        browser.close()

if __name__ == "__main__":
    main()
