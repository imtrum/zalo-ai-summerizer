
import logging

from zalo_ai.targets.json_store import get_enabled_targets
from zalo_ai.targets.filter import filter_messages_by_target_ids
from zalo_ai.ai.providers.provider_factory import create_provider
from zalo_ai.collector.message_collector import JsonMessageCollector
from zalo_ai.config.logging_config import setup_logging
from zalo_ai.summarizer.batch_summarization_service import (
    BatchSummarizationService,
)
from zalo_ai.summarizer.summarization_service import SummarizationService


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting summarization workflow.")

        collector = JsonMessageCollector("data/sample_messages.json")
        messages = collector.collect_messages()
        logger.info("Loaded %d messages.", len(messages))

        enabled_targets = get_enabled_targets()
        enabled_target_ids = {
            target["id"] for target in enabled_targets
        }

        messages = filter_messages_by_target_ids(messages, enabled_target_ids)
        
        logger.info(
            "Loaded %d enabled targets and selected %d messages.",
            len(enabled_targets),
            len(messages),
        )

        if not messages:
            logger.warning("No messages found. Nothing to summarize.")
            return

        provider = create_provider()
        logger.info("AI provider initialized: %s", type(provider).__name__)

        summarization_service = SummarizationService(provider=provider)
        batch_service = BatchSummarizationService(
            summarization_service=summarization_service
        )
        summaries = batch_service.summarize_messages(messages)

        for target_id, summary in summaries.items():
            logger.info("Summary generated for target: %s", target_id)
            print(f"\n=== Summary for {target_id} ===")
            print(summary)

        logger.info("Summarization workflow completed.")

    except (FileNotFoundError, ValueError) as exc:
        logger.error("Cannot process input: %s", exc)
        raise
    except Exception:
        logger.exception("Unexpected error during summarization.")
        raise


if __name__ == "__main__":
    main()