
from pathlib import Path

from playwright.sync_api import sync_playwright

from zalo_ai.targets.json_store import add_selected_targets
from zalo_ai.targets.zalo_discovery import discover_conversations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"


def main() -> None:
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://chat.zalo.me/")

            input(
                "Wait for Zalo to load, then press Enter here..."
            )

            conversations = discover_conversations(page)

            if not conversations:
                print("No conversations were discovered.")
                return

            print("\nDiscovered conversations:")
            for index, conversation in enumerate(conversations, start=1):
                print(f"{index}. {conversation['name']}")

            print(
                "\nEnter the numbers of the conversations you want to add, "
                "separated by commas."
            )
            print("Example: 1,3,5")
            print("Enter 0 to cancel.")

            choice = input("Your selection: ").strip()

            if choice == "0" or not choice:
                print("Target refresh cancelled.")
                return

            try:
                selected_indices = {
                    int(value.strip())
                    for value in choice.split(",")
                }
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas.")
                return

            if any(
                index < 1 or index > len(conversations)
                for index in selected_indices
            ):
                print("One or more selections are out of range.")
                return

            selected = [
                conversations[index - 1]
                for index in sorted(selected_indices)
            ]

            added_count = add_selected_targets(selected)

            print(f"\nSelected {len(selected)} conversations.")
            print(f"Added {added_count} new targets to targets.json.")
            print(
                "Existing targets were preserved. "
                "Review targets.json to confirm the result."
            )

        finally:
            context.close()


if __name__ == "__main__":
    main()
