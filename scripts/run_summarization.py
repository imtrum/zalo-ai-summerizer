import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from zalo_ai.ai.providers.provider_factory import create_provider
from zalo_ai.collector.zalo_message_collector import ZaloMessageCollector
from zalo_ai.config.logging_config import setup_logging
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"
VN_TZ = timezone(timedelta(hours=7))


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting live Zalo summarization workflow.")

        enabled_targets = get_enabled_targets()
        enabled_targets_by_id = {
            target["id"]: target for target in enabled_targets
        }

        if not enabled_targets:
            logger.warning("No enabled targets found. Nothing to summarize.")
            return

        cutoff_text = input(
            "Enter cutoff (YYYY-MM-DD HH:MM, Vietnam time): "
        ).strip()

        cutoff = datetime.strptime(
            cutoff_text,
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=VN_TZ)

        all_messages = []
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

                input(
                    "Wait for Zalo to load and log in if necessary, "
                    "then press Enter..."
                )

                scroll_handle = page.locator(
                    SCROLL_CONTAINER_SELECTOR
                ).evaluate_handle(
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
                        logger.error(
                            "Could not find the scrollable conversation list."
                        )
                    else:
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
                                        if conversation_id
                                        in enabled_targets_by_id
                                        and conversation_id
                                        not in processed_ids
                                        and conversation_id
                                        not in checked_at_position
                                    ),
                                    None,
                                )

                                if target_id is None:
                                    return

                                checked_at_position.add(target_id)
                                target = enabled_targets_by_id[target_id]
                                target_name = target["name"]

                                logger.info(
                                    "Opening conversation: %s",
                                    target_name,
                                )

                                if not open_visible_conversation(
                                    page,
                                    target_id,
                                ):
                                    logger.debug(
                                        "Conversation row %s is no longer "
                                        "visible; it will be checked again "
                                        "after scrolling.",
                                        target_id,
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

                                logger.info(
                                    "Collected %d messages from %s.",
                                    len(messages),
                                    target_name,
                                )
                                all_messages.extend(messages)
                                processed_ids.add(target_id)

                        # Scan twice to catch any rows missed during the first pass.
                        for _ in range(2):
                            scroll_container.evaluate(
                                "(element) => { element.scrollTop = 0; }"
                            )
                            page.wait_for_timeout(500)

                            unchanged_rounds = 0
                            while unchanged_rounds < 3:
                                process_visible_targets()

                                position = scroll_container.evaluate(
                                    """element => ({
                                        top: element.scrollTop,
                                        max: element.scrollHeight
                                            - element.clientHeight
                                    })"""
                                )
                                if position["top"] >= position["max"]:
                                    break

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
                                if new_top == position["top"]:
                                    unchanged_rounds += 1
                                else:
                                    unchanged_rounds = 0

                        for target_id, target in enabled_targets_by_id.items():
                            if target_id not in processed_ids:
                                logger.warning(
                                    "Could not find conversation '%s' "
                                    "(ID: %s) during the list scan.",
                                    target["name"],
                                    target_id,
                                )
                finally:
                    if scroll_container is not None:
                        scroll_container.dispose()
                    scroll_handle.dispose()

            finally:
                context.close()

        if not all_messages:
            logger.warning(
                "No messages found after the cutoff. Nothing to summarize."
            )
            return

        provider = create_provider()
        logger.info("AI provider initialized: %s", type(provider).__name__)

        summarization_service = SummarizationService(provider=provider)
        batch_service = BatchSummarizationService(
            summarization_service=summarization_service
        )
        summaries = batch_service.summarize_messages(all_messages)

        for target_id, summary in summaries.items():
            logger.info("Summary generated for target: %s", target_id)
            print(f"\n=== Summary for {target_id} ===")
            print(summary)

        logger.info("Live Zalo summarization workflow completed.")

    except (FileNotFoundError, ValueError) as exc:
        logger.error("Cannot process input: %s", exc)
        raise
    except Exception:
        logger.exception("Unexpected error during summarization.")
        raise


if __name__ == "__main__":
    main()