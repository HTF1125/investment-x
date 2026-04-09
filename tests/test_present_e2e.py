"""E2E test: Presentation Mode at /present"""
import os
from playwright.sync_api import sync_playwright

FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000")
SHOTS = "/tmp/present_e2e"
os.makedirs(SHOTS, exist_ok=True)


def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  [SHOT] {name}.png")


def get_counter(page):
    """Extract 'N / M' counter text from the page."""
    text = page.inner_text("body").strip()
    lines = text.split("\n")
    for line in reversed(lines):
        line = line.strip()
        if "/" in line and len(line) < 10:
            parts = line.split("/")
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                return line.strip()
    return None


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # ── Test 1: Initial render ──
        print("\n[TEST] Navigate to /present (demo mode)")
        page.goto(f"{FRONTEND}/present")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        shot(page, "01_slide1_title")

        counter = get_counter(page)
        assert counter == "1 / 5", f"Expected '1 / 5', got '{counter}'"
        print("[PASS] Slide counter: 1 / 5")

        # Verify title slide content
        assert "Macro Regime Monitor" in page.inner_text("body")
        print("[PASS] Title slide content rendered")

        # ── Test 2: ArrowRight advances ──
        print("\n[TEST] ArrowRight advances to slide 2")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(1000)

        counter = get_counter(page)
        assert counter == "2 / 5", f"Expected '2 / 5', got '{counter}'"
        print("[PASS] Advanced to slide 2")

        # Wait for Plotly chart to load
        page.wait_for_timeout(2000)
        assert "Yield" in page.inner_text("body") or "US Treasury" in page.inner_text("body")
        print("[PASS] Slide 2 chart content rendered")
        shot(page, "02_slide2_yield_curve")

        # ── Test 3: ArrowLeft goes back ──
        print("\n[TEST] ArrowLeft returns to slide 1")
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(800)

        counter = get_counter(page)
        assert counter == "1 / 5", f"Expected '1 / 5', got '{counter}'"
        print("[PASS] Returned to slide 1")

        # ── Test 4: Navigate to last slide ──
        print("\n[TEST] Navigate to last slide (5/5)")
        for i in range(4):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(600)

        counter = get_counter(page)
        assert counter == "5 / 5", f"Expected '5 / 5', got '{counter}'"
        print("[PASS] Reached last slide (5/5)")

        assert "Key Takeaways" in page.inner_text("body")
        print("[PASS] Last slide content rendered")
        shot(page, "03_slide5_takeaways")

        # ── Test 5: Can't go past last slide ──
        print("\n[TEST] ArrowRight at last slide stays put")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(500)

        counter = get_counter(page)
        assert counter == "5 / 5", f"Expected '5 / 5', got '{counter}'"
        print("[PASS] Stays on last slide")

        # ── Test 6: Progress bar exists ──
        print("\n[TEST] Progress bar rendered")
        bar = page.query_selector("[data-testid='progress-bar']")
        assert bar is not None, "Progress bar not found"
        print("[PASS] Progress bar exists")

        # ── Test 7: Space key also advances ──
        print("\n[TEST] Space key navigation")
        page.goto(f"{FRONTEND}/present")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.keyboard.press("Space")
        page.wait_for_timeout(800)

        counter = get_counter(page)
        assert counter == "2 / 5", f"Expected '2 / 5', got '{counter}'"
        print("[PASS] Space advances to slide 2")

        # ── Test 8: Slide 3 (chart_text layout) ──
        print("\n[TEST] Slide 3 chart_text layout")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(1500)

        body = page.inner_text("body")
        assert "S&P 500" in body or "Drawdown" in body
        assert "tariff shock" in body.lower() or "key observations" in body.lower()
        print("[PASS] Slide 3 chart + text rendered")
        shot(page, "04_slide3_chart_text")

        # ── Test 9: Slide 4 (two_charts layout) ──
        print("\n[TEST] Slide 4 two_charts layout")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(1500)

        body = page.inner_text("body")
        assert "Credit" in body or "Volatility" in body
        assert "VIX" in body
        print("[PASS] Slide 4 two charts rendered")
        shot(page, "05_slide4_two_charts")

        # ── Done ──
        shot(page, "06_final")
        browser.close()
        print("\n=== All presentation mode tests passed ===")


if __name__ == "__main__":
    main()
