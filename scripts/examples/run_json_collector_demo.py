from zalo_ai.collector.message_collector import JsonMessageCollector


def main() -> None:
    collector = JsonMessageCollector("data/sample_messages.json")
    messages = collector.collect_messages()

    print(f"Loaded {len(messages)} messages")

    for message in messages:
        print(f"{message.target_id} | {message.sender}: {message.content}")


if __name__ == "__main__":
    main()