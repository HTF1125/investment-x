"""Quick check: what's broken on http://localhost:3000/"""
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Collect console errors
        errors = []
        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)

        page.goto("http://localhost:3000/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        page.screenshot(path="/tmp/homepage_check.png", full_page=True)
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # Check body text
        body = page.text_content("body") or ""
        print(f"\nBody text (first 500 chars):\n{body[:500]}")

        # Check for error overlays
        error_overlay = page.locator("text=Something went wrong, text=Runtime Error, text=Unhandled Runtime Error")
        if error_overlay.count() > 0:
            print(f"\n[ERROR OVERLAY DETECTED]")
            print(error_overlay.first.text_content()[:300])

        # Console errors
        print(f"\nConsole messages ({len(errors)}):")
        for e in errors[:15]:
            print(f"  {e[:200]}")

        # Check network failures
        print("\nDone.")
        browser.close()

if __name__ == "__main__":
    main()
