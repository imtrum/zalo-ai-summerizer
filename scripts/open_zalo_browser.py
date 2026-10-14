from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"


def main() -> None:
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )
        
        # context.wait_for_event("close", timeout=0)

        try:
            # if context.pages : print(len(context.pages))
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")

            print("Log in to Zalo manually in the browser.")
            print("Close the browser window when you finish.")

            # Wait until the page is closed (no timeout).
            context.wait_for_event("close", timeout=0)
        except KeyboardInterrupt:
            pass
        finally:
            try:
                context.close()
                print("Close Successfully")
            except Exception:
                pass


if __name__ == "__main__":
    main()