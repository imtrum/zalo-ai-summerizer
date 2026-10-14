
from zalo_ai.ai.providers.mock_provider import MockProvider
from zalo_ai.collector.message_collector import JsonMessageCollector
from zalo_ai.summarizer.batch_summarization_service import (
    BatchSummarizationService,
)
from zalo_ai.summarizer.summarization_service import SummarizationService


def main() -> None:
    collector = JsonMessageCollector("data/sample_messages.json")
    messages = collector.collect_messages()

    mock_provider = MockProvider()
    summarization_service = SummarizationService(
        provider=mock_provider
    )
    batch_service = BatchSummarizationService(
        summarization_service=summarization_service
    )

    summaries = batch_service.summarize_messages(messages)

    print(f"Loaded {len(messages)} messages.")

    for target_id, summary in summaries.items():
        print(f"\n=== Summary for {target_id} ===")
        print(summary)


if __name__ == "__main__":
    main()