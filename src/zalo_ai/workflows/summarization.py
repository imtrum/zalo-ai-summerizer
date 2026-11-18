"""Run the end-to-end Zalo message collection and summarization workflow."""

from datetime import datetime
from threading import Event

from playwright.sync_api import sync_playwright

from zalo_ai.common.cancellation import check_cancellation
from zalo_ai.config.timezone import VN_TZ
from zalo_ai.integrations.zalo.scroll_container import find_scroll_container
from zalo_ai.targets.json_store import get_enabled_targets
from .browser import ProgressCallback, open_zalo
from .conversation_scan import _scan_conversation_list
from .summarize import _summarize


def run_summarization(
    cutoff: datetime,
    on_status: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> dict[str, str]:
    """Collect enabled Zalo chats and return summaries keyed by target ID."""
    check_cancellation(cancel_event)
    targets_by_id = {
        target["id"]: target for target in get_enabled_targets()
    }
    if not targets_by_id:
        raise ValueError("No enabled targets are configured.")
    cutoff = (
        cutoff.replace(tzinfo=VN_TZ)
        if cutoff.tzinfo is None
        else cutoff.astimezone(VN_TZ)
    )

    with sync_playwright() as playwright:
        context, page = open_zalo(on_status, playwright, cancel_event=cancel_event)
        try:
            handle, scroll_container = find_scroll_container(page)
            try:
                if scroll_container is None:
                    raise RuntimeError(
                        "Could not find the scrollable conversation list."
                    )
                messages = _scan_conversation_list(
                    page, scroll_container, targets_by_id, set(),
                    cutoff, cancel_event, on_status,
                )
            finally:
                if scroll_container is not None:
                    scroll_container.dispose()
                handle.dispose()
        finally:
            context.close()

    return _summarize(messages, targets_by_id, on_status, cancel_event)
