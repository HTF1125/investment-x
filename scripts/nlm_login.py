"""NotebookLM login script. Opens browser, you log in, press Enter to save."""
import asyncio
import sys
from pathlib import Path

def main():
    from playwright.sync_api import sync_playwright

    storage_path = Path.home() / ".notebooklm" / "storage_state.json"
    browser_profile = Path.home() / ".notebooklm" / "browser_profile"
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Storage path: {storage_path}")
    print("Connecting to existing browser profile...\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(browser_profile),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--password-store=basic",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://notebooklm.google.com/")
        print(f"Navigated to: {page.url}")
        print("Log in if needed, then come back here.\n")

        input("Press ENTER to save cookies and close browser... ")

        context.storage_state(path=str(storage_path))
        context.close()

    print(f"\nAuthentication saved to: {storage_path}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    main()
