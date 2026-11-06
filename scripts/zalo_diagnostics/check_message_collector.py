
from datetime import datetime

from playwright.sync_api import sync_playwright

from zalo_ai.config.timezone import VN_TZ
from zalo_ai.integrations.zalo.messages.collector import ZaloMessageCollector
from zalo_ai.integrations.zalo.selectors import (
    CONVERSATION_ID_ATTRIBUTE,
    CONVERSATION_SELECTOR,
    MESSAGE_FRAME_SELECTOR,
)
from zalo_ai.paths import BROWSER_PROFILE


def main() -> None:
    target_id = input("Enter the target group ID: ").strip()
    cutoff_text = input(
        "Enter cutoff (YYYY-MM-DD HH:MM): "
    ).strip()

    cutoff = datetime.strptime(
        cutoff_text, "%Y-%m-%d %H:%M"
    ).replace(tzinfo=VN_TZ)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")

            conversation = page.locator(
                f'{CONVERSATION_SELECTOR}[{CONVERSATION_ID_ATTRIBUTE}="{target_id}"]'
            )

            conversation.wait_for(state="visible", timeout=15000)
            conversation.click()

            page.locator(
                MESSAGE_FRAME_SELECTOR
            ).first.wait_for(state="visible", timeout=15000)

            print(f"Opened conversation: {target_id}")

            collector = ZaloMessageCollector(
                page=page,
                target_id=target_id,
                cutoff=cutoff,
            )
            messages = collector.collect_messages()

            print(f"\nCollected {len(messages)} messages:")
            for message in messages:
                print(
                    f"[{message.timestamp:%Y-%m-%d %H:%M}] "
                    f"{message.sender}: {message.content}"
                )
        finally:
            context.close()


if __name__ == "__main__":
    main()
