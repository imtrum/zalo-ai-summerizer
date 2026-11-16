"""Open Zalo, inspect the chat list, or collect messages from a chat."""

import argparse
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
from diagnostics_dom import inspect_chat_list


def open_browser() -> None:
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE), headless=False
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")
            print("Log in to Zalo manually in the browser.")
            print("Close the browser window when you finish.")
            context.wait_for_event("close", timeout=0)
        except KeyboardInterrupt:
            pass
        finally:
            try:
                context.close()
                print("Close Successfully")
            except Exception:
                pass


def check_messages() -> None:
    target_id = input("Enter the target group ID: ").strip()
    cutoff_text = input("Enter cutoff (YYYY-MM-DD HH:MM): ").strip()
    cutoff = datetime.strptime(cutoff_text, "%Y-%m-%d %H:%M").replace(tzinfo=VN_TZ)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE), headless=False
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")
            conversation = page.locator(
                f'{CONVERSATION_SELECTOR}[{CONVERSATION_ID_ATTRIBUTE}="{target_id}"]'
            )
            conversation.wait_for(state="visible", timeout=15000)
            conversation.click()
            page.locator(MESSAGE_FRAME_SELECTOR).first.wait_for(
                state="visible", timeout=15000
            )
            print(f"Opened conversation: {target_id}")
            messages = ZaloMessageCollector(
                page=page, target_id=target_id, cutoff=cutoff
            ).collect_messages()
            print(f"\nCollected {len(messages)} messages:")
            for message in messages:
                print(f"[{message.timestamp:%Y-%m-%d %H:%M}] {message.sender}: {message.content}")
        finally:
            context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("open-browser")
    commands.add_parser("chat-list")
    commands.add_parser("messages")
    args = parser.parse_args()
    {"open-browser": open_browser, "chat-list": inspect_chat_list,
     "messages": check_messages}[args.command]()


if __name__ == "__main__":
    main()
