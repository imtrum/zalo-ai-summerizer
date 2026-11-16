"""Run the project's sample collection and summarization demonstrations."""

import argparse
from datetime import datetime

from zalo_ai.ai.providers.mock_provider import MockProvider
from zalo_ai.collector.message_collector import JsonMessageCollector
from zalo_ai.models.message import Message
from zalo_ai.models.message_batch import MessageBatch
from zalo_ai.paths import SAMPLE_MESSAGES_FILE
from zalo_ai.summarizer.batch_summarization_service import BatchSummarizationService
from zalo_ai.summarizer.message_batcher import create_batches
from zalo_ai.summarizer.summarization_service import SummarizationService


def _messages():
    return JsonMessageCollector(SAMPLE_MESSAGES_FILE).collect_messages()


def json_demo() -> None:
    messages = _messages()
    print(f"Loaded {len(messages)} messages")
    for message in messages:
        print(f"{message.target_id} | {message.sender}: {message.content}")


def mock_demo() -> None:
    messages = _messages()
    service = SummarizationService(provider=MockProvider())
    summaries = BatchSummarizationService(service).summarize_messages(messages)
    print(f"Loaded {len(messages)} messages.")
    for target_id, summary in summaries.items():
        print(f"\n=== Summary for {target_id} ===")
        print(summary)


def batch_demo() -> None:
    messages = _messages()
    batches = create_batches(messages)
    print(f"Total messages: {len(messages)}")
    print(f"Total targets: {len(batches)}")
    for batch in batches:
        print(f"\nTarget: {batch.target_id}")
        print(f"Message count: {batch.get_message_count()}")
        for message in batch.get_messages():
            print(f"- {message.sender}: {message.content}")


def gemini_demo() -> None:
    messages = [
        Message("msg_001", "group_001", "Alice", "Cuộc họp dự án sẽ diễn ra lúc 9 giờ sáng mai.", datetime(2026, 10, 11, 8, 0)),
        Message("msg_002", "group_001", "Bob", "Tôi sẽ chuẩn bị báo cáo trước cuộc họp.", datetime(2026, 10, 11, 8, 5)),
    ]
    summary = SummarizationService().summarize(
        MessageBatch(target_id="group_001", messages=messages)
    )
    print("\n=== Gemini Summary ===")
    print(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("mock", "json", "gemini", "batch"):
        commands.add_parser(name)
    args = parser.parse_args()
    {"mock": mock_demo, "json": json_demo, "gemini": gemini_demo, "batch": batch_demo}[args.command]()


if __name__ == "__main__":
    main()
