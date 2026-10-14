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

    def summarize_messages(self, messages: list[Message]) -> dict[str, str]:
        """Return one summary for each target ID."""
        batches = create_batches(messages)

        return {
            batch.target_id: self.summarization_service.summarize(batch)
            for batch in batches
        }