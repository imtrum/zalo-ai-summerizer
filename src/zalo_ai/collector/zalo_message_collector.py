
import unicodedata
from datetime import datetime, timedelta, timezone

from playwright.sync_api import Page

from zalo_ai.collector.message_collector import MessageCollector
from zalo_ai.collector.zalo_message_parser import (
    COLLECT_JS,
    clean_text,
    parse_timestamp,
)
from zalo_ai.collector.zalo_scroll_helper import ZaloScrollHelper
from zalo_ai.models.message import Message


VN_TZ = timezone(timedelta(hours=7))

MAX_SCROLL_ROUNDS = 100
SCROLL_WAIT_MS = 1000


class ZaloMessageCollector(MessageCollector):
    """Collect Zalo messages by scrolling back to a cutoff time."""

    def __init__(
        self,
        page: Page,
        target_id: str,
        cutoff: datetime,
    ) -> None:
        if not target_id.strip():
            raise ValueError("target_id must not be empty")

        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=VN_TZ)
        else:
            cutoff = cutoff.astimezone(VN_TZ)

        self.page = page
        self.target_id = target_id
        self.cutoff = cutoff
        self.scroll_helper = ZaloScrollHelper(page)

    @staticmethod
    def _record_key(record: dict) -> tuple:
        """Build a stable key for comparing rendered message records."""
        return (
            record.get("message_id"),
            record.get("full_time_text"),
            record.get("time_text"),
            record.get("date_separator"),
            record.get("sender"),
            record.get("content"),
        )

    def _collect_snapshot(
        self,
        collected: dict[tuple, Message],
    ) -> bool:
        """Collect one rendered snapshot. Return True if cutoff is reached."""
        records = self.page.evaluate(COLLECT_JS)
        last_sender: str | None = None
        cutoff_reached = False

        for record in records:
            sender = clean_text(record.get("sender"))

            if sender:
                last_sender = sender
            else:
                sender = last_sender

            content = clean_text(record.get("content"))
            timestamp = parse_timestamp(record)

            # Never guess missing message information.
            if not content or not sender or timestamp is None:
                continue

            if timestamp < self.cutoff:
                cutoff_reached = True
                continue

            message_id = record.get("message_id")
            if not message_id:
                message_id = (
                    f"fallback-{timestamp.isoformat()}-{sender}-{content}"
                )

            key = (
                str(message_id),
                timestamp.isoformat(),
                unicodedata.normalize("NFKC", content),
            )

            if key not in collected:
                collected[key] = Message(
                    message_id=str(message_id),
                    target_id=self.target_id,
                    sender=sender,
                    content=content,
                    timestamp=timestamp,
                )

        return cutoff_reached

    def collect_messages(self) -> list[Message]:
        """Collect messages at or after cutoff, loading older history as needed."""
        collected: dict[tuple, Message] = {}

        scroller = self.scroll_helper.find_scroller()

        # If the scroll container cannot be identified, collect what's visible.
        if scroller is None:
            self._collect_snapshot(collected)
            return sorted(
                collected.values(),
                key=lambda message: message.timestamp,
            )

        try:
            for _ in range(MAX_SCROLL_ROUNDS):
                if self._collect_snapshot(collected):
                    break

                before_records = self.page.evaluate(COLLECT_JS)
                before_keys = {
                    self._record_key(record) for record in before_records
                }
                before_height = scroller.evaluate(
                    "(el) => el.scrollHeight"
                )

                self.scroll_helper.scroll_up(scroller)
                self.page.wait_for_timeout(SCROLL_WAIT_MS)

                if self._collect_snapshot(collected):
                    break

                after_records = self.page.evaluate(COLLECT_JS)
                after_keys = {
                    self._record_key(record) for record in after_records
                }
                after_height = scroller.evaluate(
                    "(el) => el.scrollHeight"
                )

                # If direct scrolling did not load anything, try the mouse wheel.
                if (
                    after_keys == before_keys
                    and after_height == before_height
                ):
                    self.scroll_helper.scroll_up_with_wheel(scroller)
                    self.page.wait_for_timeout(SCROLL_WAIT_MS)

                    if self._collect_snapshot(collected):
                        break

                    wheel_records = self.page.evaluate(COLLECT_JS)
                    wheel_keys = {
                        self._record_key(record) for record in wheel_records
                    }
                    wheel_height = scroller.evaluate(
                        "(el) => el.scrollHeight"
                    )

                    if (
                        wheel_keys == before_keys
                        and wheel_height == before_height
                    ):
                        break
        finally:
            scroller.dispose()

        return sorted(
            collected.values(),
            key=lambda message: message.timestamp,
        )
