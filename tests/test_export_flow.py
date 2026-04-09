"""Quick test: create report, add block, export PPTX + PDF via browser."""
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
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        context.add_cookies([{"name": "access_token", "value": get_token(), "domain": "localhost", "path": "/"}])
        page = context.new_page()

        # Create report
        page.goto(f"{FRONTEND}/reports")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page.locator("button:has-text('New Report')").first.click()
        page.wait_for_timeout(3000)
        print(f"Editor: {page.url}")

        # Add slide
        page.locator("button:has-text('New Slide')").first.click()
        page.wait_for_timeout(1000)

        # Type heading
        h_input = page.locator("input[placeholder*='Heading' i]")
        if h_input.count() > 0:
            h_input.first.fill("Export Test Slide")
            page.wait_for_timeout(500)

        # Add text block
        page.locator("button:has-text('Text')").last.scroll_into_view_if_needed()
        page.locator("button:has-text('Text')").last.click()
        page.wait_for_timeout(1000)

        editor = page.locator(".tiptap-content").last
        if editor.count() > 0:
            editor.click()
            page.keyboard.type("This is test content for export.")
            page.wait_for_timeout(500)

        # Wait for auto-save
        page.wait_for_timeout(2000)

        # Test PPTX export
        print("\n=== Testing PPTX export ===")
        with page.expect_download(timeout=60000) as download_info:
            page.locator("button:has-text('PPTX')").first.click()
        download = download_info.value
        pptx_path = f"{SHOTS}/export_test.pptx"
        download.save_as(pptx_path)
        size = os.path.getsize(pptx_path)
        print(f"  [OK] PPTX downloaded: {size} bytes -> {pptx_path}")

        # Wait a sec then test PDF
        page.wait_for_timeout(2000)

        print("\n=== Testing PDF export ===")
        with page.expect_download(timeout=60000) as download_info:
            page.locator("button:has-text('PDF')").first.click()
        download = download_info.value
        pdf_path = f"{SHOTS}/export_test.pdf"
        download.save_as(pdf_path)
        size = os.path.getsize(pdf_path)
        print(f"  [OK] PDF downloaded: {size} bytes -> {pdf_path}")

        page.screenshot(path=f"{SHOTS}/export_done.png", full_page=True)
        print("\nAll exports successful!")
        browser.close()

if __name__ == "__main__":
    main()
