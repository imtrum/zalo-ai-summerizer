
from zalo_ai.collector.message_collector import JsonMessageCollector
from zalo_ai.summarizer.message_batcher import create_batches


def main() -> None:
    collector = JsonMessageCollector("data/sample_messages.json")
    messages = collector.collect_messages()

    batches = create_batches(messages)

    print(f"Total messages: {len(messages)}")
    print(f"Total targets: {len(batches)}")

    for batch in batches:
        print(f"\nTarget: {batch.target_id}")
        print(f"Message count: {batch.get_message_count()}")

        for message in batch.get_messages():
            print(f"- {message.sender}: {message.content}")


if __name__ == "__main__":
    main()