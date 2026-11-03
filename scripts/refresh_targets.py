from zalo_ai.config.logging_config import setup_logging
from zalo_ai.workflows import (
    discover_target_conversations,
    save_discovered_targets,
)


def main() -> None:
    setup_logging()

    try:
        conversations = discover_target_conversations(
            on_status=print,
        )

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
                int(value.strip()) for value in choice.split(",")
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
        added_count = save_discovered_targets(selected)

        print(f"\nSelected {len(selected)} conversations.")
        print(f"Added {added_count} new targets to targets.json.")
        print(
            "Existing targets were preserved. "
            "Review targets.json to confirm the result."
        )
    except Exception as exc:
        print(f"Target refresh failed: {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
