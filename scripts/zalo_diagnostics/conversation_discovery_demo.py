from playwright.sync_api import sync_playwright

from zalo_ai.integrations.zalo.conversations import discover_conversations
from zalo_ai.paths import BROWSER_PROFILE


def main() -> None:
    profile = BROWSER_PROFILE

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")
            input("Wait for Zalo to load, then press Enter... ")

            conversations = discover_conversations(page)
            for item in conversations:
                print(item)

            print(f"Discovered {len(conversations)} conversations.")
        finally:
            context.close()


if __name__ == "__main__":
    main()
