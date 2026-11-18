"""Set up the provider and summarize collected messages."""

from threading import Event

from zalo_ai.ai.providers.provider_factory import create_provider
from zalo_ai.common.cancellation import check_cancellation
from zalo_ai.models.message import Message
from zalo_ai.summarizer.batch_summarization_service import BatchSummarizationService
from zalo_ai.summarizer.summarization_service import SummarizationService
from .browser import ProgressCallback, notify


def _summarize(
    messages: list[Message],
    targets_by_id: dict[str, dict],
    on_status: ProgressCallback | None,
    cancel_event: Event | None,
) -> dict[str, str]:
    """Return a summary for each target represented in the messages."""
    check_cancellation(cancel_event)
    if not messages:
        raise ValueError("No messages were collected after the selected cutoff.")

    notify(on_status, "Generating summaries.")
    summarization_service = SummarizationService(provider=create_provider())
    batch_service = BatchSummarizationService(
        summarization_service=summarization_service
    )
    target_names = {
        target_id: target["name"] for target_id, target in targets_by_id.items()
    }
    summaries = batch_service.summarize_messages(
        messages,
        on_status=on_status,
        target_names=target_names,
        cancel_event=cancel_event,
    )
    check_cancellation(cancel_event)
    notify(on_status, "Summarization finished.")
    return summaries
