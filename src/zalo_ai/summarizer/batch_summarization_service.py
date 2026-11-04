import logging
from collections.abc import Callable

from zalo_ai.models.message import Message
from zalo_ai.summarizer.message_batcher import create_batches
from zalo_ai.summarizer.summarization_service import SummarizationService


class BatchSummarizationService:
    """Summarize messages grouped by their Zalo target."""

    def __init__(
        self,
        summarization_service: SummarizationService | None = None,
    ) -> None:
        self.summarization_service = (
            summarization_service or SummarizationService()
        )

    def summarize_messages(
        self,
        messages: list[Message],
        on_status: Callable[[str], None] | None = None,
    ) -> dict[str, str]:
        """Return one summary per target and report each generation step."""
        batches = create_batches(messages)
        summaries: dict[str, str] = {}

        for batch in batches:
            message = f"Generating summary for target {batch.target_id}."
            if on_status is not None:
                on_status(message)
            else:
                logging.getLogger(__name__).info(message)

            summaries[batch.target_id] = (
                self.summarization_service.summarize(batch)
            )
            completed_message = (
                f"Finished summary for target {batch.target_id}."
            )
            if on_status is not None:
                on_status(completed_message)
            else:
                logging.getLogger(__name__).info(completed_message)

        return summaries
