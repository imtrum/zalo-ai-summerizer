
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone

from playwright.sync_api import Page

from zalo_ai.collector.message_collector import MessageCollector
from zalo_ai.models.message import Message


VN_TZ = timezone(timedelta(hours=7))

FRAME_SELECTOR = '[data-component="message-content-view"]'
TEXT_SELECTOR = '[data-component="message-text-content"]'
SENDER_SELECTOR = ".message-sender-name-content"
TIME_SELECTOR = ".card-send-time__sendTime, .card-send-time"


COLLECT_JS = """() => {
    const frames = [...document.querySelectorAll(
        '[data-component="message-content-view"]'
    )];

    const clean = (value) =>
        (value || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();

    const separators = [...document.querySelectorAll('*')]
        .filter(el =>
            el.children.length === 0 &&
            !el.closest('[data-component="message-content-view"]') &&
            /^(T[2-7]\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|CN\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|Hôm nay|Hôm qua|\\d{1,2}\\/\\d{1,2}\\/\\d{4})$/i
                .test(clean(el.textContent))
        );

    return frames.map((frame, index) => {
        let row = frame;

        for (let i = 0; i < 8; i++) {
            const parent = row.parentElement;
            if (!parent ||
                parent.querySelectorAll(
                    '[data-component="message-content-view"]'
                ).length !== 1) break;
            row = parent;
        }

        const sender = row.querySelector('.message-sender-name-content');
        const timeElement = row.querySelector(
            '.card-send-time__sendTime, .card-send-time'
        );

        const fullTimeElement = [...row.querySelectorAll('*')].find(el =>
            el.children.length === 0 &&
            /^\\d{1,2}:\\d{2}\\s+(\\d{1,2}\\/\\d{1,2}\\/\\d{4}|Hôm nay|Hôm qua)$/i
                .test(clean(el.textContent))
        );

        let previousDate = null;
        for (const separator of separators) {
            if (separator.compareDocumentPosition(frame) &
                Node.DOCUMENT_POSITION_FOLLOWING) {
                previousDate = separator;
            }
        }

        const ids = [];
        for (let el = frame; el; el = el.parentElement) {
            if (el.id) ids.push(el.id);
            if (el === row) break;
        }

        return {
            index,
            message_id: ids.find(id => id.startsWith('message-frame'))
                || ids[0] || null,
            sender: sender ? clean(sender.innerText) : null,
            content: [...frame.querySelectorAll(
                '[data-component="message-text-content"]'
            )].map(el => clean(el.innerText)).filter(Boolean).join('\\n'),
            time_text: timeElement ? clean(timeElement.innerText) : null,
            full_time_text: fullTimeElement
                ? clean(fullTimeElement.textContent) : null,
            date_separator: previousDate ? clean(previousDate.textContent) : null
        };
    });
}"""


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip() or None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    lowered = value.lower()
    today = datetime.now(VN_TZ).date()

    if "hôm nay" in lowered:
        return today
    if "hôm qua" in lowered:
        return today - timedelta(days=1)

    return None


def parse_timestamp(record: dict) -> datetime | None:
    """Return a timestamp only when both date and time are identifiable."""

    full_text = record.get("full_time_text") or ""
    full_match = re.search(
        r"(\d{1,2}):(\d{2})\s+(.*)",
        full_text,
    )

    if full_match:
        hour, minute = map(int, full_match.groups()[:2])
        message_date = parse_date(full_match.group(3))
    else:
        time_text = record.get("time_text") or ""
        time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", time_text)

        if not time_match:
            return None

        hour, minute = map(int, time_match.groups())
        message_date = parse_date(record.get("date_separator"))

    if message_date is None:
        return None

    try:
        return datetime.combine(
            message_date,
            time(hour, minute),
            tzinfo=VN_TZ,
        )
    except ValueError:
        return None


class ZaloMessageCollector(MessageCollector):
    """Collect currently rendered messages from an open Zalo chat."""

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

    def collect_messages(self) -> list[Message]:
        """Extract visible messages whose timestamps are at or after cutoff."""

        records = self.page.evaluate(COLLECT_JS)
        messages: list[Message] = []
        seen: set[tuple] = set()
        last_sender: str | None = None

        for record in records:
            sender = clean_text(record.get("sender"))
            if sender:
                last_sender = sender
            else:
                sender = last_sender

            content = clean_text(record.get("content"))
            timestamp = parse_timestamp(record)

            # Do not invent missing dates, times, senders, or message content.
            if not content or not sender or timestamp is None:
                continue

            if timestamp < self.cutoff:
                continue

            message_id = record.get("message_id")
            if not message_id:
                message_id = (
                    f"fallback-{timestamp.isoformat()}-"
                    f"{sender}-{content}"
                )

            key = (
                message_id,
                timestamp.isoformat(),
                unicodedata.normalize("NFKC", content),
            )

            if key in seen:
                continue
            seen.add(key)

            messages.append(
                Message(
                    message_id=str(message_id),
                    target_id=self.target_id,
                    sender=sender,
                    content=content,
                    timestamp=timestamp,
                )
            )

        return messages
