from datetime import datetime, timedelta, timezone
from threading import Event

from playwright.sync_api import sync_playwright

from zalo_ai.ai.providers.provider_factory import create_provider
from zalo_ai.cancellation import check_cancellation
from zalo_ai.collector.zalo_message_collector import ZaloMessageCollector
from zalo_ai.models.message import Message
from zalo_ai.summarizer.batch_summarization_service import (
    BatchSummarizationService,
)
from zalo_ai.summarizer.summarization_service import SummarizationService
from zalo_ai.targets.json_store import get_enabled_targets
from zalo_ai.targets.zalo_discovery import (
    SCROLL_CONTAINER_SELECTOR,
    get_visible_conversation_ids,
    open_visible_conversation,
)
from .browser import (
    ProgressCallback,
    notify,
    open_zalo,
    wait_for_locator,
)


VN_TZ = timezone(timedelta(hours=7))


def run_summarization(
    cutoff: datetime,
    on_status: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> dict[str, str]:
    """Collect enabled Zalo chats and return summaries keyed by target ID."""
    check_cancellation(cancel_event)
    enabled_targets = get_enabled_targets()
    targets_by_id = {
        target["id"]: target for target in enabled_targets
    }

    if not targets_by_id:
        raise ValueError("No enabled targets are configured.")

    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=VN_TZ)
    else:
        cutoff = cutoff.astimezone(VN_TZ)

    all_messages: list[Message] = []
    processed_ids: set[str] = set()

    with sync_playwright() as playwright:
        if cancel_event is None:
            context, page = open_zalo(on_status, playwright)
        else:
            context, page = open_zalo(
                on_status,
                playwright,
                cancel_event=cancel_event,
            )

        try:
            scroll_handle = page.locator(
                SCROLL_CONTAINER_SELECTOR
            ).first.evaluate_handle(
                """element => {
                    for (
                        let current = element;
                        current && current !== document.body;
                        current = current.parentElement
                    ) {
                        const style = getComputedStyle(current);
                        if (
                            current.scrollHeight > current.clientHeight &&
                            ["auto", "scroll", "overlay"].includes(
                                style.overflowY
                            )
                        ) {
                            return current;
                        }
                    }
                    return null;
                }"""
            )
            scroll_container = scroll_handle.as_element()

            try:
                if scroll_container is None:
                    raise RuntimeError(
                        "Could not find the scrollable conversation list."
                    )

                def process_visible_targets() -> None:
                    checked_at_position: set[str] = set()

                    while True:
                        check_cancellation(cancel_event)
                        visible_ids = get_visible_conversation_ids(
                            scroll_container
                        )
                        target_id = next(
                            (
                                conversation_id
                                for conversation_id in visible_ids
                                if conversation_id in targets_by_id
                                and conversation_id not in processed_ids
                                and conversation_id not in checked_at_position
                            ),
                            None,
                        )

                        if target_id is None:
                            return

                        checked_at_position.add(target_id)
                        target_name = targets_by_id[target_id]["name"]
                        notify(
                            on_status,
                            f"Opening {target_name} and collecting messages.",
                        )

                        check_cancellation(cancel_event)
                        if not open_visible_conversation(page, target_id):
                            notify(
                                on_status,
                                f"Could not open {target_name}; continuing "
                                "the list scan.",
                            )
                            continue

                        wait_for_locator(
                            page.locator(
                                '[data-component="message-content-view"]'
                            ).first,
                            timeout_ms=15000,
                            cancel_event=cancel_event,
                        )
                        check_cancellation(cancel_event)

                        if cancel_event is None:
                            collector = ZaloMessageCollector(
                                page=page,
                                target_id=target_id,
                                cutoff=cutoff,
                            )
                        else:
                            collector = ZaloMessageCollector(
                                page=page,
                                target_id=target_id,
                                cutoff=cutoff,
                                cancel_event=cancel_event,
                            )
                        messages = collector.collect_messages()
                        check_cancellation(cancel_event)
                        all_messages.extend(messages)
                        processed_ids.add(target_id)
                        notify(
                            on_status,
                            f"Collected {len(messages)} messages from "
                            f"{target_name}.",
                        )

                notify(
                    on_status,
                    "Scanning downward from the conversation list's "
                    "current position.",
                )
                unchanged_rounds = 0
                while unchanged_rounds < 3:
                    check_cancellation(cancel_event)
                    process_visible_targets()

                    old_top = scroll_container.evaluate(
                        "(element) => element.scrollTop"
                    )
                    scroll_container.evaluate(
                        """element => {
                            element.scrollTop += Math.max(
                                300, element.clientHeight * 0.8
                            );
                        }"""
                    )
                    page.wait_for_timeout(500)
                    check_cancellation(cancel_event)

                    new_top = scroll_container.evaluate(
                        "(element) => element.scrollTop"
                    )
                    if new_top == old_top:
                        unchanged_rounds += 1
                    else:
                        unchanged_rounds = 0

                for target_id, target in targets_by_id.items():
                    check_cancellation(cancel_event)
                    if target_id not in processed_ids:
                        notify(
                            on_status,
                            f"Could not find target '{target['name']}' "
                            "in the scanned list.",
                        )
            finally:
                if scroll_container is not None:
                    scroll_container.dispose()
                scroll_handle.dispose()
        finally:
            context.close()

    check_cancellation(cancel_event)
    if not all_messages:
        raise ValueError(
            "No messages were collected after the selected cutoff."
        )

    notify(on_status, "Generating summaries.")
    provider = create_provider()
    summarization_service = SummarizationService(provider=provider)
    batch_service = BatchSummarizationService(
        summarization_service=summarization_service
    )
    target_names = {
        target_id: target["name"]
        for target_id, target in targets_by_id.items()
    }
    if cancel_event is None:
        summaries = batch_service.summarize_messages(
            all_messages,
            on_status=on_status,
            target_names=target_names,
        )
    else:
        summaries = batch_service.summarize_messages(
            all_messages,
            on_status=on_status,
            target_names=target_names,
            cancel_event=cancel_event,
        )
    check_cancellation(cancel_event)
    notify(on_status, "Summarization finished.")
    return summaries
