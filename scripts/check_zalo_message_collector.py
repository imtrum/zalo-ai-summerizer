
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from zalo_ai.collector.zalo_message_collector import ZaloMessageCollector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"
VN_TZ = timezone(timedelta(hours=7))


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

            input(
                "Open the target group, wait for messages to appear, "
                "then press Enter here..."
            )

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
