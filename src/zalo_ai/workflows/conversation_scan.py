"""Collect enabled targets while scrolling the visible conversation list."""

from datetime import datetime
from threading import Event

from playwright.sync_api import ElementHandle, Page

from zalo_ai.common.cancellation import check_cancellation
from zalo_ai.integrations.zalo.conversations import (
    get_visible_conversation_ids,
    open_visible_conversation,
)
from zalo_ai.integrations.zalo.messages.collector import ZaloMessageCollector
from zalo_ai.integrations.zalo.selectors import MESSAGE_FRAME_SELECTOR
from zalo_ai.models.message import Message
from .browser import ProgressCallback, notify, wait_for_locator


def _collect_visible_targets(
    page: Page,
    scroll_container: ElementHandle,
    targets_by_id: dict[str, dict],
    processed_ids: set[str],
    cutoff: datetime,
    cancel_event: Event | None,
    on_status: ProgressCallback | None,
) -> list[Message]:
    """Collect each unprocessed target currently visible in the list."""
    messages: list[Message] = []
    checked_at_position: set[str] = set()
    while True:
        check_cancellation(cancel_event)
        visible_ids = get_visible_conversation_ids(scroll_container)
        target_id = next((
            conversation_id for conversation_id in visible_ids
            if conversation_id in targets_by_id
            and conversation_id not in processed_ids
            and conversation_id not in checked_at_position
        ), None)
        if target_id is None:
            return messages

        checked_at_position.add(target_id)
        target_name = targets_by_id[target_id]["name"]
        notify(on_status, f"Opening {target_name} and collecting messages.")
        check_cancellation(cancel_event)
        if not open_visible_conversation(page, target_id):
            notify(on_status, f"Could not open {target_name}; continuing the list scan.")
            continue

        wait_for_locator(
            page.locator(MESSAGE_FRAME_SELECTOR).first,
            timeout_ms=15000,
            cancel_event=cancel_event,
        )
        check_cancellation(cancel_event)
        collector = ZaloMessageCollector(
            page=page,
            target_id=target_id,
            cutoff=cutoff,
            cancel_event=cancel_event,
        )
        collected = collector.collect_messages()
        check_cancellation(cancel_event)
        messages.extend(collected)
        processed_ids.add(target_id)
        notify(on_status, f"Collected {len(collected)} messages from {target_name}.")


def _scan_conversation_list(
    page: Page,
    scroll_container: ElementHandle,
    targets_by_id: dict[str, dict],
    processed_ids: set[str],
    cutoff: datetime,
    cancel_event: Event | None,
    on_status: ProgressCallback | None,
) -> list[Message]:
    """Scroll down until three consecutive moves leave the list unchanged."""
    messages: list[Message] = []
    notify(on_status, "Scanning downward from the conversation list's current position.")
    unchanged_rounds = 0
    while unchanged_rounds < 3:
        check_cancellation(cancel_event)
        messages.extend(_collect_visible_targets(
            page, scroll_container, targets_by_id, processed_ids,
            cutoff, cancel_event, on_status,
        ))
        old_top = scroll_container.evaluate("(element) => element.scrollTop")
        scroll_container.evaluate("""element => {
            element.scrollTop += Math.max(300, element.clientHeight * 0.8);
        }""")
        page.wait_for_timeout(500)
        check_cancellation(cancel_event)
        new_top = scroll_container.evaluate("(element) => element.scrollTop")
        unchanged_rounds = unchanged_rounds + 1 if new_top == old_top else 0

    for target_id, target in targets_by_id.items():
        check_cancellation(cancel_event)
        if target_id not in processed_ids:
            notify(on_status, f"Could not find target '{target['name']}' in the scanned list.")
    return messages
