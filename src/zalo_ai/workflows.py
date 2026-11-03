import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from playwright.sync_api import sync_playwright

from zalo_ai.ai.providers.provider_factory import create_provider
from zalo_ai.collector.zalo_message_collector import ZaloMessageCollector
from zalo_ai.models.message import Message
from zalo_ai.summarizer.batch_summarization_service import (
    BatchSummarizationService,
)
from zalo_ai.summarizer.summarization_service import SummarizationService
from zalo_ai.targets.json_store import (
    add_selected_targets,
    get_enabled_targets,
)
from zalo_ai.targets.zalo_discovery import (
    CONVERSATION_SELECTOR,
    SCROLL_CONTAINER_SELECTOR,
    discover_conversations,
    get_visible_conversation_ids,
    open_visible_conversation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"
VN_TZ = timezone(timedelta(hours=7))
ProgressCallback = Callable[[str], None]


def _notify(callback: ProgressCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)
    else:
        logging.getLogger(__name__).info(message)


def run_summarization(
    cutoff: datetime,
    on_status: ProgressCallback | None = None,
) -> dict[str, str]:
    """Collect enabled Zalo chats and return summaries keyed by target ID."""
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
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )
            page.goto("https://chat.zalo.me/")
            _notify(
                on_status,
                "Zalo opened. Sign in in the browser if prompted; "
                "waiting for the conversation list.",
            )
            page.locator(CONVERSATION_SELECTOR).first.wait_for(
                state="visible",
                timeout=300000,
            )

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
                        _notify(
                            on_status,
                            f"Opening {target_name} and collecting messages.",
                        )

                        if not open_visible_conversation(page, target_id):
                            _notify(
                                on_status,
                                f"Could not open {target_name}; continuing "
                                "the list scan.",
                            )
                            continue

                        page.locator(
                            '[data-component="message-content-view"]'
                        ).first.wait_for(
                            state="visible",
                            timeout=15000,
                        )

                        collector = ZaloMessageCollector(
                            page=page,
                            target_id=target_id,
                            cutoff=cutoff,
                        )
                        messages = collector.collect_messages()
                        all_messages.extend(messages)
                        processed_ids.add(target_id)
                        _notify(
                            on_status,
                            f"Collected {len(messages)} messages from "
                            f"{target_name}.",
                        )

                _notify(
                    on_status,
                    "Scanning downward from the conversation list's "
                    "current position.",
                )
                unchanged_rounds = 0
                while unchanged_rounds < 3:
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

                    new_top = scroll_container.evaluate(
                        "(element) => element.scrollTop"
                    )
                    if new_top == old_top:
                        unchanged_rounds += 1
                    else:
                        unchanged_rounds = 0

                for target_id, target in targets_by_id.items():
                    if target_id not in processed_ids:
                        _notify(
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

    if not all_messages:
        raise ValueError(
            "No messages were collected after the selected cutoff."
        )

    _notify(on_status, "Generating summaries.")
    provider = create_provider()
    summarization_service = SummarizationService(provider=provider)
    batch_service = BatchSummarizationService(
        summarization_service=summarization_service
    )
    summaries = batch_service.summarize_messages(all_messages)
    _notify(on_status, "Summarization finished.")
    return summaries


def discover_target_conversations(
    on_status: ProgressCallback | None = None,
) -> list[dict[str, str]]:
    """Open Zalo and discover conversations for the target refresh screen."""
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE),
            headless=False,
        )

        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )
            page.goto("https://chat.zalo.me/")
            _notify(
                on_status,
                "Zalo opened. Sign in in the browser if prompted.",
            )
            page.locator(CONVERSATION_SELECTOR).first.wait_for(
                state="visible",
                timeout=300000,
            )
            _notify(on_status, "Discovering conversations.")
            return discover_conversations(page)
        finally:
            context.close()


def save_discovered_targets(
    conversations: list[dict[str, str]],
) -> int:
    """Save selected discovered conversations to the target store."""
    return add_selected_targets(conversations)
