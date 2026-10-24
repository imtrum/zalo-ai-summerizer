
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
from zalo_ai.targets.zalo_discovery import find_conversation,discover_conversations, open_conversation


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"
VN_TZ = timezone(timedelta(hours=7))


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting live Zalo summarization workflow.")

        enabled_targets = get_enabled_targets()

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

                for target in enabled_targets:
                    target_id = target["id"]
                    target_name = target["name"]

                    logger.info("Opening conversation: %s", target_name)

                    if not open_conversation(page, target_id):
                        logger.warning(
                            "Could not find conversation '%s' (ID: %s). Skipping.",
                            target_name,
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
