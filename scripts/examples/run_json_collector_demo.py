from zalo_ai.collector.message_collector import JsonMessageCollector
from zalo_ai.paths import SAMPLE_MESSAGES_FILE


def main() -> None:
    collector = JsonMessageCollector(SAMPLE_MESSAGES_FILE)
    messages = collector.collect_messages()

    print(f"Loaded {len(messages)} messages")

    for message in messages:
        print(f"{message.target_id} | {message.sender}: {message.content}")


if __name__ == "__main__":
    main()