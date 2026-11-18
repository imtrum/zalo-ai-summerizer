from threading import Event

from playwright.sync_api import sync_playwright

from zalo_ai.common.cancellation import check_cancellation
from zalo_ai.targets.json_store import add_selected_targets, ensure_targets_file
from zalo_ai.integrations.zalo.conversations import discover_conversations
from .browser import ProgressCallback, notify, open_zalo


def discover_target_conversations(
    on_status: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> list[dict[str, str]]:
    """Open Zalo and discover conversations for the target refresh screen."""
    check_cancellation(cancel_event)
    with sync_playwright() as playwright:
        context, page = open_zalo(on_status, playwright, cancel_event=cancel_event)

        try:
            notify(on_status, "Discovering conversations.")
            if cancel_event is None:
                conversations = discover_conversations(page)
            else:
                conversations = discover_conversations(
                    page,
                    cancel_event=cancel_event,
                )
            check_cancellation(cancel_event)
            return conversations
        finally:
            context.close()


def save_discovered_targets(
    conversations: list[dict[str, str]],
) -> int:
    """Save selected discovered conversations to the target store."""
    ensure_targets_file()
    return add_selected_targets(conversations)
